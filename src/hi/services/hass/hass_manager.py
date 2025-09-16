import logging
from asgiref.sync import sync_to_async
from threading import Lock
from typing import Dict

from hi.apps.common.singleton import Singleton
from hi.apps.common.utils import str_to_bool

from hi.integrations.exceptions import IntegrationAttributeError, IntegrationError
from hi.integrations.transient_models import IntegrationKey
from hi.integrations.models import Integration, IntegrationAttribute

from .enums import HassAttributeType
from .hass_client import HassClient
from .hass_metadata import HassMetaData
from .hass_models import HassState

logger = logging.getLogger(__name__)


class HassManager( Singleton ):

    def __init_singleton__( self ):
        self._hass_attr_type_to_attribute = dict()
        self._hass_client = None
        
        self._change_listeners = list()
        self._was_initialized = False
        self._data_lock = Lock()
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        self.reload()
        self._was_initialized = True
        return
    
    def register_change_listener( self, callback ):
        logger.debug( f'Adding HAss setting change listener from {callback.__module__}' )
        self._change_listeners.append( callback )
        return
    
    def notify_settings_changed(self):
        self.reload()
        for callback in self._change_listeners:
            try:
                callback()
            except Exception:
                logger.exception( 'Problem calling setting change callback.' )
            continue
        return
    
    @property
    def hass_client(self):
        return self._hass_client
    
    def reload( self ):
        """ Called when integration models are changed (via signals below). """
        logger.debug( 'HAss manager loading started.' )
        with self._data_lock:
            self._hass_attr_type_to_attribute = self._load_attributes()
            self._hass_client = self.create_hass_client( self._hass_attr_type_to_attribute )
            self.clear_caches()
            
        logger.debug( 'HAss manager loading completed.' )
        return

    def clear_caches(self):
        return
    
    def _load_attributes(self) -> Dict[ HassAttributeType, IntegrationAttribute ]:
        try:
            hass_integration = Integration.objects.get( integration_id = HassMetaData.integration_id )
        except Integration.DoesNotExist:
            raise IntegrationError( 'Home Assistant integration is not implemented.' )
        
        if not hass_integration.is_enabled:
            raise IntegrationError( 'Home Assistant integration is not enabled.' )
        
        hass_attr_type_to_attribute = dict()
        integration_key_to_attribute = hass_integration.attributes_by_integration_key
        for hass_attr_type in HassAttributeType:
            integration_key = IntegrationKey(
                integration_id = hass_integration.integration_id,
                integration_name = str(hass_attr_type),
            )
            hass_attr = integration_key_to_attribute.get( integration_key )
            if not hass_attr:
                if hass_attr_type.is_required:
                    raise IntegrationAttributeError( f'Missing HAss attribute {hass_attr_type}' )
                else:
                    continue
            if hass_attr.is_required and not hass_attr.value.strip():
                raise IntegrationAttributeError( f'Missing HAss attribute value for {hass_attr_type}' )
            
            hass_attr_type_to_attribute[hass_attr_type] = hass_attr
            continue

        return hass_attr_type_to_attribute
    
    def create_hass_client(
            self,
            hass_attr_type_to_attribute : Dict[ HassAttributeType, IntegrationAttribute ] ) -> HassClient:
        # Verify integration and build API data payload
        api_options = {
            # 'disable_ssl_cert_check': True
        }
        attr_to_api_option_key = {
            HassAttributeType.API_BASE_URL: HassClient.API_BASE_URL,
            HassAttributeType.API_TOKEN: HassClient.API_TOKEN,
        }
        
        integration_key_to_attribute = { x.integration_key: x for x in hass_attr_type_to_attribute.values() }
        for hass_attr_type in attr_to_api_option_key.keys():
            integration_key = IntegrationKey(
                integration_id = HassMetaData.integration_id,
                integration_name = str(hass_attr_type),
            )
            hass_attr = integration_key_to_attribute.get( integration_key )
            if not hass_attr:
                raise IntegrationAttributeError( f'Missing HAss API attribute {hass_attr_type}' )
            if not hass_attr.value.strip():
                raise IntegrationAttributeError( f'Missing HAss API attribute value for {hass_attr_type}' )

            options_key = attr_to_api_option_key[hass_attr_type]
            api_options[options_key] = hass_attr.value
            continue
        
        logger.debug( f'Home Assistant client options: {api_options}' )
        return HassClient( api_options = api_options )

    @property
    def should_add_alarm_events( self ) -> bool:
        attribute = self._hass_attr_type_to_attribute.get( HassAttributeType.ADD_ALARM_EVENTS )
        if attribute:
            return str_to_bool( attribute.value )
        return False
        
    def fetch_hass_states_from_api( self, verbose : bool = True ) -> Dict[ str, HassState ]:
        if verbose:
            logger.debug( 'Getting current HAss states.' )
            
        hass_entity_id_to_state = dict()
        for hass_state in self.hass_client.states():
            hass_entity_id = hass_state.entity_id
            hass_entity_id_to_state[hass_entity_id] = hass_state
            continue

        return hass_entity_id_to_state
    
    async def fetch_hass_states_from_api_async( self, verbose : bool = True ) -> Dict[ str, HassState ]:
        """
        Async version of fetch_hass_states_from_api for use in async contexts (monitors).
        Uses sync_to_async to properly handle the synchronous API call.
        """
        return await sync_to_async(
            self.fetch_hass_states_from_api,
            thread_sensitive=True
        )(verbose=verbose)
