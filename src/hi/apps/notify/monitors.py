import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .notification_manager import NotificationManager
from .notify_mixins import NotificationMixin

logger = logging.getLogger(__name__)


class NotificationMonitor( PeriodicMonitor, NotificationMixin ):

    NOTIFICATION_POLLING_INTERVAL_SECS = 10

    def __init__( self ):
        super().__init__(
            id = 'notification-monitor',
            interval_secs = self.NOTIFICATION_POLLING_INTERVAL_SECS,
        )
        self._notification_manager = NotificationManager()
        return

    async def do_work(self):
        logger.debug( 'Checking for notification maintenance work.' )
        notification_manager = await self.notification_manager_async()
        await notification_manager.do_periodic_maintenance()
        return
