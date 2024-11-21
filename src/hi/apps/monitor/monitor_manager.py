import asyncio
import logging

from hi.apps.common.singleton import Singleton

from .periodic_monitor import PeriodicMonitor

logger = logging.getLogger(__name__)


class MonitorManager( Singleton ):

    def __init_singleton__( self ):
        self._monitor_map = {}
        self._tasks = {}
        self._started = False
        self._loop = asyncio.get_event_loop()
        return

    def register( self, monitor : PeriodicMonitor ) -> None:
        if monitor.id in self._monitor_map:
            logger.debug(f"Monitor: {monitor.id} already registered")
            return

        logger.debug(f"Registering monitor: {monitor.id}")
        self._monitor_map[monitor.id] = monitor

        if self._started:
            logger.debug(f"Manager is running, starting monitor: {monitor.id}")
            self._tasks[monitor.id] = self._loop.create_task( monitor.start() )

        return
    
    def deregister( self, monitor : PeriodicMonitor ) -> None:
        if monitor.id not in self._monitor_map:
            logger.debug(f"Monitor: {monitor.id} not registered")
            return
        
        logger.debug(f"Deregistering monitor: {monitor.id}")
        if monitor.id in self._tasks:
            logger.debug(f"Stopping monitor: {monitor.id}")
            self._tasks[monitor.id].cancel()
            del self._tasks[monitor.id]
            
        monitor.stop()
        del self._monitor_map[monitor.id]
        return
    
    async def start_all(self) -> None:
        logger.info("Starting all registered monitors...")

        self._started = True
        for monitor_id, monitor in self._monitor_map.items():
            if monitor_id not in self._tasks:
                logger.debug(f"Starting monitor: {monitor_id}")
                self._tasks[monitor_id] = self._loop.create_task( monitor.start() )
            continue
        
        # Await all running tasks
        await asyncio.gather( *self._tasks.values(), return_exceptions = True )
        return

    def stop_all(self) -> None:
        if not self._started:
            return
            
        logger.info("Stopping all registered monitors...")
        self._started = False  # Mark manager as stopped
        for monitor_id, task in self._tasks.items():
            logger.debug(f"Stopping monitor: {monitor_id}")
            task.cancel()
            continue
        
        self._tasks.clear()

        for monitor in self._monitor_map.values():
            monitor.stop()
            continue
        return
