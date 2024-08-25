import json
from requests import get

from django.core.management.base import BaseCommand

from hi.apps.common.command_utils import CommandLoggerMixin

from hi.integrations.hass.hass_converter import HassConverter


class Command( BaseCommand, CommandLoggerMixin ):
    """ Used for ad-hoc testing and explorations during development of the Zoneminder integration. """
    
    help = 'Check HAss API functionality.'

    def handle(self, *args, **options):
        self.info( 'HAss API Test' )

        url = 'http://bordeaux:8123/api/states'
        token = '--REDACTED--'
        
        headers = {
            'Authorization': f'Bearer {token}',
            'content-type':'application/json',
        }
        
        response = get(url, headers=headers)
        data = json.loads(response.text)

        print( '============================================================\nSTATES' )
        print( json.dumps( data, indent=4, sort_keys=True ))
        print( f'Total states = {len(data)}' )

        hass_entity_id_to_state = dict()
        for api_dict in data:
            hass_state = HassConverter.create_hass_state( api_dict = api_dict )
            hass_entity_id_to_state[hass_state.entity_id] = hass_state
            continue

        hass_device_id_to_device = HassConverter.hass_states_to_hass_devices(
            hass_entity_id_to_state = hass_entity_id_to_state,
        )

        print( '============================================================\nDEVICES' )
        print( json.dumps( [ x.to_dict() for x in hass_device_id_to_device.values() ],
                           indent=4, sort_keys=True ))
        print( f'Total devices = {len(hass_device_id_to_device)}' )
        
        return
