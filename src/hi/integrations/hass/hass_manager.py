import logging
from typing import Dict

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.exceptions import IntegrationAttributeError
from hi.integrations.core.models import Integration

from .enums import HassAttributeName
from .hass_client import HassClient
from .hass_converter import HassConverter
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
            hass_integration = Integration.objects.get( integration_type_str = str(IntegrationType.HASS) )
        except Integration.DoesNotExist:
            logger.debug( 'HAss integration is not implemented.' )

        if not hass_integration.is_enabled:
            logger.debug( 'HAss integration is not enabled.' )
            return None

        # Verify integration
        attribute_dict = hass_integration.attribute_dict
        for hass_attr_name in HassAttributeName:
            hass_prop = attribute_dict.get( hass_attr_name.name )
            if not hass_prop:
                raise IntegrationAttributeError( f'Missing HAss attribute {hass_attr_name.name}' ) 
            if hass_prop.is_required and not hass_prop.value.strip():
                raise IntegrationAttributeError( f'Missing HAss attribute value for {hass_attr_name.name}' ) 

            continue
        
        api_options = {
            HassClient.API_BASE_URL: attribute_dict.get( HassAttributeName.API_BASE_URL.name ).value,
            HassClient.API_TOKEN: attribute_dict.get( HassAttributeName.API_TOKEN.name ).value,
        }
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
                    
        hass_device_id_to_entity = self._get_existing_hass_entities( result = result )
        result.message_list.append( f'Found {len(hass_device_id_to_entity)} existing HAss entities.' )

        hass_entity_id_to_state = self._get_hass_states_from_api( result = result )
        result.message_list.append( f'Found {len(hass_entity_id_to_state)} current HAss states.' )

        hass_device_id_to_device = HassConverter.hass_states_to_hass_devices(
            hass_entity_id_to_state = hass_entity_id_to_state,
        )
        result.message_list.append( f'Found {len(hass_device_id_to_device)} current HAss devices.' )
        
        for hass_device_id, hass_device in hass_device_id_to_device.items():
            entity = hass_device_id_to_entity.get( hass_device_id )
            if entity:
                self._update_entity( entity = entity,
                                     hass_device = hass_device,
                                     result = result )
            else:
                self._create_entity( hass_device = hass_device,
                                     result = result )
            continue
        
        for hass_device_id, entity in hass_device_id_to_entity.items():
            if hass_device_id not in hass_device_id_to_device:
                self._remove_entity( entity = entity,
                                     result = result )
            continue
        
        return result

    def _get_existing_hass_entities( self, result : ProcessingResult ) -> Dict[ str, Entity ]:
        logger.debug( 'Getting existing HAss entities.' )
        hass_device_id_to_entity = dict()

        entity_queryset = Entity.objects.filter( integration_type_str = str(IntegrationType.HASS) )
        for entity in entity_queryset:
            integration_id = entity.integration_id
            hass_device_id = integration_id.key
            if not hass_device_id:
                result.error_list.append( f'Entity found without valid HAss Id: {entity}' )
                hass_device_id = 1000000 + entity.id  # We need a (unique) placeholder for removals
            hass_device_id_to_entity[hass_device_id] = entity
            continue

        return hass_device_id_to_entity

    def _get_hass_states_from_api( self, result : ProcessingResult ) -> Dict[ int, HassState ]:
        
        logger.debug( 'Getting current HAss states.' )
        hass_entity_id_to_state = dict()
        for hass_state in self.hass_client.states():
            hass_entity_id = hass_state.entity_id
            hass_entity_id_to_state[hass_entity_id] = hass_state
            continue

        return hass_entity_id_to_state
    
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
    
