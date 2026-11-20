import logging

from django.core.exceptions import BadRequest, ValidationError
from django.core.validators import validate_email
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from hi.apps.notify.email_sender import EmailSender

from . import forms
from .magic_code_generator import MagicCodeStatus
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
        return SigninMagicCodeView().get_response(
            request = request,
            magic_code_form = forms.SigninMagicCodeForm(
                initial = { 'email_address': email_address }
            )
        )


class SigninMagicCodeView( View ):

    TEMPLATE_NAME = 'user/pages/magic_code_signin.html'

    ERROR_MESSAGES = {
        MagicCodeStatus.INVALID: 'Invalid access code.',
        MagicCodeStatus.EXPIRED: 'Access code has expired.',
    }

    def get_response( self,
                      request          : HttpRequest,
                      magic_code_form  : forms.SigninMagicCodeForm,
                      status           : int                           = 200 ):
        context = {
            'magic_code_form': magic_code_form,
        }
        response = render( request, self.TEMPLATE_NAME, context )
        response.status_code = status
        return response

    def post( self, request, *args, **kwargs ):

        magic_code_form = forms.SigninMagicCodeForm( request.POST )
        if not magic_code_form.is_valid():
            return self.get_response( request, magic_code_form = magic_code_form, status = 400 )

        magic_code_status = SigninManager().signin_with_magic_code(
            request = request,
            email_address = magic_code_form.cleaned_data.get('email_address'),
            magic_code = magic_code_form.cleaned_data.get('magic_code'),
        )
        error_message = self.ERROR_MESSAGES.get( magic_code_status )
        if error_message:
            magic_code_form.add_error( 'magic_code', error_message )
            return self.get_response( request, magic_code_form = magic_code_form, status = 400 )

        return HttpResponseRedirect( reverse( 'home' ))


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
