from django.conf import settings
from django.urls import resolve

from .views import UserSigninView


class AuthenticationMiddleware(object):

    EXEMPT_VIEW_URL_NAMES = {
        'admin',
        'manifest',
        'user_signin',
        'user_signin_magic_code',
        'user_signin_magic_link',
    }

    def __init__(self, get_response):
        self.get_response = get_response
        return

    def __call__(self, request):
        
        if settings.SUPPRESS_AUTHENTICATION or request.user.is_authenticated:
            return self.get_response( request )

        resolver_match = resolve( request.path )
        view_url_name = resolver_match.url_name
        app_name = resolver_match.app_name
        
        if (( app_name == 'admin' )
            or ( view_url_name in self.EXEMPT_VIEW_URL_NAMES )):
            return self.get_response(request)

        return UserSigninView().get( request )
