import logging

from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.system.provider_info import ProviderInfo

from .notify_mixins import NotificationMixin

logger = logging.getLogger(__name__)


class NotificationMonitor( PeriodicMonitor, NotificationMixin ):

    MONITOR_ID = 'hi.apps.notify.monitor'
    NOTIFICATION_POLLING_INTERVAL_SECS = 10

    def __init__( self ):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.NOTIFICATION_POLLING_INTERVAL_SECS,
        )
        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'Notifications Monitor',
            description = 'Notification processing and delivery',
            expected_heartbeat_interval_secs = cls.NOTIFICATION_POLLING_INTERVAL_SECS,
        )

    async def do_work(self):
        logger.debug( 'Checking for notification maintenance work.' )
        notification_manager = await self.notification_manager_async()
        if not notification_manager:
            self.record_error( 'Notification manager not available' )
            return

        try:
            result = await notification_manager.do_periodic_maintenance()

            # Update health status based on results
            summary_message = result.get_summary_message()

            if result.error_messages:
                if result.notifications_failed > 0 and result.notifications_sent == 0:
                    # All notifications failed - this is an error
                    self.record_error( summary_message )
                else:
                    # Some succeeded, some failed - this is a warning
                    self.record_warning( summary_message )
            else:
                self.record_healthy( summary_message )

            logger.debug( f'Notification maintenance completed: {summary_message}' )

        except Exception as e:
            error_msg = f"Notification maintenance failed: {str(e)[:50]}"
            logger.exception( error_msg )
            self.record_error( error_msg )

        return
