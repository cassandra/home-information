import logging

from django.contrib.auth import login as django_login
from django.http import HttpRequest
from django.urls import reverse

from hi.apps.common.singleton import Singleton
from hi.apps.common.email_sender import EmailSender, EmailSenderData

from .transient_models import UserAuthenticationData

logger = logging.getLogger(__name__)


class SigninManager( Singleton ):

    def __init_singleton__(self):
        return
    
    def send_signin_magic_link_email( self,
                                      request        : HttpRequest,
                                      user_auth_data : UserAuthenticationData ):

        _ = self.send_verify_email_helper(
            request = request,
            user_auth_data = user_auth_data,
            subject_template_name = 'user/emails/signin_magic_link_subject.txt',
            message_text_template_name = 'user/emails/signin_magic_link_message.txt',
            message_html_template_name ='user/emails/signin_magic_link_message.html',
        )
        return

    def send_verify_email_helper( self,
                                  request                     : HttpRequest,
                                  user_auth_data              : UserAuthenticationData,
                                  subject_template_name       : str,
                                  message_text_template_name  : str,
                                  message_html_template_name  : str,
                                  ):
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
        email_sender_data = EmailSenderData(
            request = request,
            subject_template_name = subject_template_name,
            message_text_template_name = message_text_template_name,
            message_html_template_name = message_html_template_name,
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
