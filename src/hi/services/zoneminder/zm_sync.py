import logging
from .pyzm_client.helpers.Monitor import Monitor as ZmMonitor
from typing import Dict, Optional

from django.db import transaction

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor

from hi.apps.model_helper import HiModelHelper

from hi.apps.entity.entity_placement import (
    EntityPlacementInput,
    EntityPlacementItem,
    EntityPlacementGroup,
)

from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from .zm_metadata import ZmMetaData
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZoneMinderSynchronizer( IntegrationSynchronizer, ZoneMinderMixin ):

    def get_integration_metadata(self):
        return ZmMetaData

    MONITOR_FUNCTION_NAME_LABEL_DICT = {
        'None': 'None',
        'Monitor': 'Monitor',
        'Modect': 'Modect',
        'Record': 'Record',
        'Mocord': 'Mocord',
        'Nodect': 'Nodect',
    }

    def get_description(self, is_initial_import: bool) -> Optional[str]:
        if is_initial_import:
            return (
                'Each monitor becomes a camera with motion and'
                ' run-state sensors.'
            )
        return None

    def _sync_impl( self, is_initial_import: bool ) -> IntegrationSyncResult:
        result = IntegrationSyncResult(
            title = self.get_result_title( is_initial_import = is_initial_import ),
        )

        if not self.zm_manager().zm_client:
            logger.debug( 'ZoneMinder client not created. ZM integration disabled?' )
            result.error_list.append( 'Sync problem. ZM integration disabled?' )
            return result

        self._sync_states( result = result )
        created_monitor_entities = self._sync_monitors( result = result )

        # Existing-entity updates do not need re-placement; only
        # newly-created monitor entities surface in the dispatcher.
        if created_monitor_entities:
            result.placement_input = self.group_entities_for_placement(
                entities = created_monitor_entities,
            )
        return result

    def group_entities_for_placement( self, entities ) -> EntityPlacementInput:
        """Single 'Monitors' group: ZM monitors typically share a
        view, and the operator's first instinct is 'all cameras →
        same place.' The dispatcher's drill-down still allows
        per-monitor placement when needed.

        Empty input → empty placement input (no dispatcher
        rendering)."""
        if not entities:
            return EntityPlacementInput()
        items = [
            EntityPlacementItem(
                key = self._placement_item_key( entity = entity ),
                label = entity.name,
                entity = entity,
            )
            for entity in entities
        ]
        return EntityPlacementInput(
            groups = [ EntityPlacementGroup( label = 'Monitors', items = items ) ],
        )

    def _sync_states( self, result : IntegrationSyncResult ) -> IntegrationSyncResult:
        zm_manager = self.zm_manager()
        
        zm_run_state_list = zm_manager.get_zm_states( force_load = True )
        new_state_values_dict = { x.name(): x.name() for x in zm_run_state_list }
        
        zm_entity = Entity.objects.filter_by_integration_key(
            integration_key = zm_manager._zm_integration_key(),
        ).first()
        
        if not zm_entity:
            _ = self._create_zm_entity(
                run_state_name_label_dict = new_state_values_dict,
                result = result,
            )
        
        zm_run_state_sensor = Sensor.objects.filter_by_integration_key(
            integration_key = zm_manager._zm_run_state_integration_key()
        ).select_related('entity_state').first()

        if not zm_run_state_sensor:
            result.error_list.append( 'Missing ZoneMinder sensor for ZM state.' )
            return

        entity_state = zm_run_state_sensor.entity_state
        new_state_values = new_state_values_dict.keys()
        existing_state_values_dict = entity_state.value_range_dict
        existing_state_values = existing_state_values_dict.keys()

        if existing_state_values != new_state_values:
            entity_state.value_range_dict = new_state_values_dict
            entity_state.save()
            result.info_list.append(
                f'Updated ZM state values to: {new_state_values_dict}'
            )

        return

    def _sync_monitors( self, result : IntegrationSyncResult ):
        """Sync monitors and return the list of newly-created monitor
        entities (for the caller to feed into
        group_entities_for_placement). Updates to existing entities
        do not contribute — they don't need re-placement."""
        integration_key_to_monitor = self._fetch_zm_monitors( result = result )
        result.info_list.append( f'Found {len(integration_key_to_monitor)} current ZM monitors.' )

        integration_key_to_entity = self._get_existing_zm_monitor_entities( result = result )
        result.info_list.append( f'Found {len(integration_key_to_entity)} existing ZM items.' )

        # Issue #281 reconnect pre-pass (framework-level). Any
        # disconnected entity whose previous identity matches an
        # unmatched upstream monitor is reconnected in place and
        # added to integration_key_to_entity, so the main loop
        # below treats it as primary-matched without any
        # reconnect-aware branching.
        self.reconnect_disconnected_items(
            integration_key_to_upstream = integration_key_to_monitor,
            integration_key_to_entity = integration_key_to_entity,
            result = result,
        )

        created_entities = []
        for integration_key, zm_monitor in integration_key_to_monitor.items():
            entity = integration_key_to_entity.get( integration_key )
            if entity:
                self._update_entity( entity = entity,
                                     zm_monitor = zm_monitor,
                                     result = result )
            else:
                entity = self._create_monitor_entity( zm_monitor = zm_monitor,
                                                      result = result )
                created_entities.append( entity )
            continue

        for integration_key, entity in integration_key_to_entity.items():
            if integration_key not in integration_key_to_monitor:
                self._remove_entity( entity = entity,
                                     result = result )
            continue

        return created_entities

    def _rebuild_integration_components( self,
                                         entity   : Entity,
                                         upstream : ZmMonitor,
                                         result   : IntegrationSyncResult ):
        """Issue #281: dispatch to the ZoneMinder monitor-entity
        converter with the existing-entity parameter set, so the
        converter repopulates integration-owned components on the
        previously-disconnected entity rather than creating a fresh
        one."""
        self._create_monitor_entity(
            zm_monitor = upstream,
            result = result,
            entity = entity,
        )
        return

    def _fetch_zm_monitors( self, result : IntegrationSyncResult ) -> Dict[ IntegrationKey, ZmMonitor ]:
        zm_manager = self.zm_manager()
        
        logger.debug( 'Getting current ZM monitors.' )
        integration_key_to_monitor = dict()
        for zm_monitor in zm_manager.get_zm_monitors( force_load = True ):
            integration_key = zm_manager._to_integration_key(
                prefix = zm_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            )
            integration_key_to_monitor[integration_key] = zm_monitor
            continue

        return integration_key_to_monitor
    
    def _get_existing_zm_monitor_entities( self, result : IntegrationSyncResult ) -> Dict[IntegrationKey, Entity]:
        logger.debug( 'Getting existing ZM entities.' )
        integration_key_to_entity = dict()
        
        entity_queryset = Entity.objects.filter( integration_id = ZmMetaData.integration_id )
        for entity in entity_queryset:
            integration_key = entity.integration_key
            if not integration_key:
                result.error_list.append( f'ZM item found without integration name: {entity}' )
                mock_monitor_id = 1000000 + entity.id  # We need a (unique) placeholder (will remove later)
                integration_key = IntegrationKey(
                    integration_id = ZmMetaData.integration_id,
                    integration_name = str( mock_monitor_id ),
                )
            if integration_key.integration_name.startswith(
                    self.zm_manager().ZM_MONITOR_INTEGRATION_NAME_PREFIX ):
                integration_key_to_entity[integration_key] = entity
            continue
        
        return integration_key_to_entity

    def _create_zm_entity( self,
                           run_state_name_label_dict  : Dict[ str, str ],
                           result                     : IntegrationSyncResult ):
        zm_manager = self.zm_manager()

        with transaction.atomic():
            zm_entity = Entity(
                name = zm_manager.ZM_ENTITY_NAME,
                entity_type_str = str(EntityType.SERVICE),
                can_user_delete = ZmMetaData.allow_entity_deletion,
            )
            zm_entity.integration_key = zm_manager._zm_integration_key()
            zm_entity.save()

            HiModelHelper.create_discrete_controller(
                entity = zm_entity,
                integration_key = zm_manager._zm_run_state_integration_key(),
                name = f'{zm_entity.name} Run State',
                name_label_dict = run_state_name_label_dict,
            )

        # The singleton ZM service entity isn't a placement candidate
        # (already attached to the integration root) — surface as an
        # info note rather than as a created_list entry so it doesn't
        # inflate the count of placeable monitors.
        result.info_list.append( f'Created ZM service item: {zm_entity}' )
        return zm_entity
            
    def _create_monitor_entity( self,
                                zm_monitor  : ZmMonitor,
                                result      : IntegrationSyncResult,
                                entity      : Optional[Entity] = None ) -> Entity:
        """
        Create or repopulate the integration-owned components for a
        ZoneMinder monitor. When ``entity`` is None (the standard
        import path), a fresh Entity is created. When ``entity`` is
        provided (the auto-reconnect path from Issue #281), the
        integration-owned fields on that entity are repopulated; the
        entity's ``name`` is deliberately preserved because the user
        may have edited it before/after the intervening disconnect.
        """
        zm_manager = self.zm_manager()

        with transaction.atomic():
            entity_integration_key = zm_manager._to_integration_key(
                prefix = zm_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            )

            if entity is None:
                entity = Entity(
                    name = zm_monitor.name(),
                    entity_type_str = str(EntityType.CAMERA),
                )

            # Integration-owned: re-applied on both fresh-create and
            # reconnect so the entity reflects current upstream state.
            entity.integration_key = entity_integration_key
            entity.can_user_delete = ZmMetaData.allow_entity_deletion
            entity.has_video_stream = True
            entity.save()

            movement_sensor = HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_key = zm_manager._to_integration_key(
                    prefix = zm_manager.MOVEMENT_SENSOR_PREFIX,
                    zm_monitor_id = zm_monitor.id(),
                ),
                provides_video_stream = True,
            )
            HiModelHelper.create_discrete_controller(
                entity = entity,
                integration_key = zm_manager._to_integration_key(
                    prefix = zm_manager.MONITOR_FUNCTION_SENSOR_PREFIX,
                    zm_monitor_id = zm_monitor.id(),
                ),
                name = f'{entity.name} Function',
                name_label_dict = self.MONITOR_FUNCTION_NAME_LABEL_DICT,
            )
            
            if zm_manager.should_add_alarm_events:
                HiModelHelper.create_movement_event_definition(
                    name = f'{movement_sensor.name} Alarm',
                    entity_state = movement_sensor.entity_state,
                    integration_key = zm_manager._to_integration_key(
                        prefix = zm_manager.MOVEMENT_EVENT_PREFIX,
                        zm_monitor_id = zm_monitor.id(),
                    ),
                )
                
        result.created_list.append( entity.name )
        return entity

    def _update_entity( self,
                        entity      : Entity,
                        zm_monitor  : ZmMonitor,
                        result      : IntegrationSyncResult ):
        if entity.name != zm_monitor.name():
            old_name = entity.name
            entity.name = zm_monitor.name()
            entity.save()
            # Surface the rename so the operator sees both names.
            result.updated_list.append( f'{old_name} → {entity.name}' )
        return
    
    def _remove_entity( self,
                        entity  : Entity,
                        result  : IntegrationSyncResult ):
        """
        Remove an entity that no longer exists in the ZoneMinder integration.
        
        Uses intelligent deletion that preserves user-created data.
        
        TODO: Should we remove the EventDefinitions that were auto-created (with integration key)?
        """
        self._remove_entity_intelligently(entity, result)
        return
