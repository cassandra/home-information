import asyncio
import logging

from django.apps import apps

from hi.apps.common.singleton import Singleton
from hi.apps.common.module_utils import import_module_safe

from .periodic_monitor import PeriodicMonitor

logger = logging.getLogger(__name__)


class MonitorManager( Singleton ):

    def __init_singleton__( self ):
        self._monitor_map = {}  # Known monitors
        self._event_loop = None  # Added dynamically and indicates if thread/event loop initialized
        return

    def register( self, monitor : PeriodicMonitor ) -> None:
        if monitor.id in self._monitor_map:
            logger.debug(f"Monitor: {monitor.id} already registered")
            return

        logger.debug(f"Registering monitor: {monitor.id}")
        self._monitor_map[monitor.id] = monitor

        if not self._event_loop:
            logger.warning("No running event loop. Deferring monitor start")
            return
        
        if self._event_loop.is_running():
            logger.debug(f"Scheduling monitor start: {monitor.id}")
            asyncio.run_coroutine_threadsafe( monitor.start(), self._event_loop )
        else:
            logger.error("Event loop is not running")

        return
    
    def deregister( self, monitor_id : str ) -> None:
        monitor = self._monitor_map.get( monitor_id )
        if not monitor:
            logger.debug(f"Monitor: {monitor.id} not registered")
            return

        logger.debug(f"Deregistering monitor: {monitor.id}")
        if monitor.is_running():
            monitor.stop()
        del self._monitor_map[monitor.id]
        return
    
    async def initialize(self) -> None:
        if self._event_loop:
            self.shutdown()
        
        self._event_loop = asyncio.get_event_loop()
        
        logger.info("Discovering app monitors...")
        periodic_monitor_class_list = self._discover_periodic_monitors()        
        for monitor_class in periodic_monitor_class_list:
            monitor = monitor_class()
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

    def _discover_periodic_monitors(self):

        periodic_monitor_class_list = list()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi' ):
                continue
            module_name = f'{app_config.name}.monitors'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
                    logger.debug( f'No monitor module for {app_config.name}' )
                    continue

                logger.debug( f'Found monitor module for {app_config.name}' )
                
                for attr_name in dir(app_module):
                    attr = getattr( app_module, attr_name )
                    if ( isinstance( attr, type )
                         and issubclass( attr, PeriodicMonitor )
                         and attr is not PeriodicMonitor ):
                        logger.debug(f'Found periodic monitor: {attr_name}')
                        periodic_monitor_class_list.append( attr )
                    continue                
                
            except Exception as e:
                logger.exception( f'Problem loading settings for {module_name}.', e )
            continue

        return periodic_monitor_class_list
       
