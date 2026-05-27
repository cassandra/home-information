import logging
from .pyzm_client.helpers.Monitor import Monitor as ZmMonitor
from typing import Dict, Optional

from asgiref.sync import sync_to_async
from django.db import transaction

from hi.apps.entity.enums import EntityType, VideoStreamType, VideoStreamMode
from hi.apps.entity.constants import VideoStreamMetadataKeys
from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoSnapshot, VideoStream
from hi.apps.sense.models import Sensor
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.apps.model_helper import HiModelHelper

from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.connector.sync_check import IntegrationSyncCheck, SyncDelta
from hi.integrations.connector.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from .constants import ZmDetailKeys
from .monitors import ZoneMinderMonitor
from .zm_controller import ZoneMinderController
from .zm_manager import ZoneMinderManager
from .zm_metadata import ZmMetaData
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZmConnector( IntegrationConnector, ZoneMinderMixin ):

    def get_metadata(self):
        return ZmMetaData

    def get_monitor(self) -> ZoneMinderMonitor:
        return ZoneMinderMonitor()

    def get_controller(self) -> ZoneMinderController:
        return ZoneMinderController()

    def get_health_status_provider(self) -> HealthStatusProvider:
        return ZoneMinderManager()

    def get_entity_video_snapshot(self, entity: Entity) -> Optional[VideoSnapshot]:
        """Return a fresh still frame for the ZoneMinder monitor backing
        this entity (``nph-zms?mode=single``). Returns None when the
        entity isn't a ZM monitor or the integration_name can't be
        parsed."""
        if not entity.has_video_snapshot:
            return None

        if not ( entity.integration_id == ZmMetaData.integration_id
                 and entity.integration_name
                 and entity.integration_name.startswith(
                     self.zm_manager().ZM_MONITOR_INTEGRATION_NAME_PREFIX )):
            return None

        try:
            monitor_id = int( entity.integration_name.split('.')[1] )
        except ( IndexError, ValueError ):
            logger.warning(
                f'Could not parse monitor ID from entity integration name: '
                f'{entity.integration_name}'
            )
            return None

        return VideoSnapshot(
            source_url = self.zm_manager().get_video_snapshot_url( monitor_id ),
            metadata = { 'monitor_id': monitor_id },
        )

    def get_entity_video_stream(self, entity: Entity) -> Optional[VideoStream]:
        """Get entity's primary video stream (typically live)"""
        if not entity.has_video_stream:
            return None

        # Check if this is a ZoneMinder camera entity
        if (entity.integration_id == ZmMetaData.integration_id
                and entity.integration_name
                and entity.integration_name.startswith(
                    self.zm_manager().ZM_MONITOR_INTEGRATION_NAME_PREFIX)):

            # Extract monitor ID from integration name (format: "monitor.{id}")
            try:
                monitor_id = int(entity.integration_name.split('.')[1])
                video_url = self.zm_manager().get_video_stream_url(monitor_id)

                return VideoStream(
                    stream_type=VideoStreamType.MJPEG,
                    source_url=video_url,
                    metadata={
                        'monitor_id': monitor_id,
                        VideoStreamMetadataKeys.STREAM_MODE: str(VideoStreamMode.LIVE)
                    }
                )
            except (IndexError, ValueError):
                logger.warning(f"Could not parse monitor ID from entity integration name:"
                               f" {entity.integration_name}")

        return None

    def get_sensor_response_event_snapshot_url(
            self,
            sensor_response: SensorResponse) -> Optional[str]:
        """Per-event snapshot URL for a ZM SensorResponse. Reads the
        event_id from detail_attrs (where the monitor stores it on
        every START / END row), builds the portal URL fresh each
        call so an operator-side portal-URL change auto-heals every
        historical row."""
        if not sensor_response.has_event_video_snapshot:
            return None
        event_id_fieldname = ZmDetailKeys.EVENT_ID_ATTR_NAME
        if not sensor_response.detail_attrs:
            return None
        raw_event_id = sensor_response.detail_attrs.get(event_id_fieldname)
        if raw_event_id is None:
            return None
        try:
            event_id = int(raw_event_id)
        except (ValueError, TypeError):
            logger.warning(
                'Could not parse event ID from ZM sensor response: %s',
                sensor_response.detail_attrs,
            )
            return None
        return self.zm_manager().get_event_snapshot_url(event_id=event_id)

    def get_sensor_response_video_stream(
            self,
            sensor_response: SensorResponse) -> Optional[VideoStream]:
        """Get video stream from sensor response (recorded events)"""
        # if not sensor_response.has_event_video_clip:
        #     return None

        event_id_fieldname = ZmDetailKeys.EVENT_ID_ATTR_NAME

        # Check if this sensor response has an event ID in its detail_attrs
        if (sensor_response.detail_attrs
                and event_id_fieldname in sensor_response.detail_attrs):

            try:
                event_id = int(sensor_response.detail_attrs[event_id_fieldname])
                video_url = self.zm_manager().get_event_video_stream_url(event_id)

                # Extract duration from detail_attrs if available
                metadata = {
                    event_id_fieldname: event_id,
                    VideoStreamMetadataKeys.STREAM_MODE: str(VideoStreamMode.RECORDED)
                }

                # Look for duration in detail_attrs using the ZoneMinder constant
                if ZmDetailKeys.DURATION_SECS in sensor_response.detail_attrs:
                    try:
                        duration_secs = float(sensor_response.detail_attrs[ZmDetailKeys.DURATION_SECS])
                        metadata[VideoStreamMetadataKeys.DURATION_SECS] = int(duration_secs)
                    except (ValueError, TypeError):
                        logger.debug(f"Could not parse duration from sensor response:"
                                     f" {sensor_response.detail_attrs.get(ZmDetailKeys.DURATION_SECS)}")

                return VideoStream(
                    stream_type=VideoStreamType.MJPEG,
                    source_url=video_url,
                    metadata=metadata
                )
            except (ValueError, TypeError):
                logger.warning(f"Could not parse event ID from sensor response:"
                               f" {sensor_response.detail_attrs}")

        return None

    MONITOR_FUNCTION_NAME_LABEL_DICT = {
        'None': 'None',
        'Monitor': 'Monitor',
        'Modect': 'Modect',
        'Record': 'Record',
        'Mocord': 'Mocord',
        'Nodect': 'Nodect',
    }

    def get_sync_description(self, is_initial_connect: bool) -> Optional[str]:
        if is_initial_connect:
            return (
                'Each monitor becomes a camera with motion and'
                ' run-state sensors.'
            )
        return None

    async def check_needs_sync(self) -> Optional[SyncDelta]:
        """Issue #283 — sync-check probe for ZoneMinder.

        Fetches the current monitor list (cheap on a typical install
        — bounded by camera count), builds the upstream
        IntegrationKey set using the same prefix scheme as the live
        sync (``MONITOR.<id>``), and compares against the
        IntegrationKeys of monitor-shaped HI entities. The ZM service
        entity and run-state sensors are excluded from the
        comparison because they are not per-monitor and would
        otherwise look like permanent extras on the HI side.
        """
        zm_manager = await self.zm_manager_async()
        if zm_manager is None:
            return None
        prefix = zm_manager.ZM_MONITOR_INTEGRATION_NAME_PREFIX
        zm_monitors = await zm_manager.get_zm_monitors_async( force_load = True )
        upstream_keys = {
            zm_manager._to_integration_key(
                prefix = prefix,
                zm_monitor_id = zm_monitor.id(),
            )
            for zm_monitor in zm_monitors
        }
        current_keys = await sync_to_async( self._get_current_monitor_integration_keys )(
            prefix = prefix,
        )
        return IntegrationSyncCheck.compute_delta(
            upstream_keys = upstream_keys,
            current_keys = current_keys,
        )

    @staticmethod
    def _get_current_monitor_integration_keys( prefix : str ) -> set:
        return {
            IntegrationKey(
                integration_id = integration_id,
                integration_name = integration_name,
            )
            for integration_id, integration_name in Entity.objects.filter(
                integration_id = ZmMetaData.integration_id,
                integration_name__startswith = prefix,
            ).values_list( 'integration_id', 'integration_name' )
        }

    def _sync_impl( self, is_initial_connect: bool ) -> IntegrationSyncResult:
        result = IntegrationSyncResult(
            title = self.get_result_title( is_initial_connect = is_initial_connect ),
        )

        if not self.zm_manager().zm_client:
            logger.debug( 'ZoneMinder client not created. ZM integration disabled?' )
            result.error_list.append( 'Sync problem. ZM integration disabled?' )
            return result

        created_service_entity = self._sync_states( result = result )
        created_monitor_entities = self._sync_monitors( result = result )
        result.created_entities = [
            *( [ created_service_entity ] if created_service_entity else [] ),
            *created_monitor_entities,
        ]
        return result

    def _sync_states( self, result : IntegrationSyncResult ) -> Optional[Entity]:
        """Returns the freshly-created ZM service entity when this
        sync run had to create one; None otherwise. Caller appends
        the return value (when non-None) to ``result.created_entities``
        so the framework's placement step treats the service entity
        symmetrically with everything else created this run."""
        zm_manager = self.zm_manager()

        zm_run_state_list = zm_manager.get_zm_states( force_load = True )
        new_state_values_dict = { x.name(): x.name() for x in zm_run_state_list }

        zm_entity = Entity.objects.filter_by_integration_key(
            integration_key = zm_manager._zm_integration_key(),
        ).first()

        created_service_entity = None
        if not zm_entity:
            created_service_entity = self._create_zm_entity(
                run_state_name_label_dict = new_state_values_dict,
                result = result,
            )
        
        zm_run_state_sensor = Sensor.objects.filter_by_integration_key(
            integration_key = zm_manager._zm_run_state_integration_key()
        ).select_related('entity_state').first()

        if not zm_run_state_sensor:
            result.error_list.append( 'Missing ZoneMinder sensor for ZM state.' )
            return created_service_entity

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

        return created_service_entity

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

        # Service entity is surfaced in the result-modal Created
        # list so the user-facing count matches what got persisted.
        # It is intentionally absent from placement_input — that's
        # built separately from the monitor-entity list in
        # _sync_impl, so created_list and placement_input can
        # disagree where appropriate.
        result.created_list.append( zm_entity.name )
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
        is_fresh_create = entity is None
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
            entity.has_video_snapshot = True
            entity.save()

            movement_sensor = HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_key = zm_manager._to_integration_key(
                    prefix = zm_manager.MOVEMENT_SENSOR_PREFIX,
                    zm_monitor_id = zm_monitor.id(),
                ),
                provides_event_video_clip = True,
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

        # Only fresh creates contribute to created_list. The
        # reconnect path (entity supplied by caller) already gets
        # surfaced via reconnected_list in
        # reconnect_disconnected_items — appending here too would
        # double-count the row.
        if is_fresh_create:
            result.created_list.append( entity.name )
        return entity

    def _update_entity( self,
                        entity      : Entity,
                        zm_monitor  : ZmMonitor,
                        result      : IntegrationSyncResult ):
        """Refresh integration-owned components on an existing entity.

        ``entity.name`` is user-editable in HI's UI on ZM entities
        (``allow_internal_attributes`` defaults to True), so it's
        treated as user-owned after creation: this method does not
        touch it on update. ZM monitor renames upstream are not
        propagated; the operator's chosen name stays.
        """
        # Re-apply integration-owned capability flags. Every ZM
        # monitor is a camera, so both flags are unconditionally True;
        # the conditional save avoids spurious writes.
        update_fields = []
        if not entity.has_video_stream:
            entity.has_video_stream = True
            update_fields.append( 'has_video_stream' )
        if not entity.has_video_snapshot:
            entity.has_video_snapshot = True
            update_fields.append( 'has_video_snapshot' )
        if update_fields:
            entity.save( update_fields = update_fields )
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
