import logging

from django.conf import settings
from django.core.exceptions import (
    BadRequest,
    PermissionDenied,
    SuspiciousOperation,
)
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseNotAllowed,
    HttpResponseServerError,
)

from .view_parameters import ViewParameters
from . import views

logger = logging.getLogger(__name__)


class ViewMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        return
    
    def __call__(self, request):
        self._set_view_parameters( request )
        return self.get_response( request )

    def _set_view_parameters( self, request ):
        request.view_parameters = ViewParameters.from_session( request )
        request.is_editing = request.view_parameters.view_mode.is_editing
        return

    
class ExceptionMiddleware(object):

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
        return None
        
    def process_exception( self, request, exception ):
        ip_address = request.META.get( 'HTTP_X_FORWARDED_FOR' )  # nginx forwarded
        logger.warning( f'Exception caught in middleware [{ip_address}]: {exception}' )
        
        if isinstance( exception, BadRequest ):
            return views.bad_request_response(request, message=str(exception))
        if isinstance( exception, SuspiciousOperation ):
            return views.bad_request_response(request, message=str(exception))
        if isinstance( exception, PermissionDenied ):
            return views.not_authorized_response(request, message=str(exception))
        if isinstance( exception, Http404 ):
            return views.page_not_found_response(request, message=str(exception))

        logger.exception( f'Exception caught in middleware: {exception}' )
        return views.internal_error_response(request, message=str(exception) )

    def process_response(self, request, response):

        if isinstance(response, HttpResponseBadRequest):
            return views.bad_request_response(request)
        if isinstance(response, HttpResponseForbidden):
            return views.not_authorized_response(request)
        if isinstance(response, HttpResponseNotFound):
            # We define a custom 404 handler (in urls.py) and emit this
            # response type, so no need to double up. However, the custom
            # 404 handler is not used when DEBUG=True.
            if settings.DEBUG:
                return views.page_not_found_response(request)
            return response  
        if isinstance(response, HttpResponseNotAllowed):
            return views.method_not_allowed_response(request)
        if isinstance(response, HttpResponseServerError):
            logger.warning( 'Internal error in middleware' )
            return views.internal_error_response(request)
        return response


