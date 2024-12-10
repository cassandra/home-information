from dataclasses import dataclass, field
import logging
from typing import Dict, List

from django.conf import settings
from django.http.request import HttpRequest
from django.urls import reverse

from hi.apps.common.email_utils import send_html_email
from hi.apps.common.utils import hash_with_seed

from .models import UnsubscribedEmail

logger = logging.getLogger(__name__)


class UnsubscribedEmailError(Exception):
    pass


@dataclass
class EmailSenderData:
    request                     : HttpRequest
    subject_template_name       : str
    message_text_template_name  : str
    message_html_template_name  : str
    to_email_address            : str
    from_email_address          : str             = None  # Defaults to system-wide FROM
    template_context            : Dict[str, str]  = field( default_factory = dict )
    files                       : List            = None  # For attachments
    non_blocking                : bool            = True
                  
    # For testing (can use the unsubscribe link to test for the original intended "to" email)
    override_to_email_address   : str             = None
    
    
class EmailSender:
    """ For sending a single email message. """
    
    def __init__( self, data : EmailSenderData ):
        self._data = data
        return

    def send( self):
        if UnsubscribedEmail.objects.exists_by_email( email = self._data.to_email_address ):
            raise UnsubscribedEmailError( f'Email address is unsubscribed for {self._data.to_email_address}' )
        
        context = self._data.template_context
        self._add_base_url( context = context )
        self._add_game_home_url( context = context )
        self._add_unsubscribe_url( context = context )

        effective_to_email_address = self._data.to_email_address
        if self._data.override_to_email_address:
            effective_to_email_address = self._data.override_to_email_address

        send_html_email(
            request = self._data.request,
            subject_template_name = self._data.subject_template_name,
            message_text_template_name = self._data.message_text_template_name,
            message_html_template_name = self._data.message_html_template_name,
            to_email_addresses = [ effective_to_email_address ],
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
    
    def _add_game_home_url( self, context : Dict ):
        relative_url = reverse( 'game_home' )
        if self._data.request:
            context['USER_HOME_URL'] = self._data.request.build_absolute_uri( relative_url )
        elif "BASE_URL" in context:
            context['USER_HOME_URL'] = f'{context["BASE_URL"]}{relative_url}'
        return
    
    def _add_unsubscribe_url( self, context : Dict ):
        token = hash_with_seed( self._data.to_email_address )
        relative_url = reverse( 'user_unsubscribe_email',
                                kwargs = {
                                    'email': self._data.to_email_address,
                                    'token': token,
                                })
        if self._data.request:
            context['UNSUBSCRIBE_URL'] = self._data.request.build_absolute_uri( relative_url )
        elif "BASE_URL" in context:
            context['UNSUBSCRIBE_URL'] = f'{context["BASE_URL"]}{relative_url}'
        return
    
