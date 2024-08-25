import json
from requests import get
from typing import Dict, List

from .hass_converter import HassConverter
from .hass_models import HassState


class HassClient:

    # Docs: https://developers.home-assistant.io/docs/api/rest/
    
    API_BASE_URL = 'api_base_url'
    API_TOKEN = 'api_token'
    
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
        return [ HassConverter.create_hass_state(x) for x in data ]
    
    
