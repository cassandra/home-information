import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.monitor.state_monitor_mixin import EntityStateMonitorMixin

from .zm_manager import ZoneMinderManager

logger = logging.getLogger(__name__)


class ZoneMinderMonitor( PeriodicMonitor, EntityStateMonitorMixin ):

    def __init__( self ):
        super().__init__(
            id = 'zm-monitor',
            interval_secs = 10,
        )
        self._manager = ZoneMinderManager()
        return

    async def do_work(self):


        if self.TRACE:
            logger.debug( 'Fetched ZoneMinder States' )


        # TODO: zzz Update Redis with state values



        
        return
    
