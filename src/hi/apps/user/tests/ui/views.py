from typing import Dict

from django.conf import settings
from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from hi.apps.notify.email_sender import EmailSender
from hi.apps.user.signin_manager import SigninManager
from hi.apps.user.transient_models import UserAuthenticationData

from hi.tests.ui.email_test_views import EmailTestViewView


class TestUiUserHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "user/tests/ui/home.html", context )

    
class TestUiViewSigninEmailView( EmailTestViewView ):

    @property
    def app_name(self):
        return 'user'

    def get_extra_context( self, email_type : str ) -> Dict[ str, object ]:
        if email_type == 'signin_magic_link':
            return {
                'magic_code': 'abc123',
                'magic_code_lifetime_minutes': 123,
            }
        return dict()

    
class TestUiSendSigninEmailView( View ):
    """ Actually sending emails to ensure looks right on delivery. """
    
    def get( self, request, *args, **kwargs ):
        if not EmailSender.is_email_configured():
            raise NotImplementedError('Email is not configured for this server.')
        
        if request.user.is_anonymous or not request.user.email:
            email_address = settings.EMAIL_HOST_USER
        else:
            email_address = request.user.email
            
        email_type = kwargs.get('email_type')
        if email_type == 'signin_magic_link':
            user_auth_data = UserAuthenticationData(
                request = request,
                override_email = email_address,
            )
            SigninManager().send_signin_magic_link_email(
                request = request,
                user_auth_data = user_auth_data,
            )
        else:
            raise BadRequest( f'Sending email type "{email_type}" not implemented.' )
        
        return render( request, 'user/tests/ui/send_email_success.html' )

