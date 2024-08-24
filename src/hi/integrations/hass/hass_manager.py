import logging
from typing import Dict

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.common.singleton import Singleton
from hi.apps.entity.enums import (
    AttributeName,
    EntityType,
    AttributeValueType,
    AttributeType,
)
from hi.apps.entity.models import Entity, Attribute

from hi.apps.entity_helpers import EntityHelpers

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.exceptions import IntegrationPropertyError
from hi.integrations.core.models import Integration

from .enums import (
    HassPropertyName,
    HassAttributeName,
)
from .hass_client import HassClient
from .hass_state import HassState

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
        property_dict = hass_integration.property_dict
        for hass_prop_name in HassPropertyName:
            hass_prop = property_dict.get( hass_prop_name.name )
            if not hass_prop:
                raise IntegrationPropertyError( f'Missing HAss property {hass_prop_name.name}' ) 
            if hass_prop.is_required and not hass_prop.value.strip():
                raise IntegrationPropertyError( f'Missing HAss property value for {hass_prop_name.name}' ) 

            continue
        
        api_options = {
            HassClient.API_BASE_URL: property_dict.get( HassPropertyName.API_BASE_URL.name ).value,
            HassClient.API_TOKEN: property_dict.get( HassPropertyName.API_TOKEN.name ).value,
        }
        return HassClient( api_options = api_options )
        
    def sync( self ) -> ProcessingResult:
        try:
            with ExclusionLockContext( name = self.SYNCHRONIZATION_LOCK_NAME ):
                logger.debug( 'HAss integration sync started.' )
                return self._sync_helper()
        except RuntimeError as e:
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
                    
        hass_id_to_entity = self._get_hass_entities( result = result )
        result.message_list.append( f'Found {len(hass_id_to_entity)} existing HAss entities.' )

        hass_id_to_state = self._get_hass_states( result = result )
        result.message_list.append( f'Found {len(hass_id_to_state)} current HAss states.' )
        
        for hass_id, hass_state in hass_id_to_state.items():
            entity = hass_id_to_entity.get( hass_id )
            if entity:
                self._update_entity( entity = entity,
                                     hass_state = hass_state,
                                     result = result )
            else:
                self._create_entity( hass_state = hass_state,
                                     result = result )
            continue
        
        for hass_id, entity in hass_id_to_entity.items():
            if hass_id not in hass_id_to_state:
                self._remove_entity( entity = entity,
                                     result = result )
            continue
        
        return result

    def _get_hass_entities( self, result : ProcessingResult ) -> Dict[ int, Entity ]:
        logger.debug( 'Getting existing HAss entities.' )
        hass_id_to_entity = dict()

        attribute_queryset = Attribute.objects.select_related( 'entity' ). filter(
            name = AttributeName.INTEGRATION_SOURCE,
            value = IntegrationType.HASS.name,
        )
        for attribute in attribute_queryset:
            hass_entity = attribute.entity
            attribute_map = hass_entity.get_attribute_map()
            attribute = attribute_map.get( str(HassAttributeName.HASS_ENTITY_ID) )
            if attribute and attribute.value:
                hass_id = attribute.value
            else:
                result.error_list.append( f'HAss entity found without valid HAss Id: {hass_entity}' )
                hass_id = 1000000 + hass_entity.id  # We need a (unique) placeholder (will remove this later)
            hass_id_to_entity[hass_id] = hass_entity
            continue

        return hass_id_to_entity

    def _get_hass_states( self, result : ProcessingResult ) -> Dict[ int, HassState ]:
        
        logger.debug( 'Getting current HAss states.' )
        hass_id_to_state = dict()
        for hass_state in self.hass_client.states():
            hass_id = hass_state.entity_id
            
            hass_id_to_state[hass_id] = hass_state
            continue

        return hass_id_to_state
    
    def _create_entity( self,
                        hass_state  : HassState,
                        result      : ProcessingResult ):

        result.error_list.append( f'Create not yet implemented: {hass_state} [insteon={hass_state.is_insteon}]' )
        return
    
    def _update_entity( self,
                        entity      : Entity,
                        hass_state  : HassState,
                        result      : ProcessingResult ):

        result.error_list.append( f'Update not yet implemented: {entity}' )
        
        return
    
    def _remove_entity( self,
                        entity   : Entity,
                        result   : ProcessingResult ):

        result.error_list.append( f'Remove not yet implemented: {entity}' )
        return
    
