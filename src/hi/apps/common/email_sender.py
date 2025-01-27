from dataclasses import dataclass, field
import logging
from typing import Dict, List

from django.conf import settings
from django.http.request import HttpRequest

from hi.apps.common.email_utils import send_html_email

logger = logging.getLogger(__name__)


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
                  
    # For testing
    override_to_email_address   : str             = None
    
    
class EmailSender:
    """ For sending a single email message. """
    
    def __init__( self, data : EmailSenderData ):
        self._data = data
        return

    def send( self):
        
        context = self._data.template_context
        self._add_base_url( context = context )

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
