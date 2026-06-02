"""Fault injection for the weather-source simulators.

Parallels ``ServiceFaultInjectionMiddleware`` but scoped to each weather
source's API surface. The matcher targets ``/weather/<short_name>/api/``
only, so the tab pages and the fault-mode / state setters (which live
off the ``api/`` subpath) are never themselves faulted. A single source
short name covers all of that source's API endpoints — e.g. Open-Meteo's
forecast and archive endpoints both sit under ``/weather/openmeteo/api/``.
"""
import re

from hi.simulator.fault_injection import apply_fault_mode

from .fault_state import get_fault_mode


class WeatherFaultInjectionMiddleware:

    _WEATHER_API_RE = re.compile( r'^/weather/(?P<short_name>[^/]+)/api/' )

    def __init__(self, get_response):
        self.get_response = get_response
        return

    def __call__(self, request):
        match = self._WEATHER_API_RE.match( request.path )
        if not match:
            return self.get_response( request )
        fault_mode = get_fault_mode( match.group( 'short_name' ) )
        return apply_fault_mode( fault_mode, request, self.get_response )
