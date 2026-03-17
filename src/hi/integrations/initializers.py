import logging

from django.apps import apps
from django.db import transaction

from hi.apps.common.module_utils import import_module_safe

from .integration_gateway import IntegrationGateway
from .integration_manager import IntegrationManager
from .models import Integration

logger = logging.getLogger(__name__)


class IntegrationInitializer:
    """Ensure required Integration DB records exist after migrations are applied."""

    def run( self, sender = None, **kwargs ):
        logger.debug( 'Populating initial DB records for integrations.' )
        defined_integration_gateway_map = self._discover_defined_integrations()
        self._create_integrations( defined_integration_gateway_map = defined_integration_gateway_map )
        return

    def _discover_defined_integrations( self ):
        integration_id_to_gateway = dict()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi.services' ):
                continue

            module_name = f'{app_config.name}.integration'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
                    continue

                for attr_name in dir(app_module):
                    attr = getattr( app_module, attr_name )
                    if ( isinstance( attr, type )
                         and issubclass( attr, IntegrationGateway )
                         and attr is not IntegrationGateway ):
                        integration_gateway = attr()
                        integration_metadata = integration_gateway.get_metadata()
                        integration_id = integration_metadata.integration_id
                        integration_id_to_gateway[integration_id] = integration_gateway
                    continue

            except Exception as e:
                logger.exception( f'Problem getting integration gateway for {module_name}.', e )
            continue

        return integration_id_to_gateway

    def _create_integrations( self, defined_integration_gateway_map ):
        existing_integration_map = { x.integration_id: x for x in Integration.objects.all() }
        integration_manager = IntegrationManager()

        with transaction.atomic():
            for integration_id, integration_gateway in defined_integration_gateway_map.items():
                integration_metadata = integration_gateway.get_metadata()
                integration = existing_integration_map.get( integration_id )
                if not integration:
                    integration = Integration.objects.create(
                        integration_id = integration_id,
                        is_enabled = False,
                    )

                integration_manager._ensure_all_attributes_exist(
                    integration_metadata = integration_metadata,
                    integration = integration,
                )
                continue

        return
