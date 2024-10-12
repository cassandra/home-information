import logging
from typing import List

from hi.apps.common.singleton import Singleton

from hi.integrations.hass.hass_gateway import HassGateway
from hi.integrations.zoneminder.zm_gateway import ZoneMinderGateway

from .enums import IntegrationType
from .integration_gateway import IntegrationGateway
from .models import Integration

logger = logging.getLogger(__name__)


class IntegrationFactory( Singleton ):

    def __init_singleton__( self ):
        return

    def get_all_integrations( self ) -> List[ Integration ]:
        integration_list = list()
        for integration_type in IntegrationType:
            if integration_type == IntegrationType.NONE:
                continue
            integration = self.get_integration( integration_type = integration_type )
            integration_list.append( integration )
            continue
        return integration_list
    
    def get_integration( self, integration_type : IntegrationType ) -> Integration:
        try:
            return Integration.objects.get( integration_type_str = str(integration_type) )
        except Integration.DoesNotExist:
            return Integration(
                integration_type_str = str(integration_type),
                is_enabled = False,
            )
        
    def get_integration_gateway( self, integration_type : IntegrationType ) -> IntegrationGateway:
        if integration_type == IntegrationType.HASS:
            return HassGateway()
        elif integration_type == IntegrationType.ZONEMINDER:
            return ZoneMinderGateway()
        else:
            raise ValueError( f'The "{integration_type}" integration is not yet implemented.' )
