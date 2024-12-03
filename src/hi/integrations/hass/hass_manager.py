import logging
from typing import Dict

from hi.apps.common.singleton import Singleton

from hi.integrations.core.exceptions import IntegrationAttributeError
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.models import Integration

from .enums import HassAttributeType
from .hass_client import HassClient
from .hass_metadata import HassMetaData
from .hass_models import HassState

logger = logging.getLogger(__name__)


class HassManager( Singleton ):

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

    def fetch_hass_states_from_api( self, verbose : bool = True ) -> Dict[ str, HassState ]:
        if verbose:
            logger.debug( 'Getting current HAss states.' )
            
        hass_entity_id_to_state = dict()
        for hass_state in self.hass_client.states():
            hass_entity_id = hass_state.entity_id
            hass_entity_id_to_state[hass_entity_id] = hass_state
            continue

        return hass_entity_id_to_state
