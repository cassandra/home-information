import json
from requests import get

from django.core.management.base import BaseCommand

from hi.apps.common.command_utils import CommandLoggerMixin


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
        print( json.dumps( data, indent=4, sort_keys=True ))

        print( f'Total states = {len(data)}' )
        return
