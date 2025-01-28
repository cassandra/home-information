import logging

from django.contrib.auth import login as django_login
from django.http import HttpRequest
from django.urls import reverse

from hi.apps.common.singleton import Singleton
from hi.apps.notify.email_sender import EmailData, EmailSender

from .transient_models import UserAuthenticationData

logger = logging.getLogger(__name__)


class SigninManager( Singleton ):

    SIGNIN_SUBJECT_TEMPLATE_NAME = 'user/emails/signin_magic_link_subject.txt'
    SIGNIN_MESSAGE_TEXT_TEMPLATE_NAME = 'user/emails/signin_magic_link_message.txt'
    SIGNIN_MESSAGE_HTML_TEMPLATE_NAME = 'user/emails/signin_magic_link_message.html'
    
    def __init_singleton__(self):
        return
    
    def send_signin_magic_link_email( self,
                                      request        : HttpRequest,
                                      user_auth_data : UserAuthenticationData ):

        to_email_address = user_auth_data.email_address
        page_url = request.build_absolute_uri(
            reverse( 'user_signin_magic_link',
                     kwargs = { 'token': user_auth_data.token,
                                'email': user_auth_data.email_address } )
        )

        email_template_context = {
            'page_url': page_url,
            'magic_code': user_auth_data.magic_code,
        }
        email_sender_data = EmailData(
            request = request,
            subject_template_name = self.SIGNIN_SUBJECT_TEMPLATE_NAME,
            message_text_template_name = self.SIGNIN_MESSAGE_TEXT_TEMPLATE_NAME,
            message_html_template_name = self.SIGNIN_MESSAGE_HTML_TEMPLATE_NAME,
            to_email_address = to_email_address,
            template_context = email_template_context,
            non_blocking = True,
        )

        email_sender = EmailSender( data = email_sender_data )
        email_sender.send()
        return True

    def do_login( self, request, verified_email : str = False ):
        django_login( request, request.user )
        if not verified_email:
            return
        if request.user.email_verified:
            return
        request.user.email_verified = True
        request.user.save()
        return
