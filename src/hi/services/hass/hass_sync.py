import logging
from typing import Dict, List, Optional

from django.db import transaction

from hi.apps.entity.models import Entity

from hi.apps.entity.entity_placement import (
    EntityPlacementInput,
    EntityPlacementItem,
    EntityPlacementGroup,
)

from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from .hass_converter import HassConverter
from .hass_models import HassDevice
from .hass_mixins import HassMixin
from .hass_metadata import HassMetaData

logger = logging.getLogger(__name__)


class HassSynchronizer( IntegrationSynchronizer, HassMixin ):

    def get_description(self, is_initial_import: bool) -> Optional[str]:
        if is_initial_import:
            return 'Only items matching your Allowed Item Types setting will be imported.'
        return 'Only items matching your Allowed Item Types setting are compared.'

    def _sync_impl( self, is_initial_import: bool ) -> IntegrationSyncResult:
        hass_manager = self.hass_manager()
        result = IntegrationSyncResult(
            title = self.get_result_title( is_initial_import = is_initial_import ),
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

        import_allowlist = hass_manager.import_allowlist
        hass_device_id_to_device = HassConverter.hass_states_to_hass_devices(
            hass_entity_id_to_state = hass_entity_id_to_state,
            import_allowlist = import_allowlist,
        )
        result.info_list.append( f'Found {len(hass_device_id_to_device)} current Home Assistant devices.' )

        if import_allowlist:
            total_states = len( hass_entity_id_to_state )
            imported_states = sum(
                len( device.hass_state_list )
                for device in hass_device_id_to_device.values()
            )
            skipped_count = total_states - imported_states
            if skipped_count > 0:
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

        # Track newly-created entities only — existing-entity updates
        # don't need re-placement and shouldn't surface in the
        # dispatcher modal (refresh-with-no-new-items must produce
        # an empty sync result).
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

        if created_entities:
            result.placement_input = self.group_entities_for_placement(
                entities = created_entities,
            )
        return result

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
        self._remove_entity_intelligently(entity, result, 'HASS')
        return

    def group_entities_for_placement( self, entities ) -> EntityPlacementInput:
        """Group HASS entities by Hi-side entity_type_str.

        HASS uses no ungrouped bucket — every entity has a type.
        Groups are ordered by their label alphabetically for stable
        presentation. Falls back to an 'Other' bucket for entities
        without a recorded type."""
        type_to_items: Dict[str, List[EntityPlacementItem]] = {}
        for entity in entities:
            type_label = str( entity.entity_type_str or 'Other' )
            type_to_items.setdefault( type_label, [] ).append(
                EntityPlacementItem(
                    key = self._placement_item_key( entity = entity ),
                    label = entity.name,
                    entity = entity,
                )
            )
            continue
        groups = [
            EntityPlacementGroup( label = label, items = type_to_items[label] )
            for label in sorted( type_to_items.keys() )
        ]
        return EntityPlacementInput( groups = groups )
