import logging
from typing import Dict, List, Optional

from asgiref.sync import sync_to_async
from django.db import transaction

from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoSnapshot

from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.connector.sync_check import IntegrationSyncCheck, SyncDelta
from hi.integrations.connector.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from .hass_controller import HassController
from .hass_converter import HassConverter
from .hass_manager import HassManager
from .hass_models import HassDevice
from .hass_mixins import HassMixin
from .hass_metadata import HassMetaData
from .monitors import HassMonitor

logger = logging.getLogger(__name__)


class HassConnector( IntegrationConnector, HassMixin ):

    def get_integration_metadata(self):
        return HassMetaData

    def get_monitor(self) -> HassMonitor:
        return HassMonitor()

    def get_controller(self) -> HassController:
        return HassController()

    def get_health_status_provider(self) -> HealthStatusProvider:
        return HassManager()

    def get_entity_video_snapshot(self, entity: Entity) -> Optional[VideoSnapshot]:
        if not entity.has_video_snapshot:
            return None
        if entity.integration_id != HassMetaData.integration_id:
            return None

        hass_manager = HassManager()
        # ``Entity.integration_name`` is the HassDevice device_id (an HI
        # grouping construct), not the HA state id the attrs cache is
        # keyed by. The manager bridges the two via a sync-time-built
        # map of HI Entity.id -> camera-domain HA state id.
        ha_state_id = hass_manager.get_ha_state_id_for_entity( entity )
        if not ha_state_id:
            return None

        attrs = hass_manager.get_latest_attrs( ha_state_id )
        if not attrs:
            return None

        entity_picture = attrs.get( 'entity_picture' )
        if not entity_picture:
            return None

        # Some HA integrations emit an absolute URL; pass those
        # through unchanged. Relative paths get the HA base prefix.
        if entity_picture.startswith( ('http://', 'https://') ):
            source_url = entity_picture
        else:
            client = hass_manager.hass_client
            if not client:
                return None
            source_url = f'{client.api_base_url}{entity_picture}'

        return VideoSnapshot( source_url = source_url )

    def get_description(self, is_initial_connect: bool) -> Optional[str]:
        if is_initial_connect:
            return 'Only items matching your Allowed Item Types setting will be imported.'
        return 'Only items matching your Allowed Item Types setting are compared.'

    async def check_needs_sync(self) -> Optional[SyncDelta]:
        """Issue #283 — sync-check probe for Home Assistant.

        Fetches the same ``/api/states`` payload the periodic monitor
        uses, applies the configured Allowed Item Types include
        filter (so the upstream key set matches what Refresh would
        actually import — not what HA exposes raw), then compares against the
        IntegrationKeys of HA-attached HI entities.

        Convention matched to
        ``HassConverter.hass_device_to_integration_key``: each
        aggregated HassDevice maps to one IntegrationKey, which is
        what Refresh stores on the corresponding HI entity. Routing
        the upstream side through the same converter helper means
        the comparison automatically picks up whatever canonicalization
        ``IntegrationKey`` applies. Adds/removes only.
        """
        hass_manager = await self.hass_manager_async()
        if hass_manager is None:
            return None
        hass_entity_id_to_state = await hass_manager.fetch_hass_states_from_api_async(
            verbose = False,
        )
        include_filter = hass_manager.include_filter
        hass_device_id_to_device = HassConverter.hass_states_to_hass_devices(
            hass_entity_id_to_state = hass_entity_id_to_state,
            include_filter = include_filter,
        )
        upstream_keys = {
            HassConverter.hass_device_to_integration_key( hass_device )
            for hass_device in hass_device_id_to_device.values()
        }
        current_keys = await sync_to_async( self._get_current_integration_keys )()
        return IntegrationSyncCheck.compute_delta(
            upstream_keys = upstream_keys,
            current_keys = current_keys,
        )

    @staticmethod
    def _get_current_integration_keys() -> set:
        return {
            IntegrationKey(
                integration_id = integration_id,
                integration_name = integration_name,
            )
            for integration_id, integration_name in Entity.objects.filter(
                integration_id = HassMetaData.integration_id,
            ).values_list( 'integration_id', 'integration_name' )
        }

    def post_sync(self, result):
        hass_manager = self.hass_manager()
        if hass_manager is None:
            return
        hass_manager.reload()
        return

    def _sync_impl( self, is_initial_connect: bool ) -> IntegrationSyncResult:
        hass_manager = self.hass_manager()
        result = IntegrationSyncResult(
            title = self.get_result_title( is_initial_connect = is_initial_connect ),
        )

        hass_client = hass_manager.hass_client
        if not hass_client:
            logger.debug( 'Home Assistant client not created. Home Assistant integration disabled?' )
            result.error_list.append( 'Sync problem. Home Assistant integration disabled?' )
            return result

        hass_entity_id_to_state = hass_manager.fetch_hass_states_from_api()
        result.info_list.append( f'Found {len(hass_entity_id_to_state)} current Home Assistant states.' )

        integration_key_to_entity = self._get_existing_hass_entities( result = result )
        result.info_list.append( f'Found {len(integration_key_to_entity)} existing Home Assistant items.' )

        include_filter = hass_manager.include_filter
        hass_device_id_to_device = HassConverter.hass_states_to_hass_devices(
            hass_entity_id_to_state = hass_entity_id_to_state,
            include_filter = include_filter,
        )
        result.info_list.append( f'Found {len(hass_device_id_to_device)} current Home Assistant devices.' )

        if include_filter:
            total_states = len( hass_entity_id_to_state )
            imported_states = sum(
                len( device.hass_state_list )
                for device in hass_device_id_to_device.values()
            )
            skipped_count = total_states - imported_states
            if skipped_count > 0:
                result.items_filtered_count = skipped_count
                result.info_list.append(
                    f'Filtered {skipped_count} states not matching the Allowed Item Types.'
                )
                result.footer_message = (
                    'Not seeing all your Home Assistant items? '
                    'Check the "Allowed Item Types" in the Home Assistant '
                    'integration settings to add more domains or device classes.'
                )

        integration_key_to_hass_device = {
            HassConverter.hass_device_to_integration_key( hass_device ): hass_device
            for hass_device in hass_device_id_to_device.values()
        }

        # Issue #281 reconnect pre-pass (framework-level). Any
        # disconnected entity whose previous identity matches an
        # unmatched upstream device is reconnected in place and
        # added to integration_key_to_entity, so the main loop below
        # treats it as primary-matched without any reconnect-aware
        # branching.
        self.reconnect_disconnected_items(
            integration_key_to_upstream = integration_key_to_hass_device,
            integration_key_to_entity = integration_key_to_entity,
            result = result,
        )

        # Track newly-created entities only — existing-entity updates
        # don't need re-placement and shouldn't surface in the
        # placement modal (refresh-with-no-new-items must produce
        # an empty sync result). Reconnected entities are also
        # excluded: their layout/collection memberships are preserved
        # by reconnect (Part 3 contract) so they don't need placement.
        created_entities: List[Entity] = []

        with transaction.atomic():
            for integration_key, hass_device in integration_key_to_hass_device.items():
                entity = integration_key_to_entity.get( integration_key )
                if entity:
                    self._update_entity( entity = entity,
                                         hass_device = hass_device,
                                         result = result )
                else:
                    entity = self._create_entity( hass_device = hass_device,
                                                  result = result )
                    created_entities.append( entity )
                continue

            for integration_key, entity in integration_key_to_entity.items():
                if integration_key not in integration_key_to_hass_device:
                    self._remove_entity( entity = entity,
                                         result = result )
                continue

        result.created_entities = created_entities
        return result

    def _rebuild_integration_components( self,
                                         entity   : Entity,
                                         upstream : HassDevice,
                                         result   : IntegrationSyncResult ):
        """Issue #281: dispatch to the HASS converter with the
        existing-entity parameter set, so the converter repopulates
        integration-owned components on the previously-disconnected
        entity rather than creating a fresh one."""
        HassConverter.create_models_for_hass_device(
            hass_device = upstream,
            add_alarm_events = self.hass_manager().should_add_alarm_events,
            entity = entity,
        )
        return

    def _get_existing_hass_entities( self, result : IntegrationSyncResult ) -> Dict[ IntegrationKey, Entity ]:
        logger.debug( 'Getting existing HAss entities.' )
        integration_key_to_entity = dict()

        entity_queryset = Entity.objects.filter( integration_id = HassMetaData.integration_id )
        for entity in entity_queryset:
            integration_key = entity.integration_key
            if not integration_key:
                result.error_list.append( f'Item found without valid Home Assistant Id: {entity}' )
                mock_hass_device_id = 1000000 + entity.id  # We need a (unique) placeholder for removals
                integration_key = IntegrationKey(
                    integration_id = HassMetaData.integration_id,
                    integration_name = str( mock_hass_device_id ),
                )
            integration_key_to_entity[integration_key] = entity
            continue

        return integration_key_to_entity

    def _create_entity( self,
                        hass_device  : HassDevice,
                        result       : IntegrationSyncResult ) -> Entity:
        entity = HassConverter.create_models_for_hass_device(
            hass_device = hass_device,
            add_alarm_events = self.hass_manager().should_add_alarm_events,
        )
        result.created_list.append( entity.name )
        return entity

    def _update_entity( self,
                        entity       : Entity,
                        hass_device  : HassDevice,
                        result       : IntegrationSyncResult ):
        # update_models_for_hass_device returns a list of change
        # description strings — non-empty means at least one
        # operator-visible change was made.
        change_messages = HassConverter.update_models_for_hass_device(
            entity = entity,
            hass_device = hass_device,
        )
        if change_messages:
            result.updated_list.append( entity.name )
        return

    def _remove_entity( self,
                        entity   : Entity,
                        result   : IntegrationSyncResult ):
        """
        Remove an entity that no longer exists in the HASS integration.

        Uses intelligent deletion that preserves user-created data.
        """
        self._remove_entity_intelligently(entity, result)
        return

