import asyncio
from typing import Dict

from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from hi.apps.config.settings_manager import SettingsManager
from hi.apps.notify.email_sender import EmailSender
from hi.apps.notify.notify_mixins import NotificationMixin
from hi.apps.notify.tests.synthetic_data import NotifySyntheticData
from hi.apps.notify.settings import NotifySetting

from hi.tests.ui.email_test_views import EmailTestViewView


class TestUiNotifyHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "notify/tests/ui/home.html", context )

    
class TestUiViewEmailView( EmailTestViewView ):

    @property
    def app_name(self):
        return 'notify'

    def get_extra_context( self, email_type : str ) -> Dict[ str, object ]:
        if email_type == 'notification':
            notification = NotifySyntheticData().create_random_notification()
            return {
                'notification': notification,
            }
        return dict()

    
class TestUiSendEmailView( View, NotificationMixin ):

    def get( self, request, *args, **kwargs ):

        if not EmailSender.is_email_configured():
            raise NotImplementedError('Email is not configured for this server.')
        
        email_addresses_str = SettingsManager().get_setting_value(
            NotifySetting.NOTIFICATIONS_EMAIL_ADDRESSES,
        )
        if not email_addresses_str:
            raise NotImplementedError('No notification addresses have been defined in the settings.')
        
        email_type = kwargs.get('email_type')
        if email_type == 'notification':
            notification = NotifySyntheticData().create_random_notification()
            send_email_coroutine = self.notification_manager().send_email_notification_if_needed_async(
                notification = notification,
            )
            result = asyncio.run( send_email_coroutine )
            if not result:
                raise Exception( 'No able to send. Check email address configuration.' )

        else:
            raise BadRequest( f'Sending email type "{email_type}" not implemented.' )
        
        return render( request, 'notify/tests/ui/send_email_success.html' )
    
