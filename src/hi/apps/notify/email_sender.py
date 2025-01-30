from asgiref.sync import sync_to_async
from dataclasses import dataclass, field
import logging
from typing import Dict, List, Union

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.urls import reverse

from hi.apps.common.email_utils import send_html_email
from hi.apps.common.utils import hash_with_seed

from .models import UnsubscribedEmail

logger = logging.getLogger(__name__)


class UnsubscribedEmailError(Exception):
    pass


@dataclass
class EmailData:
    """
    Input data format for sending emails with EmailSender. Caller defines
    the three required templates for formatting the email. The email sender
    will create a template context that includes the following variables
    that should be used in the email:

        BASE_URL  - Use this to forms any needed site links.
        HOME_URL - Url to the site's main landing page page.
        UNSUBSCRIBE_URL - Include as best practice if you send email more broadly.

    The templates are best defined by extending some pre-defined base
    templates to make all emails have a consistent formatting. e.g.,
    Unsubscribe URL appearing in footer.
    """

    # Set the request to None for background tasks, but also make sure
    # settings.BASE_URL_FOR_EMAIL_LINKS is set.
    #
    request                     : HttpRequest
    
    subject_template_name       : str
    message_text_template_name  : str
    message_html_template_name  : str
    to_email_address            : Union[ str, List[ str ]]

    # Defaults to system-wide settings.DEFAULT_FROM_EMAIL
    from_email_address          : str             = None
    
    template_context            : Dict[str, str]  = field( default_factory = dict )
    files                       : List            = None  # For attachments
    non_blocking                : bool            = True
                  
    # For testing (can use the unsubscribe link to test for the original intended "to" email)
    override_to_email_address   : str             = None


class EmailSender:
    """ For sending a single email message. """

    HOME_URL_NAME = 'home'
    UNSUBSCRIBE_URL_NAME = 'notify_email_unsubscribe'
    
    def __init__( self, data : EmailData ):
        self._data = data
        return

    def send(self):
        self._assert_not_unsubscribed()
        self._send_helper()
        return
    
    async def send_async( self):
        await self._assert_not_unsubscribed_async()
        self._send_helper()
        return
        
    def _send_helper(self):
        self._assert_email_configured()
        
        context = self._data.template_context
        self._add_base_url( context = context )
        self._add_home_url( context = context )
        self._add_unsubscribe_url( context = context )

        if self._data.override_to_email_address:
            effective_to_email_address = self._data.override_to_email_address
        else:
            effective_to_email_address = self._data.to_email_address
            
        send_html_email(
            request = self._data.request,
            subject_template_name = self._data.subject_template_name,
            message_text_template_name = self._data.message_text_template_name,
            message_html_template_name = self._data.message_html_template_name,
            to_email_addresses = effective_to_email_address,
            from_email_address = self._data.from_email_address,
            context = context,
            files = self._data.files,
            non_blocking = self._data.non_blocking,
        )
        return

    def _add_base_url( self, context : Dict ):
        if self._data.request:
            context['BASE_URL'] = self._data.request.build_absolute_uri('/')[:-1]
        else:
            context['BASE_URL'] = settings.BASE_URL_FOR_EMAIL_LINKS
        return
    
    def _add_home_url( self, context : Dict ):
        relative_url = reverse( self.HOME_URL_NAME )
        if self._data.request:
            context['HOME_URL'] = self._data.request.build_absolute_uri( relative_url )
        elif "BASE_URL" in context:
            context['HOME_URL'] = f'{context["BASE_URL"]}{relative_url}'
        return
    
    def _add_unsubscribe_url( self, context : Dict ):
        token = hash_with_seed( self._data.to_email_address )
        relative_url = reverse( self.UNSUBSCRIBE_URL_NAME,
                                kwargs = {
                                    'email': self._data.to_email_address,
                                    'token': token,
                                })
        if self._data.request:
            context['UNSUBSCRIBE_URL'] = self._data.request.build_absolute_uri( relative_url )
        elif "BASE_URL" in context:
            context['UNSUBSCRIBE_URL'] = f'{context["BASE_URL"]}{relative_url}'
        return
    
    async def _assert_not_unsubscribed_async( self ):
        await sync_to_async( self._assert_not_unsubscribed,
                             thread_sensitive = True )()
        return
    
    def _assert_not_unsubscribed( self ):
        email_address = self._data.to_email_address
        if UnsubscribedEmail.objects.exists_by_email( email = email_address ):
            raise UnsubscribedEmailError( f'Email address is unsubscribed for {email_address}' )
        return
    
    def _assert_email_configured( self ):
        missing_names = self.get_missing_email_setting_names()
        if missing_names:
            raise ImproperlyConfigured( 'Email is not configured. Missing: %s.'
                                        % ', '.join( missing_names ))
        return
    
    @classmethod
    def is_email_configured( cls ) -> bool:
        missing_names = cls.get_missing_email_setting_names()
        if missing_names:
            return False
        return True
    
    @classmethod
    def get_missing_email_setting_names( cls ) -> List[ str ]:
        missing_names = list()
        for setting_name in [ 'EMAIL_BACKEND',
                              'EMAIL_HOST',
                              'EMAIL_PORT',
                              'EMAIL_HOST_USER',
                              'DEFAULT_FROM_EMAIL',
                              'SERVER_EMAIL' ]:
            email_setting = getattr( settings, setting_name )
            if not email_setting:
                missing_names.append( setting_name )
            continue
        return missing_names
