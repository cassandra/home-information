import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.provider_info import ProviderInfo

from .alert_mixins import AlertMixin

logger = logging.getLogger(__name__)


class AlertMonitor( PeriodicMonitor, AlertMixin ):

    MONITOR_ID = 'hi.apps.alert.monitor'
    ALERT_POLLING_INTERVAL_SECS = 3

    TRACE = False  # for debugging
    
    def __init__( self ):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.ALERT_POLLING_INTERVAL_SECS,
        )
        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'Alert Monitor',
            description = 'Alert processing and notification management',
            expected_heartbeat_interval_secs = cls.ALERT_POLLING_INTERVAL_SECS,
        )

    async def do_work(self):
        if self.TRACE:
            logger.debug( 'Checking for alert maintenance work.' )
        alert_manager = await self.alert_manager_async()
        if not alert_manager:
            return
        
        await alert_manager.do_periodic_maintenance()
        return
