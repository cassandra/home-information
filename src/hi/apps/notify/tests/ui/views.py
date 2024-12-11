import html

from django.shortcuts import render
from django.template.loader import render_to_string

from django.views.generic import View

from hi.apps.notify.tests.synthetic_data import NotifySyntheticData


class TestUiNotifyHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "notify/tests/ui/home.html", context )

    
class TestUiViewEmailView( View ):

    def get( self, request, *args, **kwargs ):
        view_name = kwargs.get('name')
        notification = NotifySyntheticData().create_random_notification()
        context = {
            'notification': notification,
        }
        return self.email_preview_response(
            request = request,
            app_name = 'notify',
            view_name = view_name,
            context = context,
        )

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


class TestUiSendEmailView( View ):
    pass
