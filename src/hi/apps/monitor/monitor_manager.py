import asyncio
import logging

from hi.apps.common.singleton import Singleton

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
            logger.error("No running event loop. Deferring monitor start")
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
        logger.info("Starting all registered monitors...")

        # In case any registrations happened before initialize is called.
        for monitor_id, monitor in self._monitor_map.items():
            if not monitor.is_running:
                logger.debug(f"Starting monitor: {monitor_id}")
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
