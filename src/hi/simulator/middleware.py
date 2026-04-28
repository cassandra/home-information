import logging
import os
import re
import time

from django.http import HttpResponse, JsonResponse

from .enums import SimulatorFaultMode
from .sim_view_parameters import SimViewParameters
from .simulator_manager import SimulatorManager

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


class SimulatorFaultInjectionMiddleware:
    """
    Intercepts requests under /services/<short_name>/<...> and applies the
    target simulator's current fault mode. Lets manual end-to-end testing
    of the main app's integration test_connection probe failure paths
    proceed without standing up real misbehaving servers.

    Each service can define its own URL layout, so this matcher does NOT
    assume any specific subpath structure (e.g., /api/) — any request
    under a service's mount is subject to fault injection. The fault-mode
    setter lives at a top-level simulator URL (/fault-mode/set/...) and
    therefore never matches this prefix.

    SLOW mode sleeps and then lets the real view run, so the failure that
    surfaces upstream is the integration's read timeout — not a 5xx —
    which is exactly the bucket we want to exercise.
    """

    _SERVICE_PATH_RE = re.compile( r'^/services/(?P<short_name>[^/]+)/' )

    SLOW_FAULT_SECS = float( os.environ.get( 'HI_SIM_SLOW_FAULT_SECS', '10.0' ))

    def __init__(self, get_response):
        self.get_response = get_response
        self._segment_to_simulator = None  # Lazy-built on first request
        return

    def __call__(self, request):
        match = self._SERVICE_PATH_RE.match( request.path )
        if not match:
            return self.get_response( request )

        simulator = self._resolve_simulator( match.group('short_name') )
        if simulator is None:
            return self.get_response( request )

        fault_mode = simulator.fault_mode
        if fault_mode == SimulatorFaultMode.HEALTHY:
            return self.get_response( request )

        if fault_mode == SimulatorFaultMode.AUTH_FAIL:
            return JsonResponse(
                { 'message': 'Unauthorized' },
                status = 401,
            )

        if fault_mode == SimulatorFaultMode.SERVER_ERROR:
            return JsonResponse(
                { 'message': 'Internal server error' },
                status = 500,
            )

        if fault_mode == SimulatorFaultMode.SLOW:
            logger.debug( f'Fault injection: sleeping {self.SLOW_FAULT_SECS}s for {request.path}' )
            time.sleep( self.SLOW_FAULT_SECS )
            return self.get_response( request )

        if fault_mode == SimulatorFaultMode.NON_JSON:
            return HttpResponse(
                b'<html><body>simulated non-JSON response</body></html>',
                content_type = 'text/html',
                status = 200,
            )

        return self.get_response( request )

    def _resolve_simulator(self, short_name):
        if self._segment_to_simulator is None:
            mapping = {}
            for sim_data in SimulatorManager().get_simulator_data_list():
                mapping[ sim_data.simulator.url_path_segment ] = sim_data.simulator
            self._segment_to_simulator = mapping
        return self._segment_to_simulator.get( short_name )
