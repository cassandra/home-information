import logging
from typing import List

from hi.apps.common.singleton import Singleton

from .integration_gateway import IntegrationGateway
from .models import Integration
from .transient_models import IntegrationData

logger = logging.getLogger(__name__)


class IntegrationFactory( Singleton ):

    def __init_singleton__( self ):
        self._integration_gateway_map = dict()
        return

    def get_integration_data_list( self ) -> List[ IntegrationData ]:
        integration_data_list = list()
        for integration_gateway in self._integration_gateway_map.values():
            integration_metadata = integration_gateway.get_meta_data()
            integration = self.get_integration( integration_id = integration_metadata.integration_id )
            integration_data = IntegrationData(
                integration_metadata = integration_metadata,
                integration = integration,
            )
            integration_data_list.append( integration_data )
            continue
        return integration_data_list
    
    def get_integration( self, integration_id : str ) -> Integration:
        if integration_id not in self._integration_gateway_map:
            raise KeyError( f'Unknown integration id "{integration_id}".' )
        try:
            return Integration.objects.get( integration_id = integration_id )
        except Integration.DoesNotExist:
            return Integration(
                integration_id = integration_id,
                is_enabled = False,
            )
        
    def get_integration_gateway( self, integration_id : str ) -> IntegrationGateway:
        if integration_id in self._integration_gateway_map:
            return self._integration_gateway_map[integration_id]
        raise KeyError( f'Unknown integration id "{integration_id}".' )
        
    def register( self, integration_gateway  : IntegrationGateway ):
        integration_metadata = integration_gateway.get_meta_data()
        integration_id = integration_metadata.integration_id
        if integration_id in self._integration_gateway_map:
            logger.debug( f'Ignoring repeat integration registration: {integration_metadata.label}' )
            return
        logger.debug( f'Registering integration: {integration_metadata.label}' )
        self._integration_gateway_map[integration_id] = integration_gateway
        return
