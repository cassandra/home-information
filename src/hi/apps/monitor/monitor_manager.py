import asyncio
import logging
import threading
from typing import List, Type

from hi.apps.system.health_status_provider import HealthStatusProvider

from django.apps import apps
from django.conf import settings

from hi.apps.common.singleton import Singleton
from hi.apps.common.module_utils import import_module_safe

from .periodic_monitor import PeriodicMonitor

logger = logging.getLogger(__name__)


class AppMonitorManager( Singleton ):

    def __init_singleton__( self ):
        self._monitor_map = dict()
        self._initialized = False
        self._data_lock = threading.Lock()
        self._monitor_event_loop = None
        return
    
    async def initialize( self, event_loop ) -> None:
        with self._data_lock:
            if self._initialized:
                logger.info('MonitorManager already initialize. Skipping.')
                return
            self._initialized = True

            self._monitor_event_loop = event_loop
            
            logger.info('Discovering and starting app monitors...')
            periodic_monitor_class_list = self._discover_periodic_monitors()        
            for monitor_class in periodic_monitor_class_list:
                monitor = monitor_class()

                self._monitor_map[monitor.id] = monitor
                if not monitor.is_running:
                    if settings.DEBUG and settings.SUPPRESS_MONITORS:
                        logger.debug(f'Skipping app monitor: {monitor.id}. See SUPPRESS_MONITORS = True')
                        continue

                    logger.debug( f'Starting app monitor: {monitor.id}' )
                    asyncio.create_task( monitor.start() )

                continue
        return

    async def shutdown(self) -> None:
        logger.info('Stopping all registered app monitors...')
        for monitor in self._monitor_map.values():
            logger.debug( f'Stopping app monitor: {monitor.id}' )
            monitor.stop()
            continue
        return

    def get_health_status_providers(self) -> List[HealthStatusProvider]:
        """Get health status providers for all registered monitors.

        Returns:
            List of HealthStatusProvider instances.
            Each provider exposes get_provider_info() and health_status.
        """
        with self._data_lock:
            # Return monitors as HealthStatusProvider instances
            # PeriodicMonitor inherits from HealthStatusProvider
            return list(self._monitor_map.values())

    def _discover_periodic_monitors(self) -> List[ Type[ PeriodicMonitor ]]:
        periodic_monitor_class_list = list()
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith( 'hi.apps' ):
                continue
            module_name = f'{app_config.name}.monitors'
            try:
                app_module = import_module_safe( module_name = module_name )
                if not app_module:
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
                logger.exception( f'Problem loading monitor for {module_name}.', e )
            continue

        return periodic_monitor_class_list
