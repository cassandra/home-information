"""Simulator-only logging filters.

Kept separate from the main app's ``hi.testing.utils.log_filters`` because the
noisy endpoints differ entirely: the simulator is polled by HI's integration
and weather pollers plus the Scenes status poll, and those URL names only
resolve against the simulator's urlconf. Wired in via
``hi.settings.simulator``'s LOGGING override.
"""
import logging
import re

from django.conf import settings
from django.urls import resolve


class SuppressSimulatorPollingFilter( logging.Filter ):
    """Drop ``django.server`` request logs for the simulator's frequently-polled
    endpoints so they don't drown out everything else in the dev console.

    Matches by URL name (resolved against the simulator urlconf), not hardcoded
    paths, so route changes don't silently re-enable the noise. Gated on
    ``settings.SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING`` (shared toggle), and
    fail-open: any parsing/resolution hiccup keeps the log line.
    """

    URL_NAMES_TO_SUPPRESS = {
        # HI integration pollers (Home Assistant, ZoneMinder, Frigate states)
        'hass_api_states',
        'zm_api_events_index',
        'simulator_api_states',
        # Weather-source pollers
        'simulator_weather_usno_api',
        'simulator_weather_sunrise_sunset_api',
        'simulator_weather_nws_observations',
        'simulator_weather_nws_points',
        'simulator_weather_nws_forecast_hourly',
        'simulator_weather_nws_alerts_active',
        'simulator_weather_openmeteo_forecast',
        'simulator_weather_openmeteo_archive',
        # Simulator UI live polling
        'simulator_scene_status',
    }

    def filter( self, record ):
        if not getattr( settings, 'SUPPRESS_SELECT_REQUEST_ENPOINTS_LOGGING', True ):
            return True
        try:
            args = getattr( record, 'args', None )
            if not args:
                return True
            request_line = args[ 0 ]
            if not isinstance( request_line, str ):
                # For request logs this is the "GET /path HTTP/1.1" string; other
                # records (e.g. a PosixPath arg) are left alone.
                return True
            match = re.match( r'^[A-Z]+ (/[^ ?]*)', request_line )
            if not match:
                return True
            if resolve( match.group( 1 )).url_name in self.URL_NAMES_TO_SUPPRESS:
                return False
        except Exception:
            pass
        return True
