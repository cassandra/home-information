import logging
import re

from hi.simulator.fault_injection import apply_fault_mode

from .service_simulator_manager import ServiceSimulatorManager

logger = logging.getLogger(__name__)


class ServiceFaultInjectionMiddleware:
    """
    Intercepts requests under /services/<short_name>/<...> and applies the
    target simulator's current fault mode. Lets manual end-to-end testing
    of the main app's integration validate_access probe failure paths
    proceed without standing up real misbehaving servers.

    Each service can define its own URL layout, so this matcher does NOT
    assume any specific subpath structure (e.g., /api/) — any request
    under a service's mount is subject to fault injection. The fault-mode
    setter lives at a top-level simulator URL (/fault-mode/set/...) and
    therefore never matches this prefix.

    The mode→response mapping (including SLOW's sleep-then-passthrough) is
    shared with the weather-sources middleware via
    ``hi.simulator.fault_injection.apply_fault_mode``.
    """

    _SERVICE_PATH_RE = re.compile( r'^/services/(?P<short_name>[^/]+)/' )

    def __init__(self, get_response):
        self.get_response = get_response
        return

    def __call__(self, request):
        match = self._SERVICE_PATH_RE.match( request.path )
        if not match:
            return self.get_response( request )

        simulator = self._resolve_simulator( match.group('short_name') )
        if simulator is None:
            return self.get_response( request )

        return apply_fault_mode( simulator.fault_mode, request, self.get_response )

    def _resolve_simulator(self, short_name):
        # No cache — the lookup is cheap (small list, dict comprehension)
        # and avoids staleness if the simulator registry is ever changed
        # at runtime (e.g., test isolation, future dynamic registration).
        for sim_data in ServiceSimulatorManager().get_simulator_data_list():
            if sim_data.simulator.url_path_segment == short_name:
                return sim_data.simulator
        return None
