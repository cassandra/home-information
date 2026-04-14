from django.http import HttpRequest
from django.urls import reverse

from hi.apps.security.security_manager import SecurityManager

from .console_helper import ConsoleSettingsHelper
from .constants import ConsoleConstants
from .views import ConsoleUnlockView


class ConsoleLockMiddleware:

    EXCLUDED_PATHS = [
        reverse('console_unlock'),
        reverse('api_status' ),
    ]

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
        self._process_away_auto_lock( request )

        if request.session.get( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, False ):
            if request.path in self.EXCLUDED_PATHS:
                return None
            return ConsoleUnlockView().get( request )
        return None

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

        lock_password = ConsoleSettingsHelper().get_console_lock_password()
        if not lock_password:
            return

        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        return

    def process_response(self, request, response):
        return response
