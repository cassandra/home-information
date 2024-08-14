import logging
import re
import threading
from typing import List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

import waa.apps.common.metrics as metrics

logger = logging.getLogger(__name__)


ALLOW_NON_BLOCKING_EMAILS = bool( not settings.DEBUG )


def parse_emails_from_text( text ):
    result_list = list()
    if not text:
        return result_list
    
    for line in text.split( '\n' ):
        for element in re.split( r'[\,\;]+', line ):
            if element.strip():
                result_list.append( element.strip() )
            continue
        continue
    return result_list


def safe_subject( subject ):
    """
    For security reasons, Django does not allow newlines in
    header fields. This replaces all newlines and carriage returns 
    with a space.
    """
    return subject.replace('\n', ' ').replace('\r',' ').strip()


def send_html_email( request,
                     subject_template_name,
                     message_text_template_name,
                     message_html_template_name,
                     to_email_addresses : List[str],
                     from_email_address = None,
                     context = None,
                     files = None,
                     non_blocking = False,
                     from_email_name = None ):
    
    if not from_email_address:
        from_email_address = settings.DEFAULT_FROM_EMAIL
    if not from_email_name:
        from_email_name = settings.FROM_EMAIL_NAME
        
    if not isinstance( to_email_addresses, list ):
        to_email_addresses = [ to_email_addresses, ]        

    if context is None:
        context = {}

    # If wanting to reference images and other static content in HTML,
    # we'll need the base url.
    #
    if request and ( 'BASE_URL' not in context ):
        context['BASE_URL'] = request.build_absolute_uri('/')[:-1]
            
    subject = render_to_string( subject_template_name, context )
    subject = safe_subject( subject )
    message_text = render_to_string( message_text_template_name, context )
    message_html = render_to_string( message_html_template_name, context )

    message = EmailMultiAlternatives(
        subject,
        message_text.strip(),
        "%s <%s>" % ( from_email_name, from_email_address ),
        to_email_addresses,
    )
    message.attach_alternative( message_html, "text/html")

    if files:
        if files is not list:
            files = [ files ]
        for file in files:
            message.attach_file(file)

    if non_blocking and not settings.UNIT_TESTING:  # Unit tests will fail if async emails
        EmailThread( message = message ).start()
    else:
        message.send()
        
    return


class EmailThread( threading.Thread ):
    
    def __init__( self, message : EmailMultiAlternatives ):
        self.message = message
        threading.Thread.__init__( self )
        return
    
    def run(self):
        try:
            self.message.send()
        except Exception as e:
            logger.exception( 'Problem in email thread.' )
            metrics.exception( e )
        return
