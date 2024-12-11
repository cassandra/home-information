import logging

from hi.apps.common.email_utils import parse_emails_from_text
from hi.apps.common.singleton import Singleton
from hi.apps.common.utils import str_to_bool
from hi.apps.config.enums import SubsystemAttributeType
from hi.apps.config.settings_manager import SettingsManager
from hi.apps.notify.notification_queue import NotificationQueue

from .email_sender import EmailSender
from .transient_models import EmailData, Notification, NotificationItem

logger = logging.getLogger(__name__)


class NotificationManager(Singleton):

    def __init_singleton__(self):
        self._notification_queue = NotificationQueue()
        self._settings_manager = SettingsManager()
        return

    def add_notification_item( self, notification_item : NotificationItem ):
        self._notification_queue.add_item( notification_item = notification_item )
        return
    
    async def do_periodic_maintenance(self):
        try:
            notification_list = self._notification_queue.check_for_notifications()
            logger.debug( f'Notifications found: {len(notification_list)}.' )
            for notification in notification_list:
                await self.send_notifications( notification )
                continue
        except Exception as e:
            logger.exception( "Problem sending notifications", e )
        return

    async def send_notifications( self, notification : Notification ) -> bool:
        notifications_enabled_str = self._settings_manager.get_setting_value(
            SubsystemAttributeType.NOTIFICATIONS_ENABLED,
        )
        notifications_enabled = str_to_bool( notifications_enabled_str )
        if not notifications_enabled:
            logger.debug( f'Notifications not enabled. Ignoring: {notification}.' )
            return False

        return await self.send_email_notification_if_needed_async( notification = notification )
    
    async def send_email_notification_if_needed_async( self, notification : Notification ) -> bool:
        
        email_addresses_str = self._settings_manager.get_setting_value(
            SubsystemAttributeType.NOTIFICATIONS_EMAIL_ADDRESSES,
        )
        email_address_list = parse_emails_from_text( text = email_addresses_str )
        if not email_address_list:
            logger.debug( f'No valid notification emails defined. Ignoring: {notification}.' )
            return False

        logger.debug( f'Sending notification email to "{email_address_list}": {notification}.' )

        email_data = EmailData(
            request = None,
            to_email_address = email_address_list,            
            subject_template_name = 'notify/emails/notification_subject.txt',
            message_text_template_name = 'notify/emails/notification_message.txt',
            message_html_template_name = 'notify/emails/notification_message.html',
            template_context = { 'notification': notification },
        )
        email_sender = EmailSender( data = email_data )
        await email_sender.send_async()
        return True
