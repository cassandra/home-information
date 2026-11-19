from django.http import HttpRequest
from django.urls import reverse

from hi.apps.security.security_manager import SecurityManager

from .console_helper import ConsoleSettingsHelper
from .constants import ConsoleConstants
from .device_capabilities import DeviceCapabilities, DeviceCapabilitiesCodec
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


class DeviceCapabilitiesMiddleware:
    """
    Attaches ``request.device_capabilities``. Capability query parameters
    are accepted on any request so a kiosk launch URL can point at any
    page; when present they are merged into the persisted cookie.
    """

    def __init__( self, get_response ):
        self.get_response = get_response
        return

    def __call__( self, request ):
        persisted = DeviceCapabilitiesCodec.from_cookie_value(
            request.COOKIES.get( ConsoleConstants.DEVICE_CAPABILITIES_COOKIE_NAME )
        )
        declarations = DeviceCapabilitiesCodec.declarations_from_query_params( request.GET )
        request.device_capabilities = persisted.with_declarations( declarations )

        response = self.get_response( request )

        if declarations:
            self._persist( response, request.device_capabilities )
        return response

    def _persist( self, response, device_capabilities : DeviceCapabilities ):
        cookie_name = ConsoleConstants.DEVICE_CAPABILITIES_COOKIE_NAME
        if device_capabilities.is_default:
            response.delete_cookie( cookie_name, samesite = 'Lax' )
            return
        response.set_cookie(
            cookie_name,
            DeviceCapabilitiesCodec.to_cookie_value( device_capabilities ),
            max_age = ConsoleConstants.DEVICE_CAPABILITIES_COOKIE_MAX_AGE_SECS,
            samesite = 'Lax',
            httponly = True,
        )
        return
