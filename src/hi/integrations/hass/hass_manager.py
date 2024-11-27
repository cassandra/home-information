import logging
from typing import Dict

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity

from hi.integrations.core.exceptions import IntegrationAttributeError
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.models import Integration

from .enums import HassAttributeType
from .hass_client import HassClient
from .hass_converter import HassConverter
from .hass_metadata import HassMetaData
from .hass_models import HassState, HassDevice

logger = logging.getLogger(__name__)


class HassManager( Singleton ):

    SYNCHRONIZATION_LOCK_NAME = 'hass_integration_sync'

    def __init_singleton__( self ):
        self._is_loading = False
        self._hass_client = None
        self.reload()
        return

    @property
    def hass_client(self):
        return self._hass_client
    
    def reload( self ):
        """ Should be called when integration settings are changed. """
        if self._is_loading:
            logger.warning( 'HAss is already loading.' )
            return
        try:
            self._is_loading = True
            self._hass_client = self.create_hass_client()
        
        finally:
            self._is_loading = False
            logger.debug( 'HAss loading completed.' )
        return

    def create_hass_client(self):
        try:
            hass_integration = Integration.objects.get( integration_id = HassMetaData.integration_id )
        except Integration.DoesNotExist:
            logger.debug( 'HAss integration is not implemented.' )

        if not hass_integration.is_enabled:
            logger.debug( 'HAss integration is not enabled.' )
            return None

        # Verify integration and build API data payload
        api_options = {
            # 'disable_ssl_cert_check': True
        }
        attr_to_api_option_key = {
            HassAttributeType.API_BASE_URL: HassClient.API_BASE_URL,
            HassAttributeType.API_TOKEN: HassClient.API_TOKEN,
        }
        
        attribute_dict = hass_integration.attributes_by_integration_key
        for hass_attr_type in HassAttributeType:
            integration_key = IntegrationKey(
                integration_id = hass_integration.integration_id,
                integration_name = str(hass_attr_type),
            )
            hass_attr = attribute_dict.get( integration_key )
            if not hass_attr:
                raise IntegrationAttributeError( f'Missing HAss attribute {hass_attr_type}' ) 
            if hass_attr.is_required and not hass_attr.value.strip():
                raise IntegrationAttributeError( f'Missing HAss attribute value for {hass_attr_type}' )

            if hass_attr_type in attr_to_api_option_key:
                options_key = attr_to_api_option_key[hass_attr_type]
                api_options[options_key] = hass_attr.value
            
            continue
        
        logger.debug( f'Home Assistant client options: {api_options}' )
        return HassClient( api_options = api_options )
        
    def sync( self ) -> ProcessingResult:
        try:
            with ExclusionLockContext( name = self.SYNCHRONIZATION_LOCK_NAME ):
                logger.debug( 'HAss integration sync started.' )
                return self._sync_helper()
        except RuntimeError as e:
            logger.exception( e )
            return ProcessingResult(
                title = 'HAss Sync Result',
                error_list = [ str(e) ],
            )
        finally:
            logger.debug( 'HAss integration sync ended.' )
    
    def _sync_helper( self ) -> ProcessingResult:
        result = ProcessingResult( title = 'HAss Sync Result' )

        hass_client = self.hass_client
        if not hass_client:
            logger.debug( 'HAss client not created. HAss integration disabled?' )
            result.error_list.append( 'Sync problem. HAss integration disabled?' )
            return result
                    
        hass_entity_id_to_state = self.fetch_hass_states_from_api()
        result.message_list.append( f'Found {len(hass_entity_id_to_state)} current HAss states.' )

        integration_key_to_entity = self._get_existing_hass_entities( result = result )
        result.message_list.append( f'Found {len(integration_key_to_entity)} existing HAss entities.' )

        hass_device_id_to_device = HassConverter.hass_states_to_hass_devices(
            hass_entity_id_to_state = hass_entity_id_to_state,
        )
        result.message_list.append( f'Found {len(hass_device_id_to_device)} current HAss devices.' )

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

    def fetch_hass_states_from_api( self, verbose : bool = True ) -> Dict[ str, HassState ]:
        if verbose:
            logger.debug( 'Getting current HAss states.' )
            
        hass_entity_id_to_state = dict()
        for hass_state in self.hass_client.states():
            hass_entity_id = hass_state.entity_id
            hass_entity_id_to_state[hass_entity_id] = hass_state
            continue

        return hass_entity_id_to_state
    
    def _get_existing_hass_entities( self, result : ProcessingResult ) -> Dict[ IntegrationKey, Entity ]:
        logger.debug( 'Getting existing HAss entities.' )
        integration_key_to_entity = dict()

        entity_queryset = Entity.objects.filter( integration_id = HassMetaData.integration_id )
        for entity in entity_queryset:
            integration_key = entity.integration_key
            if not integration_key:
                result.error_list.append( f'Entity found without valid HAss Id: {entity}' )
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
        entity = HassConverter.create_models_for_hass_device( hass_device = hass_device )
        result.message_list.append( f'Created HAss entity: {entity}' )
        return
    
    def _update_entity( self,
                        entity       : Entity,
                        hass_device  : HassDevice,
                        result       : ProcessingResult ):

        result.message_list.append( f'No updates needed for HAss entity: {entity}' )        
        return
    
    def _remove_entity( self,
                        entity   : Entity,
                        result   : ProcessingResult ):
        entity.delete()  # Deletion cascades to attributes, positions, sensors, controllers, etc.
        result.message_list.append( f'Removed stale HAss entity: {entity}' )
        return
    
