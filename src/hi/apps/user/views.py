import logging

from django.core.exceptions import BadRequest, ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from hi.apps.common.keypad_spec import KeypadEntry, KeypadField
from hi.apps.notify.email_sender import EmailSender

from . import forms
from .constants import UserConstants
from .magic_code_generator import MagicCodeStatus
from .signin_manager import SigninManager
from .transient_models import MagicCodePageState

logger = logging.getLogger(__name__)


class UserSigninView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'email_not_configured': not EmailSender.is_email_configured(),
        }
        return render( request, 'user/pages/signin.html', context )

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            raise BadRequest( 'You are already logged in.' )

        email_address = request.POST.get('email')
        if not email_address:
            raise BadRequest( 'No email provided' )

        try:
            validate_email( email_address )
        except ValidationError:
            raise BadRequest( 'Invalid email provided' )

        SigninManager().start_signin( request = request, email_address = email_address )
        return HttpResponseRedirect( reverse( 'user_signin_magic_code' ))


class SigninMagicCodeView( View ):
    """
    The access code page. Submits redirect back here (POST/redirect/GET), so
    reloading never resubmits an email (sending a new code) or a code (using
    up an attempt). SigninManager decides what the page shows.
    """

    TEMPLATE_NAME = 'user/pages/magic_code_signin.html'
    MAGIC_CODE_FIELD = KeypadField( name = 'magic_code' )

    MESSAGES = {
        MagicCodeStatus.INVALID: 'Invalid access code.',
        MagicCodeStatus.EXPIRED: 'Access code has expired. Send a new code to try again.',
        MagicCodeStatus.TOO_MANY_ATTEMPTS: 'Too many incorrect attempts. Send a new code to try again.',
        MagicCodeStatus.NO_CODE: 'This code has already been used or replaced. Send a new code to try again.',
    }

    def get( self, request, *args, **kwargs ):
        if request.user.is_authenticated:
            return HttpResponseRedirect( reverse( 'home' ))

        page_state = SigninManager().get_magic_code_page_state( request )
        if not page_state:
            return HttpResponseRedirect( reverse( 'user_signin' ))
        return self.render_page( request, page_state = page_state )

    def render_page( self, request, page_state : MagicCodePageState ):
        context = {
            'email_address': page_state.email_address,
        }
        message = self.MESSAGES.get( page_state.status )
        if page_state.attempts_remaining is not None:
            message = f'{message} {self._attempts_left_text( page_state.attempts_remaining )}'
        if page_state.is_code_usable:
            context['keypad_entry'] = KeypadEntry(
                spec = UserConstants.MAGIC_CODE_KEYPAD,
                fields = ( self.MAGIC_CODE_FIELD, ),
                error_message = message,
            )
        else:
            context['unusable_code_message'] = message
        return render( request, self.TEMPLATE_NAME, context )

    def _attempts_left_text( self, attempts_remaining : int ) -> str:
        noun = 'attempt' if attempts_remaining == 1 else 'attempts'
        return f'{attempts_remaining} {noun} left.'

    def post( self, request, *args, **kwargs ):
        if request.user.is_authenticated:
            return HttpResponseRedirect( reverse( 'home' ))

        magic_code_form = forms.SigninMagicCodeForm( request.POST )
        if magic_code_form.is_valid():
            magic_code_status = SigninManager().signin_with_magic_code(
                request = request,
                magic_code = magic_code_form.cleaned_data.get( self.MAGIC_CODE_FIELD.name ),
            )
            if magic_code_status == MagicCodeStatus.VALID:
                return HttpResponseRedirect( reverse( 'home' ))
        else:
            SigninManager().reject_malformed_code( request )

        return HttpResponseRedirect( reverse( 'user_signin_magic_code' ))


class SigninMagicLinkView( View ):
    """ This is the view for the links we include in emails for logging in. """

    def get( self, request, *args, **kwargs ):

        token = kwargs.get('token')
        email_address = kwargs.get('email')

        if not token or not email_address:
            raise BadRequest( 'Malformed request.' )

        if not SigninManager().signin_with_magic_link( request = request,
                                                       email_address = email_address,
                                                       token = token ):
            return render( request, 'user/pages/signin_magic_bad_link.html' )

        return HttpResponseRedirect( reverse( 'home' ))
