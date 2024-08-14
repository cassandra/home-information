import boto3

from lp_game.singleton import Singleton


class AwsClientManager( Singleton ):
    
    def __init_singleton__( self ):
        self._location_client = None
        return

    def get_location_client(self):
        if not self._location_client:
            self._location_client = boto3.client("location")
        return self._location_client

