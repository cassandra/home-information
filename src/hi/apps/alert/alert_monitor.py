import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .alert_manager import AlertManager

logger = logging.getLogger(__name__)


class AlertMonitor( PeriodicMonitor ):

    ALERT_POLLING_INTERVAL_SECS = 10

    def __init__( self ):
        super().__init__(
            id = 'alert-monitor',
            interval_secs = self.ALERT_POLLING_INTERVAL_SECS,
        )
        self._alert_manager = AlertManager()
        return

    async def do_work(self):
        logger.debug( 'Checking for alert maintenance work.' )
        self._alert_manager.do_periodic_maintenance()
        return
