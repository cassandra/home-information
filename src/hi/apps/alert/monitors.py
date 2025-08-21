import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .alert_mixins import AlertMixin

logger = logging.getLogger(__name__)


class AlertMonitor( PeriodicMonitor, AlertMixin ):

    ALERT_POLLING_INTERVAL_SECS = 3

    TRACE = False  # for debugging
    
    def __init__( self ):
        super().__init__(
            id = 'alert-monitor',
            interval_secs = self.ALERT_POLLING_INTERVAL_SECS,
        )
        return

    async def do_work(self):
        if self.TRACE:
            logger.debug( 'Checking for alert maintenance work.' )
        alert_manager = await self.alert_manager_async()
        if not alert_manager:
            return
        
        await alert_manager.do_periodic_maintenance()
        return
