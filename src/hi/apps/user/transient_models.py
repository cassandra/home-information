import logging

from django.contrib.auth.models import User as UserType
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http import HttpRequest

from .magic_code_generator import MagicCodeGenerator
from . import forms

logger = logging.getLogger(__name__)


class UserAuthenticationData:

    def __init__( self, request : HttpRequest, override_user : UserType = None ):
        if override_user:
            self._user = override_user
        else:
            self._user = request.user

        self._email_address = self._user.email
        
        # We re-purpose the clever way tokens are used for password resets in Django
        token_generator = PasswordResetTokenGenerator()
        self._token = token_generator.make_token( user = self._user )

        magic_code_generator = MagicCodeGenerator()
        self._magic_code = magic_code_generator.make_magic_code( request )

        self._magic_code_form = forms.SigninMagicCodeForm(
            initial = { 'email_address': self._email_address }
        )
        logger.debug( f'UserAuthenticationData: EMAIL = {self._user},'
                      f'TOKEN = {self._token}, CODE = {self._magic_code}' )
        return
    
    @property
    def user(self):
        return self._user
    
    @property
    def email_address(self):
        return self._email_address
    
    @property
    def token(self):
        return self._token
              
    @property
    def magic_code(self):
        return self._magic_code
                   
    @property
    def magic_code_form(self):
        return self._magic_code_form
