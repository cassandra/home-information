import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.provider_info import ProviderInfo

from .notify_mixins import NotificationMixin

logger = logging.getLogger(__name__)


class NotificationMonitor( PeriodicMonitor, NotificationMixin ):

    NOTIFICATION_POLLING_INTERVAL_SECS = 10

    def __init__( self ):
        super().__init__(
            id = 'notification-monitor',
            interval_secs = self.NOTIFICATION_POLLING_INTERVAL_SECS,
        )
        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        """ Subclasses should override with something more meaningful. """
        return ProviderInfo(
            provider_id = 'hi.apps.notify',
            provider_name = 'Notifications Monitor',
            description = 'Notification processing and delivery management',
            expected_heartbeat_interval_secs = cls.NOTIFICATION_POLLING_INTERVAL_SECS,
        )
        
    async def do_work(self):
        logger.debug( 'Checking for notification maintenance work.' )
        notification_manager = await self.notification_manager_async()
        if not notification_manager:
            return
        await notification_manager.do_periodic_maintenance()
        return
