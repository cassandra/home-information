import asyncio
import html
from typing import Dict

from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import View

from hi.apps.notify.notify_mixins import NotificationMixin
from hi.apps.notify.tests.synthetic_data import NotifySyntheticData


class TestUiNotifyHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "notify/tests/ui/home.html", context )

    
class TestUiViewEmailView( View ):

    def get( self, request, *args, **kwargs ):
        context = self.get_context_for_email_message( request, *args, **kwargs )
        return self.email_preview_response(
            request = request,
            app_name = 'notify',
            view_name = context.get('email_type', 'Not specifified'),
            context = context,
        )

    def get_context_for_email_message( self, request, *args, **kwargs ) -> Dict[ str, object ]:
        email_type = kwargs.get('email_type')
        if email_type == 'notification':
            notification = NotifySyntheticData().create_random_notification()
            return {
                'email_type': email_type,
                'notification': notification,
            }
        return dict()

    def email_preview_response( self, request, app_name : str, view_name : str, context : dict ):

        context.update({
            'view_name': view_name,
            'BASE_URL': ' ',
            'UNSUBSCRIBE_URL': 'https://example.com/unsubscribe',
            'USER_HOME_URL': 'https://example.com/home',
        })

        # Need to make sure inline CSS of HTML email does not clash with
        # site's main CSS.  Using IFRAME for this, and the "srcdoc"
        # atttribute need us to pre-render.
        #
        body_html_template = f'{app_name}/emails/{view_name}_message.html'
        body_html = render_to_string( body_html_template, context )
        escaped_email_html = html.escape( body_html )

        context.update({
            'subject_text_template': f'{app_name}/emails/{view_name}_subject.txt',
            'body_text_template': f'{app_name}/emails/{view_name}_message.txt',
            'body_html_template': body_html_template,
            'body_html': escaped_email_html, 
        })
        return render( request, 'notify/tests/ui/email_preview.html', context )


class TestUiSendEmailView( View, NotificationMixin ):

    def get( self, request, *args, **kwargs ):
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
    
