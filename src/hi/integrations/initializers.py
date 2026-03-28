import logging

from django.db import transaction

from .integration_manager import IntegrationManager
from .models import Integration

logger = logging.getLogger(__name__)


class IntegrationInitializer:
    """Ensure required Integration DB records exist after migrations are applied."""

    def run( self, sender = None, **kwargs ):
        logger.debug( 'Populating initial DB records for integrations.' )
        integration_manager = IntegrationManager()
        defined_gateway_map = integration_manager.discover_defined_integrations()
        self._create_integrations(
            integration_manager = integration_manager,
            defined_gateway_map = defined_gateway_map,
        )
        return

    def _create_integrations( self,
                              integration_manager  : IntegrationManager,
                              defined_gateway_map  : dict ):
        existing_integration_map = { x.integration_id: x for x in Integration.objects.all() }

        with transaction.atomic():
            for integration_id, integration_gateway in defined_gateway_map.items():
                integration = existing_integration_map.get( integration_id )
                if not integration:
                    integration = Integration.objects.create(
                        integration_id = integration_id,
                        is_enabled = False,
                    )

                integration_metadata = integration_gateway.get_metadata()
                integration_manager.ensure_all_attributes_exist(
                    integration_metadata = integration_metadata,
                    integration = integration,
                )
                continue

        return
