import html
from typing import Dict

from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.generic import View


class EmailTestViewView( View ):
    """ For visually seeing email without sending for formatting """

    @property
    def app_name(self):
        raise NotImplementedError('Subclasses must override this' )

    def get_extra_context( self, email_type : str ) -> Dict[ str, object ]:
        raise NotImplementedError('Subclasses must override this' )

    def get( self, request, *args, **kwargs ):
        context = self.get_context_for_email_message( request, *args, **kwargs )
        return self.email_preview_response(
            request = request,
            app_name = self.app_name,
            view_name = context.get('email_type', 'NOT_SPECIFIED'),
            context = context,
        )

    def get_context_for_email_message( self, request, *args, **kwargs ) -> Dict[ str, object ]:
        email_type = kwargs.get('email_type')
        context = {
            'email_type': email_type,
        }
        context.update( self.get_extra_context( email_type = email_type ))
        return context
                        
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
        return render( request, 'tests/ui/email_preview.html', context )
