import logging

from hi.apps.common.singleton import Singleton

from .enums import IntegrationType
from .models import Integration

logger = logging.getLogger(__name__)


class IntegrationManager( Singleton ):

    def __init_singleton__( self ):
        return

    def get_integration( self, integration_type : IntegrationType ) -> Integration:
        try:
            return Integration.objects.get( integration_type_str = str(integration_type) )
        except Integration.DoesNotExist:
            return Integration(
                integration_type_str = str(integration_type),
                is_enabled = False,
            )
