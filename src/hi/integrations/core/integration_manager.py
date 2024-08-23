import logging
from typing import List

from hi.apps.common.singleton import Singleton

from .enums import IntegrationType
from .models import Integration

logger = logging.getLogger(__name__)


class IntegrationManager( Singleton ):

    def __init_singleton__( self ):
        return

    def get_all_integrations( self ) -> List[ Integration ]:
        integration_list = list()
        for integration_type in IntegrationType:
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
