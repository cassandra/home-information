from constance import config
import logging

from .view_parameters import ViewParameters

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
        request.is_editing = request.view_parameters.edit_mode.is_editing
        return
    
