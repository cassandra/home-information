from asgiref.sync import sync_to_async
import asyncio
import logging
from typing import Dict, List

from django.apps import apps

from hi.apps.common.singleton import Singleton
from hi.apps.common.module_utils import import_module_safe

from .integration_gateway import IntegrationGateway
from .models import Integration
from .integration_data import IntegrationData

logger = logging.getLogger(__name__)


class IntegrationManager( Singleton ):

    def __init_singleton__( self ):
        self._integration_data_map : Dict[ str, IntegrationData ] = dict()
        self._monitor_map = {}  # Known monitors
        self._event_loop = None  # Added dynamically and indicates if thread/event loop initialized
        return

    def get_integration_data_list( self, enabled_only = False ) -> List[ IntegrationData ]:
        if enabled_only:
            integration_data_list = [ x for x in self._integration_data_map.values() if x.is_enabled ]
        else:
            integration_data_list = list( self._integration_data_map.values() )

        integration_data_list.sort( key = lambda data : data.integration_metadata.label )
        return integration_data_list
    
    def get_default_integration_data( self ) -> IntegrationData:
        enabled_integration_data_list = [ x for x in self._integration_data_map.values()
                                          if x.is_enabled ]
        if not enabled_integration_data_list:
            return None
        enabled_integration_data_list.sort( key = lambda data : data.integration_metadata.label )
        return enabled_integration_data_list[0]

    def get_integration_data( self, integration_id : str ) -> IntegrationData :
        if integration_id in self._integration_data_map:
            return self._integration_data_map[integration_id]
        raise KeyError( f'Unknown integration id "{integration_id}".' )

    def get_integration_gateway( self, integration_id : str ) -> IntegrationGateway:
        if integration_id in self._integration_data_map:
            return self._integration_data_map[integration_id].integration_gateway
        raise KeyError( f'Unknown integration id "{integration_id}".' )

    async def initialize(self) -> None:
        await self._load_integration_data()
        await self._start_monitors()
        return
        
    async def _load_integration_data(self) -> None:
        
        logger.debug("Discovering defined integrations ...")
        defined_integration_gateway_map = self._discover_defined_integrations()

        logger.debug("Loading existing integrations ...")
        existing_integration_map = await sync_to_async( self._load_existing_integrations )()
        
        for integration_id, integration_gateway in defined_integration_gateway_map.items():
            integration_metadata = integration_gateway.get_metadata()
            integration_id = integration_metadata.integration_id
            if integration_id in existing_integration_map:
                integration = existing_integration_map[integration_id]
            else:
                integration = Integration.objects.create(
                    integration_id = integration_id,
                    is_enabled = False,
                )
            integration_data = IntegrationData(
                integration_gateway = integration_gateway,
                integration = integration,
            )
            self._integration_data_map[integration_id] = integration_data
            continue
        return

    async def _start_monitors(self) -> None:
        if self._event_loop:
            self.shutdown()
        
        self._event_loop = asyncio.get_event_loop()
        
        for integration_data in self._integration_data_map.values():
            if not integration_data.is_enabled:
                continue
            monitor = integration_data.integration_gateway.get_monitor()
            if not monitor:
                continue
            self._monitor_map[monitor.id] = monitor
            if not monitor.is_running:
                logger.debug(f"Starting monitor: {monitor.id}")
                asyncio.run_coroutine_threadsafe( monitor.start(), self._event_loop )
            continue
        return

    def shutdown(self) -> None:
        if not self._event_loop:
            logger.info("Cannot stop all monitors. No event loop.")
            return
        
        logger.info("Stopping all registered monitors...")

        for monitor in self._monitor_map.values():
            monitor.stop()
            continue

        if self._event_loop.is_running():
            self._event_loop.stop()
        
        return

    def _discover_defined_integrations(self) -> Dict[ str, IntegrationGateway ]:

        integration_id_to_gateway = dict()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi.integrations' ):
                continue
            module_name = f'{app_config.name}.integration'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
                    logger.debug( f'No integration module for {app_config.name}' )
                    continue

                logger.debug( f'Found integration module for {app_config.name}' )
                
                for attr_name in dir(app_module):
                    attr = getattr( app_module, attr_name )
                    if ( isinstance( attr, type )
                         and issubclass( attr, IntegrationGateway )
                         and attr is not IntegrationGateway ):
                        logger.debug(f'Found integration gateway: {attr_name}')
                        integration_gateway = attr()
                        integration_metadata = integration_gateway.get_metadata()
                        integration_id = integration_metadata.integration_id
                        integration_id_to_gateway[integration_id] = integration_gateway
                    continue                
                
            except Exception as e:
                logger.exception( f'Problem getting integration gateway for {module_name}.', e )
            continue

        return integration_id_to_gateway

    def _load_existing_integrations(self):
        integration_queryset = Integration.objects.all()
        return { x.integration_id: x for x in integration_queryset }
    
