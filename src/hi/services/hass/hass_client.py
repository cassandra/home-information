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

    TRACE = True
    
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
        response = get( url, headers = self._headers )
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
            
        response = post( url, json = data, headers = self._headers )
        if response.status_code != 200:
            raise ValueError( f"Failed to set state: {response.status_code} {response.text}" )
        
        return response.json()

    
