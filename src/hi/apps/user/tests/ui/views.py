from typing import Dict

from django.conf import settings
from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from hi.apps.notify.email_sender import EmailSender
from hi.apps.user.magic_code_generator import MagicCodeStatus
from hi.apps.user.signin_manager import SigninManager
from hi.apps.user.transient_models import MagicCodePageState, UserAuthenticationData
from hi.apps.user.views import SigninMagicCodeView

from hi.testing.ui.email_test_views import EmailTestViewView


UI_TEST_EMAIL_ADDRESS = 'someone.with.a.long.address@example.com'

MAGIC_CODE_PAGE_STATES = {
    'entry': MagicCodePageState( email_address = UI_TEST_EMAIL_ADDRESS, is_code_usable = True ),
    'invalid': MagicCodePageState( email_address = UI_TEST_EMAIL_ADDRESS, is_code_usable = True,
                                   status = MagicCodeStatus.INVALID, attempts_remaining = 2 ),
    'invalid_last_attempt': MagicCodePageState( email_address = UI_TEST_EMAIL_ADDRESS, is_code_usable = True,
                                                status = MagicCodeStatus.INVALID, attempts_remaining = 1 ),
    'expired': MagicCodePageState( email_address = UI_TEST_EMAIL_ADDRESS, is_code_usable = False,
                                   status = MagicCodeStatus.EXPIRED ),
    'too_many_attempts': MagicCodePageState( email_address = UI_TEST_EMAIL_ADDRESS, is_code_usable = False,
                                             status = MagicCodeStatus.TOO_MANY_ATTEMPTS ),
    'no_code': MagicCodePageState( email_address = UI_TEST_EMAIL_ADDRESS, is_code_usable = False,
                                   status = MagicCodeStatus.NO_CODE ),
}


class TestUiUserHomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'magic_code_page_states': MAGIC_CODE_PAGE_STATES.keys(),
        }
        return render(request, "user/tests/ui/home.html", context )


class TestUiMagicCodePageView( View ):
    """ The access code page in any state; some are slow to reach for real. """

    def get( self, request, *args, **kwargs ):
        state = kwargs.get( 'state' )
        if state not in MAGIC_CODE_PAGE_STATES:
            raise BadRequest( f'Unknown access code page state "{state}".' )
        return SigninMagicCodeView().render_page( request, page_state = MAGIC_CODE_PAGE_STATES[ state ] )

    
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

