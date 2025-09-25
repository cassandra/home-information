import logging
from typing import Dict

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.models import Entity

from hi.integrations.transient_models import IntegrationKey
from hi.integrations.sync_mixins import IntegrationSyncMixin

from .hass_converter import HassConverter
from .hass_models import HassDevice
from .hass_mixins import HassMixin
from .hass_metadata import HassMetaData

logger = logging.getLogger(__name__)


class HassSynchronizer( HassMixin, IntegrationSyncMixin ):

    SYNCHRONIZATION_LOCK_NAME = 'hass_integration_sync'

    def __init__(self):
        return
        
    def sync( self ) -> ProcessingResult:
        try:
            with ExclusionLockContext( name = self.SYNCHRONIZATION_LOCK_NAME ):
                logger.debug( 'HAss integration sync started.' )
                return self._sync_helper()
        except RuntimeError as e:
            logger.exception( e )
            return ProcessingResult(
                title = 'Home Assistant Import Result',
                error_list = [ str(e) ],
            )
        finally:
            logger.debug( 'HAss integration sync ended.' )
    
    def _sync_helper( self ) -> ProcessingResult:
        hass_manager = self.hass_manager()
        result = ProcessingResult( title = 'Home Assistant Import Result' )

        hass_client = hass_manager.hass_client
        if not hass_client:
            logger.debug( 'Home Assistant client not created. Home Assistant integration disabled?' )
            result.error_list.append( 'Sync problem. Home Assistant integration disabled?' )
            return result

        hass_entity_id_to_state = hass_manager.fetch_hass_states_from_api()
        result.message_list.append( f'Found {len(hass_entity_id_to_state)} current Home Assistant states.' )

        integration_key_to_entity = self._get_existing_hass_entities( result = result )
        result.message_list.append( f'Found {len(integration_key_to_entity)} existing Home Assistant entities.' )

        hass_device_id_to_device = HassConverter.hass_states_to_hass_devices(
            hass_entity_id_to_state = hass_entity_id_to_state,
        )
        result.message_list.append( f'Found {len(hass_device_id_to_device)} current Home Assistant devices.' )

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

    
