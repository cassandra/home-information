import logging

from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth.models import User as UserType
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http import HttpRequest
from django.urls import reverse

from hi.apps.common.singleton import Singleton
from hi.apps.notify.email_sender import EmailData, EmailSender

from .magic_code_generator import MagicCodeGenerator, MagicCodeStatus
from .transient_models import UserAuthenticationData

logger = logging.getLogger(__name__)


class SigninManager( Singleton ):
    """
    Owns the password-less sign-in policy. Every path must behave the same
    whether or not an account exists for the email address, so that responses
    do not reveal which email addresses have accounts.
    """

    SIGNIN_SUBJECT_TEMPLATE_NAME = 'user/emails/signin_magic_link_subject.txt'
    SIGNIN_MESSAGE_TEXT_TEMPLATE_NAME = 'user/emails/signin_magic_link_message.txt'
    SIGNIN_MESSAGE_HTML_TEMPLATE_NAME = 'user/emails/signin_magic_link_message.html'
    
    def __init_singleton__(self):
        return

    def start_signin( self, request : HttpRequest, email_address : str ):
        """
        Issues a code bound to the email address. If no account exists, the
        code is issued but never sent, so the session changes identically.
        """
        existing_user = self._get_user( email_address )
        if not existing_user:
            logger.debug( f'No user exists with email: {email_address}' )
            MagicCodeGenerator().make_magic_code( request, email_address = email_address )
            return

        user_auth_data = UserAuthenticationData(
            request = request,
            override_user = existing_user,
        )
        self.send_signin_magic_link_email(
            request = request,
            user_auth_data = user_auth_data,
        )
        return

    def signin_with_magic_code( self,
                                request        : HttpRequest,
                                email_address  : str,
                                magic_code     : str ) -> MagicCodeStatus:
        magic_code_status = MagicCodeGenerator().redeem_magic_code(
            request,
            email_address = email_address,
            magic_code = magic_code,
        )
        if magic_code_status == MagicCodeStatus.VALID:
            existing_user = self._get_user( email_address )
            if existing_user:
                self._signin_verified_user( request, existing_user )
            else:
                magic_code_status = MagicCodeStatus.INVALID

        logger.debug( f'Signin Magic Code: Email={email_address}, Status={magic_code_status}' )
        return magic_code_status

    def signin_with_magic_link( self,
                                request        : HttpRequest,
                                email_address  : str,
                                token          : str ) -> bool:
        existing_user = self._get_user( email_address )
        # We re-purpose the clever way tokens are used for password resets in Django
        is_valid = bool( existing_user
                         and PasswordResetTokenGenerator().check_token( user = existing_user, token = token ))

        logger.debug( f'Signin Magic Link: Email={email_address}, Valid={is_valid}' )
        if is_valid:
            self._signin_verified_user( request, existing_user )
        return is_valid

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
            'magic_code_lifetime_minutes': MagicCodeGenerator.get_timeout_minutes(),
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

    def _signin_verified_user( self, request : HttpRequest, user : UserType ):
        request.user = user
        self.do_login( request = request, verified_email = True )
        return

    def _get_user( self, email_address : str ) -> UserType:
        return get_user_model().objects.filter( email = email_address ).first()
