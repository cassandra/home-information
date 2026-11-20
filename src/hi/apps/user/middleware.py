from django.http import JsonResponse
from django.urls import resolve

from hi.apps.common.utils import is_ajax

from .access import has_content_access
from .views import UserSigninView


class AuthenticationMiddleware:

    EXEMPT_VIEW_URL_NAMES = {
        'admin',
        'console_device_capabilities',
        'console_device_capability_unavailable',
        'manifest',
        'user_signin',
        'user_signin_magic_code',
        'user_signin_magic_link',
    }

    def __init__(self, get_response):
        self.get_response = get_response
        return

    def __call__(self, request):
        
        if has_content_access( request ):
            return self.get_response( request )

        resolver_match = resolve( request.path )
        view_url_name = resolver_match.url_name
        app_name = resolver_match.app_name
        
        if (( app_name == 'admin' )
            or ( view_url_name in self.EXEMPT_VIEW_URL_NAMES )):
            return self.get_response(request)

        return self._unauthenticated_response( request )

    def _unauthenticated_response( self, request ):
        # Async callers cannot use the sign-in page, so they get a 401 they
        # can detect (e.g., status polling shows a sign-in required banner).
        if is_ajax( request ):
            return JsonResponse( { 'error_message': 'Sign-in required.' }, status = 401 )
        return UserSigninView().get( request )
