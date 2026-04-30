import logging
from .pyzm_client.helpers.Monitor import Monitor as ZmMonitor
from typing import Dict, Optional

from django.db import transaction

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor

from hi.apps.model_helper import HiModelHelper

from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.sync_result import (
    IntegrationSyncResult,
    SyncResultItem,
    SyncResultItemGroup,
)
from hi.integrations.transient_models import IntegrationKey

from .zm_metadata import ZmMetaData
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZoneMinderSynchronizer( IntegrationSynchronizer, ZoneMinderMixin ):

    RESULT_TITLE = 'ZM Import Result'

    MONITOR_FUNCTION_NAME_LABEL_DICT = {
        'None': 'None',
        'Monitor': 'Monitor',
        'Modect': 'Modect',
        'Record': 'Record',
        'Mocord': 'Mocord',
        'Nodect': 'Nodect',
    }

    def get_result_title(self) -> str:
        return self.RESULT_TITLE

    def get_description(self, is_initial_import: bool) -> Optional[str]:
        if is_initial_import:
            return (
                'Import will pull in each ZoneMinder monitor as a'
                ' camera entity, along with derived motion and'
                ' run-state sensors.'
            )
        return (
            'Refresh reconciles already-imported cameras with the'
            ' current set of ZoneMinder monitors: new monitors are'
            ' added, existing entities are updated in place, and'
            ' monitors no longer present upstream are removed.'
        )

    def _sync_impl( self ) -> IntegrationSyncResult:
        result = IntegrationSyncResult( title = self.RESULT_TITLE )

        if not self.zm_manager().zm_client:
            logger.debug( 'ZoneMinder client not created. ZM integration disabled?' )
            result.error_list.append( 'Sync problem. ZM integration disabled?' )
            return result

        self._sync_states( result = result )
        monitor_entities = self._sync_monitors( result = result )

        # Single "Monitors" group: ZM monitors typically share a view,
        # and the operator's first instinct is "all cameras → same
        # place." The dispatcher's drill-down still allows per-monitor
        # placement when needed.
        if monitor_entities:
            items = [
                SyncResultItem(
                    key = self._sync_result_item_key( entity ),
                    label = entity.name,
                    entity = entity,
                )
                for entity in monitor_entities
            ]
            result.groups = [
                SyncResultItemGroup( label = 'Monitors', items = items )
            ]

        return result

    def _sync_result_item_key( self, entity : Entity ) -> str:
        integration_key = entity.integration_key
        if integration_key:
            return f'{integration_key.integration_id}:{integration_key.integration_name}'
        return f'entity:{entity.id}'

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
            result.message_list.append( f'Updated ZM state values to: {new_state_values_dict}' )

        return

    def _sync_monitors( self, result : IntegrationSyncResult ):
        """Sync monitors and return the list of imported (created or
        updated) monitor entities for grouping by the caller."""
        integration_key_to_monitor = self._fetch_zm_monitors( result = result )
        result.message_list.append( f'Found {len(integration_key_to_monitor)} current ZM monitors.' )

        integration_key_to_entity = self._get_existing_zm_monitor_entities( result = result )
        result.message_list.append( f'Found {len(integration_key_to_entity)} existing ZM entities.' )

        monitor_entities = []
        for integration_key, zm_monitor in integration_key_to_monitor.items():
            entity = integration_key_to_entity.get( integration_key )
            if entity:
                self._update_entity( entity = entity,
                                     zm_monitor = zm_monitor,
                                     result = result )
            else:
                entity = self._create_monitor_entity( zm_monitor = zm_monitor,
                                                      result = result )
            monitor_entities.append( entity )
            continue

        for integration_key, entity in integration_key_to_entity.items():
            if integration_key not in integration_key_to_monitor:
                self._remove_entity( entity = entity,
                                     result = result )
            continue

        return monitor_entities

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
                result.error_list.append( f'ZM entity found without integration name: {entity}' )
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

        result.message_list.append( f'Created ZM entity: {zm_entity}' )
        return zm_entity
            
    def _create_monitor_entity( self,
                                zm_monitor  : ZmMonitor,
                                result      : IntegrationSyncResult ) -> Entity:
        zm_manager = self.zm_manager()

        with transaction.atomic():
            entity_integration_key = zm_manager._to_integration_key(
                prefix = zm_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX,
                zm_monitor_id = zm_monitor.id(),
            )
            entity = Entity(
                name = zm_monitor.name(),
                entity_type_str = str(EntityType.CAMERA),
                can_user_delete = ZmMetaData.allow_entity_deletion,
                has_video_stream = True,
            )
            entity.integration_key = entity_integration_key
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
                
        result.message_list.append( f'Create new camera entity: {entity}' )
        return entity
    
    def _update_entity( self,
                        entity      : Entity,
                        zm_monitor  : ZmMonitor,
                        result      : IntegrationSyncResult ):

        if entity.name != zm_monitor.name():
            result.message_list.append(f'Name changed for {entity}. Setting to "{zm_monitor.name()}"')
            entity.name = zm_monitor.name()
            entity.save()
        else:
            result.message_list.append( f'No changes found for {entity}.' )
        return
    
    def _remove_entity( self,
                        entity  : Entity,
                        result  : IntegrationSyncResult ):
        """
        Remove an entity that no longer exists in the ZoneMinder integration.
        
        Uses intelligent deletion that preserves user-created data.
        
        TODO: Should we remove the EventDefinitions that were auto-created (with integration key)?
        """
        self._remove_entity_intelligently(entity, result, 'ZoneMinder')
        return
