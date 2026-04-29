import logging
from typing import Dict, Optional

from django.db import transaction

from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.models import Entity

from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.transient_models import IntegrationKey

from .hass_converter import HassConverter
from .hass_models import HassDevice
from .hass_mixins import HassMixin
from .hass_metadata import HassMetaData

logger = logging.getLogger(__name__)


class HassSynchronizer( IntegrationSynchronizer, HassMixin ):

    RESULT_TITLE = 'Home Assistant Import Result'

    def get_result_title(self) -> str:
        return self.RESULT_TITLE

    def get_description(self, is_initial_import: bool) -> Optional[str]:
        if is_initial_import:
            return (
                'Import will pull in every entity from your Home'
                ' Assistant instance whose domain is on your configured'
                ' import allowlist. Entities outside the allowlist are'
                ' skipped and will not appear here.'
            )
        return (
            'Refresh reconciles already-imported entities with the'
            ' current state of your Home Assistant instance: new'
            ' entities (within the allowlist) are added, existing'
            ' entities are updated in place, and entities no longer'
            ' present upstream are removed.'
        )

    def _sync_impl( self ) -> ProcessingResult:
        hass_manager = self.hass_manager()
        result = ProcessingResult( title = self.RESULT_TITLE )

        hass_client = hass_manager.hass_client
        if not hass_client:
            logger.debug( 'Home Assistant client not created. Home Assistant integration disabled?' )
            result.error_list.append( 'Sync problem. Home Assistant integration disabled?' )
            return result

        hass_entity_id_to_state = hass_manager.fetch_hass_states_from_api()
        result.message_list.append( f'Found {len(hass_entity_id_to_state)} current Home Assistant states.' )

        integration_key_to_entity = self._get_existing_hass_entities( result = result )
        result.message_list.append( f'Found {len(integration_key_to_entity)} existing Home Assistant entities.' )

        import_allowlist = hass_manager.import_allowlist
        hass_device_id_to_device = HassConverter.hass_states_to_hass_devices(
            hass_entity_id_to_state = hass_entity_id_to_state,
            import_allowlist = import_allowlist,
        )
        result.message_list.append( f'Found {len(hass_device_id_to_device)} current Home Assistant devices.' )

        if import_allowlist:
            total_states = len( hass_entity_id_to_state )
            imported_states = sum(
                len( device.hass_state_list )
                for device in hass_device_id_to_device.values()
            )
            skipped_count = total_states - imported_states
            if skipped_count > 0:
                result.message_list.append(
                    f'Filtered {skipped_count} states not matching the Import Allowlist.'
                )
                result.footer_message = (
                    'Not seeing all your Home Assistant items? '
                    'Check the "Import Allowlist" in the Home Assistant '
                    'integration settings to add more domains or device classes.'
                )

        integration_key_to_hass_device = {
            HassConverter.hass_device_to_integration_key( hass_device ): hass_device
            for hass_device in hass_device_id_to_device.values()
        }
    
        with transaction.atomic():
            for integration_key, hass_device in integration_key_to_hass_device.items():
                entity = integration_key_to_entity.get( integration_key )
                if entity:
                    self._update_entity( entity = entity,
                                         hass_device = hass_device,
                                         result = result )
                else:
                    self._create_entity( hass_device = hass_device,
                                         result = result )
                continue

            for integration_key, entity in integration_key_to_entity.items():
                if integration_key not in integration_key_to_hass_device:
                    self._remove_entity( entity = entity,
                                         result = result )
                continue
        
        return result

    def _get_existing_hass_entities( self, result : ProcessingResult ) -> Dict[ IntegrationKey, Entity ]:
        logger.debug( 'Getting existing HAss entities.' )
        integration_key_to_entity = dict()

        entity_queryset = Entity.objects.filter( integration_id = HassMetaData.integration_id )
        for entity in entity_queryset:
            integration_key = entity.integration_key
            if not integration_key:
                result.error_list.append( f'Entity found without valid Home Assistant Id: {entity}' )
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
                        result       : ProcessingResult ):
        entity = HassConverter.create_models_for_hass_device(
            hass_device = hass_device,
            add_alarm_events = self.hass_manager().should_add_alarm_events,
        )
        result.message_list.append( f'Created Home Assistant entity: {entity}' )
        return
    
    def _update_entity( self,
                        entity       : Entity,
                        hass_device  : HassDevice,
                        result       : ProcessingResult ):

        message_list = HassConverter.update_models_for_hass_device(
            entity = entity,
            hass_device = hass_device,
        )
        for message in message_list:
            result.message_list.append( message )
            continue
        return
    
    def _remove_entity( self,
                        entity   : Entity,
                        result   : ProcessingResult ):
        """
        Remove an entity that no longer exists in the HASS integration.
        
        Uses intelligent deletion that preserves user-created data.
        """
        self._remove_entity_intelligently(entity, result, 'HASS')
        return

    
