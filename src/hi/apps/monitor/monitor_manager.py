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

    START_DELAY_INTERVAL_SECS = 5

    def __init_singleton__( self ):
        self._monitor_map = dict()
        self._initialized = False
        self._data_lock = threading.Lock()
        self._monitor_event_loop = None
        return

    def _add_monitor(self, monitor: PeriodicMonitor) -> None:
        """Thread-safe setter for monitor_map."""
        with self._data_lock:
            self._monitor_map[monitor.id] = monitor

    def _get_monitor(self, monitor_id: str) -> PeriodicMonitor:
        """Thread-safe getter for a single monitor."""
        with self._data_lock:
            return self._monitor_map.get(monitor_id)

    def _get_all_monitors(self) -> List[PeriodicMonitor]:
        """Thread-safe getter for all monitors."""
        with self._data_lock:
            return list(self._monitor_map.values())

    async def initialize( self, event_loop ) -> None:
        # Check if already initialized (with lock)
        with self._data_lock:
            if self._initialized:
                logger.info('MonitorManager already initialize. Skipping.')
                return
            self._initialized = True
            self._monitor_event_loop = event_loop

        # Discovery and instantiation (no lock needed for discovery)
        logger.info('Discovering and starting app monitors...')
        periodic_monitor_class_list = self._discover_periodic_monitors()

        # Instantiate and add all monitors (with lock per add)
        for monitor_class in periodic_monitor_class_list:
            monitor = monitor_class()
            self._add_monitor(monitor)

        # Sort monitors by query interval (ascending) for priority ordering
        # This ensures critical monitors with shorter intervals start first
        sorted_monitors = sorted(self._get_all_monitors(), key=lambda m: m._query_interval_secs)

        # Start monitors with staggered delays (no lock needed)
        for monitor in sorted_monitors:
            if not monitor.is_running:
                if settings.DEBUG and settings.SUPPRESS_MONITORS:
                    logger.debug(f'Skipping app monitor: {monitor.id}. See SUPPRESS_MONITORS = True')
                    continue

                # Staggered startup: sleep before starting each monitor
                logger.debug(f'Delaying startup of {monitor.id} by {self.START_DELAY_INTERVAL_SECS}s (interval: {monitor._query_interval_secs}s)')
                await asyncio.sleep(self.START_DELAY_INTERVAL_SECS)

                logger.debug(f'Starting app monitor: {monitor.id}')
                asyncio.create_task(monitor.start(), name=f'App-{monitor.id}')
        return

    async def shutdown(self) -> None:
        logger.info('Stopping all registered app monitors...')
        with self._data_lock:
            for monitor in self._monitor_map.values():
                logger.debug( f'Stopping app monitor: {monitor.id}' )
                monitor.stop()
                continue
        return

    def get_health_status_by_monitor_id( self,
                                         monitor_id : str ) -> HealthStatusProvider:
        monitor = self._get_monitor(monitor_id)
        if monitor:
            return monitor
        raise KeyError( f'Unknown monitor id: "{monitor_id}".' )

    def get_health_status_providers(self) -> List[HealthStatusProvider]:
        """Get health status providers for all registered monitors.
            Each provider exposes get_provider_info() and health_status.
        """
        return self._get_all_monitors()

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
