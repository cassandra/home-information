from django.http import HttpRequest
from django.urls import Resolver404, resolve, reverse

from hi.apps.security.security_manager import SecurityManager
from hi.apps.user.access import has_content_access

from .console_helper import ConsoleSettingsHelper
from .constants import ConsoleConstants
from .device_capabilities import DeviceCapabilitiesCookie
from .views import ConsoleUnlockView


class ConsoleLockMiddleware:

    EXCLUDED_PATHS = [
        reverse('console_unlock'),
        reverse('console_device_capabilities'),
        reverse('api_status' ),
    ]
    EXCLUDED_APP_NAME = 'admin'

    def __init__(self, get_response):
        self.get_response = get_response
        return

    def __call__(self, request):
        response = self.process_request( request )
        if response:
            return response
        response = self.get_response(request)
        return self.process_response( request, response )

    def process_request( self, request ):
        # The lock protects content. A session that can only reach the
        # sign-in flow has nothing to protect, and locking it would block
        # signing in (sign-in pages would get the unlock prompt).
        if not has_content_access( request ):
            return None

        self._process_away_auto_lock( request )

        if request.session.get( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, False ):
            if self._is_excluded( request ):
                return None
            return ConsoleUnlockView().get( request )
        return None

    def _is_excluded( self, request : HttpRequest ) -> bool:
        if request.path in self.EXCLUDED_PATHS:
            return True
        # The Django admin has its own staff login and is the way to
        # recover from problems (e.g., a forgotten PIN), so never lock it.
        try:
            return resolve( request.path ).app_name == self.EXCLUDED_APP_NAME
        except Resolver404:
            return False

    def _process_away_auto_lock( self, request : HttpRequest ) -> None:
        away_timestamp = SecurityManager().get_console_away_lock_timestamp()
        if not away_timestamp:
            return

        previous_away_timestamp = request.session.get(
            ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR
        )
        if str( previous_away_timestamp ) == str( away_timestamp ):
            return

        request.session[ConsoleConstants.CONSOLE_AWAY_LOCK_TIMESTAMP_SESSION_VAR] = str( away_timestamp )

        if request.session.get( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, False ):
            return

        if not ConsoleSettingsHelper().get_console_lock_pin():
            return

        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return

    def process_response(self, request, response):
        return response


class DeviceCapabilitiesMiddleware:
    """
    Attaches ``request.device_capabilities`` from the persisted cookie.
    Read-only: capabilities are declared only through
    DeviceCapabilitiesView, the dedicated kiosk entry point.
    """

    def __init__( self, get_response ):
        self.get_response = get_response
        return

    def __call__( self, request ):
        request.device_capabilities = DeviceCapabilitiesCookie.read( request )
        return self.get_response( request )
