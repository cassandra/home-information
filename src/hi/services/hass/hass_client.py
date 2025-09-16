import json
import logging
from requests import get, post
from typing import Dict, List

from .hass_converter import HassConverter
from .hass_models import HassState

logger = logging.getLogger(__name__)


class HassClient:

    # Docs: https://developers.home-assistant.io/docs/api/rest/
    
    API_BASE_URL = 'api_base_url'
    API_TOKEN = 'api_token'

    TRACE = False  # For debugging

    def __init__( self, api_options : Dict[ str, str ] ):

        self._api_base_url = api_options.get( self.API_BASE_URL )
        assert self._api_base_url is not None
        if self._api_base_url[-1] == '/':
            self._api_base_url = self._api_base_url[0:-1]
            
        token = api_options.get( self.API_TOKEN )
        assert token is not None
        
        self._headers = {
            'Authorization': f'Bearer {token}',
            'content-type':'application/json',
        }
        return

    def states(self) -> List[ HassState ]:

        url = f'{self._api_base_url}/api/states'
        response = get( url, headers = self._headers, timeout = 25.0 )
        data = json.loads(response.text)
        if self.TRACE:
            logger.debug( f'HAss Response = {response.text}' )
        return [ HassConverter.create_hass_state(x) for x in data ]

    def set_state( self, entity_id: str, state: str, attributes: dict = None ) -> dict:

        url = f'{self._api_base_url}/api/states/{entity_id}'
        data = {
            'state': state,
        }
        if attributes:
            data["attributes"] = attributes
        response = post( url, json = data, headers = self._headers, timeout = 25.0 )
        if response.status_code != 200:
            raise ValueError( f"Failed to set state: {response.status_code} {response.text}" )
        
        return response.json()

    def call_service( self, domain: str, service: str, hass_state_id: str, service_data: dict = None ):
        """
        Call a Home Assistant service for a specific HassState.
        
        Args:
            domain: The domain (e.g., 'light', 'switch')
            service: The service name (e.g., 'turn_on', 'turn_off')
            hass_state_id: The HassState identifier (e.g., 'light.switch_name')
            service_data: Additional service data (optional)
        
        Returns:
            Response object
        """
        url = f'{self._api_base_url}/api/services/{domain}/{service}'
        data = {
            'entity_id': hass_state_id,
        }
        if service_data:
            data.update(service_data)
            
        response = post( url, json = data, headers = self._headers, timeout = 25.0 )
        if response.status_code not in [200, 201]:
            raise ValueError( f"Failed to call service: {response.status_code} {response.text}" )
            
        logger.debug( f'HAss call_service: {domain}.{service} for {hass_state_id}, response={response.status_code}' )
        return response

    
