import logging
from typing import List

from hi.apps.common.email_utils import parse_emails_from_text
from hi.apps.common.singleton import Singleton
from hi.apps.common.utils import str_to_bool
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.notify.notification_queue import NotificationQueue

from .email_sender import EmailData, EmailSender
from .transient_models import Notification, NotificationItem
from .settings import NotifySetting
from .transient_models import NotificationMaintenanceResult

logger = logging.getLogger(__name__)


class NotificationManager( Singleton, SettingsMixin ):

    def __init_singleton__(self):
        self._notification_queue = NotificationQueue()
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        # Any future heavyweight initializations go here (e.g., any DB operations).
        self._was_initialized = True
        return

    def add_notification_item( self, notification_item : NotificationItem ):
        self._notification_queue.add_item( notification_item = notification_item )
        return

    async def do_periodic_maintenance(self) -> NotificationMaintenanceResult:
        """Process pending notifications and return execution results."""
        result = NotificationMaintenanceResult()

        try:
            settings_manager = await self.settings_manager_async()
            if not settings_manager:
                result.error_messages.append("Settings manager not available")
                return result

            notifications_enabled_str = settings_manager.get_setting_value(
                NotifySetting.NOTIFICATIONS_ENABLED,
            )
            notifications_enabled = str_to_bool( notifications_enabled_str )

            if not notifications_enabled:
                result.notifications_disabled = True
                logger.debug( 'Notifications are disabled, skipping maintenance.' )
                return result

            email_addresses_str = settings_manager.get_setting_value(
                NotifySetting.NOTIFICATIONS_EMAIL_ADDRESSES,
            )
            email_address_list = parse_emails_from_text( text = email_addresses_str )

            if not email_address_list:
                result.no_email_addresses = True

            # Get pending notifications
            notification_list = self._notification_queue.check_for_notifications()
            result.notifications_found = len(notification_list)
            logger.debug( f'Notifications found: {result.notifications_found}.' )

            # Process each notification
            for notification in notification_list:
                try:
                    if not email_address_list:
                        logger.info( f'No valid notification emails defined. Skipping: {notification}.' )
                        result.notifications_skipped += 1
                        continue

                    success = await self._send_email_notification_internal(
                        notification=notification,
                        email_address_list=email_address_list
                    )
                    if success:
                        result.notifications_sent += 1
                    else:
                        result.notifications_failed += 1
                except Exception as e:
                    logger.exception( f"Failed to send notification: {e}" )
                    result.notifications_failed += 1
                    error_msg = str(e)[:100]  # Truncate long error messages
                    if error_msg not in result.error_messages:
                        result.error_messages.append(error_msg)
                continue

        except Exception as e:
            logger.exception( "Problem checking notifications queue", e )
            result.error_messages.append(f"Queue check failed: {str(e)[:100]}")

        return result

    async def send_notifications( self, notification : Notification ) -> bool:
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return False
        notifications_enabled_str = settings_manager.get_setting_value(
            NotifySetting.NOTIFICATIONS_ENABLED,
        )
        notifications_enabled = str_to_bool( notifications_enabled_str )
        if not notifications_enabled:
            logger.debug( f'Notifications not enabled. Ignoring: {notification}.' )
            return False

        return await self.send_email_notification_if_needed_async( notification = notification )

    async def send_email_notification_if_needed_async( self, notification : Notification ) -> bool:
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return False
        email_addresses_str = settings_manager.get_setting_value(
            NotifySetting.NOTIFICATIONS_EMAIL_ADDRESSES,
        )
        email_address_list = parse_emails_from_text( text = email_addresses_str )
        if not email_address_list:
            logger.info( f'No valid notification emails defined. Ignoring: {notification}.' )
            return False

        return await self._send_email_notification_internal(
            notification=notification,
            email_address_list=email_address_list
        )

    async def _send_email_notification_internal(
        self,
        notification: Notification,
        email_address_list: List[str]
    ) -> bool:
        """Internal method to send email notification with known email list."""
        logger.debug( f'Sending notification email to "{email_address_list}": {notification}.' )

        email_data = EmailData(
            request = None,
            to_email_address = email_address_list,
            subject_template_name = 'notify/emails/notification_subject.txt',
            message_text_template_name = 'notify/emails/notification_message.txt',
            message_html_template_name = 'notify/emails/notification_message.html',
            template_context = { 'notification': notification },
        )

        try:
            email_sender = EmailSender( data = email_data )
            await email_sender.send_async()
            return True
        except Exception as e:
            logger.exception( f"Failed to send email notification: {e}" )
            raise
