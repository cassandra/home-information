import logging
from typing import Dict, List, Optional

from asgiref.sync import sync_to_async
from django.db import transaction

from hi.apps.entity.enums import EntityType
from hi.apps.entity.entity_placement import (
    EntityPlacementGroup,
    EntityPlacementInput,
    EntityPlacementItem,
)
from hi.apps.entity.models import Entity
from hi.apps.model_helper import HiModelHelper

from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.sync_check import IntegrationSyncCheck, SyncDelta
from hi.integrations.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from .frigate_manager import FrigateManager
from .frigate_metadata import FrigateMetaData
from .frigate_mixins import FrigateMixin

logger = logging.getLogger(__name__)


class FrigateSynchronizer( IntegrationSynchronizer, FrigateMixin ):
    """Drives the Frigate Import / Refresh workflow.

    Mirrors ``ZoneMinderSynchronizer`` in role: pulls the upstream
    camera list from Frigate (via ``/api/config`` since Frigate has
    no dedicated cameras endpoint), reconciles it against existing
    HI entities by integration_key, creates / updates / removes as
    needed. Frigate v1 has no native moving stream (MJPEG/RTSP
    require go2rtc on the operator's end), so camera entities are
    created with ``has_video_snapshot`` + a non-zero
    ``video_snapshot_stream_fps`` rather than ``has_video_stream``."""

    CAMERA_SNAPSHOT_STREAM_FPS = 1.0

    def get_integration_metadata(self):
        return FrigateMetaData

    def get_description(self, is_initial_import : bool) -> Optional[ str ]:
        if is_initial_import:
            return (
                'Each Frigate camera becomes a HI camera entity with'
                ' motion and object-presence sensors.'
            )
        return None

    async def check_needs_sync(self) -> Optional[ SyncDelta ]:
        """Sync-check probe (Issue #283 protocol). Pulls the camera
        list from Frigate and compares its integration-key set against
        the keys of the existing camera-shaped HI entities."""
        frigate_manager = await self.frigate_manager_async()
        if frigate_manager is None or frigate_manager.frigate_client is None:
            return None
        prefix = FrigateManager.FRIGATE_CAMERA_INTEGRATION_NAME_PREFIX

        def _fetch_cameras():
            return frigate_manager.frigate_client.get_cameras()

        try:
            cameras = await sync_to_async( _fetch_cameras, thread_sensitive = True )()
        except Exception:
            logger.exception( 'Frigate check_needs_sync: failed to fetch cameras' )
            return None
        upstream_keys = {
            FrigateManager._to_integration_key(
                prefix = prefix,
                camera_name = camera[ 'name' ],
            )
            for camera in cameras
        }
        current_keys = await sync_to_async( self._get_current_camera_integration_keys )(
            prefix = prefix,
        )
        return IntegrationSyncCheck.compute_delta(
            upstream_keys = upstream_keys,
            current_keys = current_keys,
        )

    @staticmethod
    def _get_current_camera_integration_keys( prefix : str ) -> set:
        return {
            IntegrationKey(
                integration_id = integration_id,
                integration_name = integration_name,
            )
            for integration_id, integration_name in Entity.objects.filter(
                integration_id = FrigateMetaData.integration_id,
                integration_name__startswith = prefix,
            ).values_list( 'integration_id', 'integration_name' )
        }

    def _sync_impl( self, is_initial_import : bool ) -> IntegrationSyncResult:
        result = IntegrationSyncResult(
            title = self.get_result_title( is_initial_import = is_initial_import ),
        )
        frigate_manager = self.frigate_manager()
        if frigate_manager.frigate_client is None:
            result.error_list.append( 'Frigate client not available. Integration disabled?' )
            return result

        created_camera_entities = self._sync_cameras( result = result )
        if created_camera_entities:
            result.placement_input = self.group_entities_for_placement(
                entities = created_camera_entities,
            )
        return result

    def group_entities_for_placement( self, entities ) -> EntityPlacementInput:
        """Single 'Cameras' placement group: Frigate cameras usually
        share a wall-of-views layout, so 'all cameras → same place'
        is the right default. Operators can still drill into
        per-camera placement from the dispatcher."""
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
            groups = [ EntityPlacementGroup( label = 'Cameras', items = items ) ],
        )

    def _sync_cameras( self, result : IntegrationSyncResult ) -> List[ Entity ]:
        integration_key_to_camera = self._fetch_frigate_cameras( result = result )
        result.info_list.append(
            f'Found {len(integration_key_to_camera)} current Frigate cameras.'
        )

        integration_key_to_entity = self._get_existing_camera_entities( result = result )
        result.info_list.append(
            f'Found {len(integration_key_to_entity)} existing Frigate items.'
        )

        # Issue #281 reconnect pre-pass — any disconnected entity whose
        # previous identity matches an unmatched upstream camera is
        # reconnected in place and the main loop below treats it as
        # primary-matched.
        self.reconnect_disconnected_items(
            integration_key_to_upstream = integration_key_to_camera,
            integration_key_to_entity = integration_key_to_entity,
            result = result,
        )

        created_entities = []
        for integration_key, camera in integration_key_to_camera.items():
            entity = integration_key_to_entity.get( integration_key )
            if entity:
                self._update_entity( entity = entity,
                                     camera = camera,
                                     result = result )
            else:
                entity = self._create_camera_entity( camera = camera,
                                                     result = result )
                created_entities.append( entity )
            continue

        for integration_key, entity in integration_key_to_entity.items():
            if integration_key not in integration_key_to_camera:
                self._remove_entity( entity = entity, result = result )
            continue

        return created_entities

    def _rebuild_integration_components( self,
                                         entity   : Entity,
                                         upstream : dict,
                                         result   : IntegrationSyncResult ):
        """Issue #281: dispatch to the camera-entity converter with
        the existing-entity parameter set, so the converter repopulates
        integration-owned components on the previously-disconnected
        entity rather than creating a fresh one."""
        self._create_camera_entity(
            camera = upstream,
            result = result,
            entity = entity,
        )
        return

    def _fetch_frigate_cameras( self, result : IntegrationSyncResult ) -> Dict[ IntegrationKey, dict ]:
        frigate_manager = self.frigate_manager()
        prefix = FrigateManager.FRIGATE_CAMERA_INTEGRATION_NAME_PREFIX
        logger.debug( 'Getting current Frigate cameras.' )
        integration_key_to_camera = dict()
        cameras = frigate_manager.frigate_client.get_cameras()
        for camera in cameras:
            integration_key = FrigateManager._to_integration_key(
                prefix = prefix,
                camera_name = camera[ 'name' ],
            )
            integration_key_to_camera[ integration_key ] = camera
            continue
        return integration_key_to_camera

    def _get_existing_camera_entities( self,
                                       result : IntegrationSyncResult,
                                       ) -> Dict[ IntegrationKey, Entity ]:
        logger.debug( 'Getting existing Frigate entities.' )
        prefix = FrigateManager.FRIGATE_CAMERA_INTEGRATION_NAME_PREFIX
        integration_key_to_entity = dict()
        entity_queryset = Entity.objects.filter(
            integration_id = FrigateMetaData.integration_id,
        )
        for entity in entity_queryset:
            integration_key = entity.integration_key
            if not integration_key:
                result.error_list.append(
                    f'Frigate item found without integration name: {entity}'
                )
                mock_id = 1000000 + entity.id  # disambiguating placeholder
                integration_key = IntegrationKey(
                    integration_id = FrigateMetaData.integration_id,
                    integration_name = f'{prefix}.placeholder_{mock_id}',
                )
            if integration_key.integration_name.startswith( prefix + '.' ):
                integration_key_to_entity[ integration_key ] = entity
            continue
        return integration_key_to_entity

    def _create_camera_entity( self,
                               camera   : dict,
                               result   : IntegrationSyncResult,
                               entity   : Optional[ Entity ] = None ) -> Entity:
        """Create or repopulate the integration-owned components for
        a Frigate camera. ``entity is None`` is the fresh-import path;
        passing an existing ``entity`` is the auto-reconnect path
        (Issue #281), where integration-owned fields get refilled but
        the user-editable ``name`` is preserved across the
        intervening disconnect."""
        camera_name = camera[ 'name' ]
        # Frigate's camera key (snake_case) is the technical identifier;
        # the ``friendly_name`` on the per-camera config is the operator's
        # display label. Prefer it for the HI entity name and fall back
        # to the snake_case key when no friendly_name is set.
        camera_config = camera.get( 'config' ) or {}
        display_name = camera_config.get( 'friendly_name' ) or camera_name
        with transaction.atomic():
            entity_integration_key = FrigateManager._to_integration_key(
                prefix = FrigateManager.FRIGATE_CAMERA_INTEGRATION_NAME_PREFIX,
                camera_name = camera_name,
            )
            if entity is None:
                entity = Entity(
                    name = display_name,
                    entity_type_str = str( EntityType.CAMERA ),
                )

            # Integration-owned fields: re-applied on fresh-create and
            # on reconnect so the entity reflects current upstream state.
            entity.integration_key = entity_integration_key
            entity.can_user_delete = FrigateMetaData.allow_entity_deletion
            entity.has_video_stream = False
            entity.has_video_snapshot = True
            entity.video_snapshot_stream_fps = self.CAMERA_SNAPSHOT_STREAM_FPS
            entity.save()

            # Single sensor per camera — OBJECT_PRESENCE subsumes the
            # "is motion happening" signal (any non-OBJECT_NONE value
            # implies motion + the class causing it). Frigate's data
            # model doesn't expose motion independent of object
            # detection, so a separate MOVEMENT sensor would always
            # mirror this one's state.
            object_presence_sensor = HiModelHelper.create_object_presence_sensor(
                entity = entity,
                integration_key = FrigateManager._to_integration_key(
                    prefix = FrigateManager.OBJECT_PRESENCE_SENSOR_PREFIX,
                    camera_name = camera_name,
                ),
                provides_event_video_clip = True,
                provides_event_video_snapshot = True,
            )

            if self.frigate_manager().should_add_alarm_events:
                HiModelHelper.create_object_presence_event_definition(
                    name = f'{object_presence_sensor.name} Alarm',
                    entity_state = object_presence_sensor.entity_state,
                    integration_key = FrigateManager._to_integration_key(
                        prefix = FrigateManager.OBJECT_PRESENCE_EVENT_PREFIX,
                        camera_name = camera_name,
                    ),
                )

        result.created_list.append( entity.name )
        return entity

    def _update_entity( self,
                        entity  : Entity,
                        camera  : dict,
                        result  : IntegrationSyncResult ):
        """Refresh integration-owned capability flags on an existing
        camera entity. Like the ZM integration, ``entity.name`` is
        treated as user-owned after creation: this method does not
        touch it on update."""
        update_fields = []
        if entity.has_video_stream:
            entity.has_video_stream = False
            update_fields.append( 'has_video_stream' )
        if not entity.has_video_snapshot:
            entity.has_video_snapshot = True
            update_fields.append( 'has_video_snapshot' )
        if entity.video_snapshot_stream_fps != self.CAMERA_SNAPSHOT_STREAM_FPS:
            entity.video_snapshot_stream_fps = self.CAMERA_SNAPSHOT_STREAM_FPS
            update_fields.append( 'video_snapshot_stream_fps' )
        if update_fields:
            entity.save( update_fields = update_fields )
        return

    def _remove_entity( self,
                        entity  : Entity,
                        result  : IntegrationSyncResult ):
        """Remove an entity that no longer exists in Frigate. Uses
        ``_remove_entity_intelligently`` to preserve user-attached
        data when present."""
        self._remove_entity_intelligently( entity, result )
        return
