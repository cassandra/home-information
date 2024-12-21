import logging

from .sim_view_parameters import SimViewParameters

logger = logging.getLogger(__name__)


class SimViewMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        return
    
    def __call__(self, request):
        self._set_sim_view_parameters( request )
        return self.get_response( request )

    def _set_sim_view_parameters( self, request ):
        request.sim_view_parameters = SimViewParameters.from_session( request )
        return
