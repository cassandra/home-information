from django.urls import reverse

from .constants import ConsoleConstants
from .views import ConsoleUnlockView


class ConsoleLockMiddleware:

    EXCLUDED_PATHS = [ reverse('console_unlock'), reverse('api_status' ) ]

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
        if request.session.get( ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR, False ):
            if request.path in self.EXCLUDED_PATHS:
                return None
            return ConsoleUnlockView().get( request )
        return None
    
    def process_response(self, request, response):
        return response
