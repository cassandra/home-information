import logging
from typing import Optional

from django.core.exceptions import BadRequest, ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from hi.apps.notify.email_sender import EmailSender

from hi.apps.common.keypad_spec import KeypadEntry, KeypadField

from . import forms
from .constants import UserConstants
from .magic_code_generator import MagicCodeGenerator, MagicCodeStatus
from .signin_manager import SigninManager

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
    up an attempt). A failed submit's outcome is carried to the next page
    load only.
    """

    TEMPLATE_NAME = 'user/pages/magic_code_signin.html'
    MAGIC_CODE_FIELD = KeypadField( name = 'magic_code' )
    LAST_STATUS_SESSION_VAR = 'signin_magic_code_last_status'

    ERROR_MESSAGES = {
        MagicCodeStatus.INVALID: 'Invalid access code.',
        MagicCodeStatus.EXPIRED: 'Access code has expired. Send a new code to try again.',
        MagicCodeStatus.TOO_MANY_ATTEMPTS: 'Too many incorrect attempts. Send a new code to try again.',
        MagicCodeStatus.NO_CODE: 'This access code is no longer valid. Send a new code to try again.',
    }
    # Only a new code can succeed after these.
    UNUSABLE_CODE_STATUSES = {
        MagicCodeStatus.EXPIRED,
        MagicCodeStatus.TOO_MANY_ATTEMPTS,
        MagicCodeStatus.NO_CODE,
    }

    def get( self, request, *args, **kwargs ):
        if request.user.is_authenticated:
            return HttpResponseRedirect( reverse( 'home' ))

        email_address = SigninManager().get_signin_email( request )
        if not email_address:
            return HttpResponseRedirect( reverse( 'user_signin' ))

        magic_code_status = self._pop_last_status( request )
        if ( magic_code_status is None ) and not MagicCodeGenerator().has_pending_code( request ):
            magic_code_status = MagicCodeStatus.NO_CODE
        return self.render_page( request,
                                 email_address = email_address,
                                 magic_code_status = magic_code_status )

    def render_page( self,
                     request,
                     email_address      : str,
                     magic_code_status  : Optional[ MagicCodeStatus ] ):
        """ Code entry, showing why the last code failed, or that only a new code can succeed. """
        context = {
            'email_address': email_address,
        }
        message = self.ERROR_MESSAGES.get( magic_code_status )
        if magic_code_status in self.UNUSABLE_CODE_STATUSES:
            context['unusable_code_message'] = message
        else:
            context['keypad_entry'] = KeypadEntry(
                spec = UserConstants.MAGIC_CODE_KEYPAD,
                fields = ( self.MAGIC_CODE_FIELD, ),
                error_message = message,
            )
        return render( request, self.TEMPLATE_NAME, context )

    def post( self, request, *args, **kwargs ):

        magic_code_form = forms.SigninMagicCodeForm( request.POST )
        if magic_code_form.is_valid():
            magic_code_status = SigninManager().signin_with_magic_code(
                request = request,
                email_address = magic_code_form.cleaned_data.get('email_address'),
                magic_code = magic_code_form.cleaned_data.get('magic_code'),
            )
            if magic_code_status == MagicCodeStatus.VALID:
                return HttpResponseRedirect( reverse( 'home' ))
        else:
            magic_code_status = MagicCodeStatus.INVALID

        request.session[self.LAST_STATUS_SESSION_VAR] = magic_code_status.name
        return HttpResponseRedirect( reverse( 'user_signin_magic_code' ))

    def _pop_last_status( self, request ) -> Optional[ MagicCodeStatus ]:
        status_name = request.session.pop( self.LAST_STATUS_SESSION_VAR, None )
        if status_name is None:
            return None
        return MagicCodeStatus[ status_name ]


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
