import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .alert_mixins import AlertMixin

logger = logging.getLogger(__name__)


class AlertMonitor( PeriodicMonitor, AlertMixin ):

    ALERT_POLLING_INTERVAL_SECS = 1

    def __init__( self ):


        
        print( 'ALERT-INIT' )


        
        
        super().__init__(
            id = 'alert-monitor',
            interval_secs = self.ALERT_POLLING_INTERVAL_SECS,
        )
        return

    async def do_work(self):


        print( 'START-ALERT-WORK' )

        
        logger.debug( 'Checking for alert maintenance work.' )
        alert_manager = await self.alert_manager_async()

        print( 'START-ALERT-MAINTENANCE' )
        if not alert_manager:
            return
        


        
        await alert_manager.do_periodic_maintenance()

        print( 'END-ALERT-WORK' )
        
        return
