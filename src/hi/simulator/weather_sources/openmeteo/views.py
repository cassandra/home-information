import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.simulator.profile.profile_manager import ProfileManager
from hi.simulator.weather_sources import payload_utils

from .apps import OpenMeteoWeatherSimConfig
from .forms import OpenMeteoSimStateForm
from .models import OpenMeteoSimState

logger = logging.getLogger(__name__)

TEMPLATE_DIR = 'weather_sources/openmeteo/payloads'
CURRENT_TEMPLATE = f'{TEMPLATE_DIR}/current.json'
HOURLY_TEMPLATE = f'{TEMPLATE_DIR}/forecast_hourly.json'
DAILY_TEMPLATE = f'{TEMPLATE_DIR}/forecast_daily.json'
ARCHIVE_TEMPLATE = f'{TEMPLATE_DIR}/archive.json'

HOURLY_FORECAST_HOURS = 7 * 24   # matches the main app's forecast_days=7
DAILY_FORECAST_DAYS = 14         # matches the main app's forecast_days=14
ELEVATION_M = 10.0


def get_current_state() -> OpenMeteoSimState:
    """The single state row for Open-Meteo's currently-selected profile,
    created on first access."""
    current_profile = ProfileManager().get_current( OpenMeteoWeatherSimConfig.name )
    state, _created = OpenMeteoSimState.objects.get_or_create( sim_profile = current_profile )
    return state


def _parse_float( value : str, default : float ) -> float:
    try:
        return float( value )
    except ( TypeError, ValueError ):
        return default


def _location_context( request ) -> dict:
    return {
        'latitude': _parse_float( request.GET.get( 'latitude' ), 0.0 ),
        'longitude': _parse_float( request.GET.get( 'longitude' ), 0.0 ),
        'elevation': ELEVATION_M,
    }


class OpenMeteoForecastApiView( View ):
    """The ``/v1/forecast`` endpoint serves three shapes off one path,
    so we dispatch on the same query params the main app sends:
    ``current_weather=true`` → current, else ``daily`` → daily, else
    ``hourly`` → hourly forecast."""

    def get( self, request, *args, **kwargs ):
        get = request.GET
        if 'current_weather' in get:
            return self._current( request )
        if 'daily' in get:
            return self._daily_forecast( request )
        if 'hourly' in get:
            return self._hourly_forecast( request )
        # No recognized selector — current is the safe default.
        return self._current( request )

    def _current( self, request ):
        state = get_current_state()
        day_start = payload_utils.now_hour().replace( hour = 0 )
        times = payload_utils.hourly_time_strings( 24, day_start )
        count = len( times )

        context = _location_context( request )
        context.update({
            # Minute-resolution "now" (not the top of the hour) so each poll's
            # source_datetime advances and the main app's freshness gate accepts
            # operator edits. The parser truncates this to the hour (HH:00) when
            # locating the current entry in the hourly arrays, so the lookup
            # still matches.
            'current_time': datetimeproxy.now().strftime( '%Y-%m-%dT%H:%M' ),
            'temperature': state.temperature_c,
            'windspeed': state.windspeed_kmh,
            'winddirection': state.winddirection_deg,
            'is_day': 1 if state.is_day else 0,
            'weathercode': state.weathercode,
            'hourly_time': times,
            'hourly_temperature': [ state.temperature_c ] * count,
            'hourly_humidity': [ state.relative_humidity_pct ] * count,
            'hourly_dewpoint': [ state.dewpoint_c ] * count,
            'hourly_precip': [ state.precipitation_mm ] * count,
            'hourly_pressure': [ state.pressure_msl_hpa ] * count,
        })
        return JsonResponse(
            payload_utils.render_json_payload( CURRENT_TEMPLATE, context, encode = True ) )

    def _hourly_forecast( self, request ):
        state = get_current_state()
        day_start = payload_utils.now_hour().replace( hour = 0 )
        times = payload_utils.hourly_time_strings( HOURLY_FORECAST_HOURS, day_start )
        count = len( times )

        # Light per-hour jitter around the operator's values so the forecast
        # isn't a flat line; deterministic per index (stable across polls).
        # Weather code is left as set.
        j = payload_utils.jitter
        clamp = payload_utils.clamp
        context = _location_context( request )
        context.update({
            'hourly_time': times,
            'hourly_temperature': [ round( j( state.temperature_c, 2.0, i, 1 ), 1 ) for i in range( count ) ],
            'hourly_humidity': [ int( clamp( j( state.relative_humidity_pct, 8, i, 3 ), 0, 100 ) ) for i in range( count ) ],
            'hourly_windspeed': [ round( max( 0.0, j( state.windspeed_kmh, 4.0, i, 4 ) ), 1 ) for i in range( count ) ],
            'hourly_winddirection': [ int( j( state.winddirection_deg, 25, i, 6 ) ) % 360 for i in range( count ) ],
            'hourly_precip': [ round( max( 0.0, j( state.precipitation_mm, 0.6, i, 7 ) ), 1 ) for i in range( count ) ],
            'hourly_weathercode': [ state.weathercode ] * count,
        })
        return JsonResponse(
            payload_utils.render_json_payload( HOURLY_TEMPLATE, context, encode = True ) )

    def _daily_forecast( self, request ):
        state = get_current_state()
        dates = payload_utils.daily_date_strings(
            DAILY_FORECAST_DAYS, payload_utils.now_hour().date() )
        return JsonResponse(
            payload_utils.render_json_payload(
                DAILY_TEMPLATE, _daily_context( request, state, dates ), encode = True ) )


class OpenMeteoArchiveApiView( View ):
    """The separate archive host's endpoint; same daily shape over the
    explicit ``start_date``..``end_date`` range the main app requests."""

    def get( self, request, *args, **kwargs ):
        state = get_current_state()
        start = payload_utils.parse_request_date( request.GET.get( 'start_date' ) )
        end = payload_utils.parse_request_date( request.GET.get( 'end_date' ) )
        dates = payload_utils.date_range_strings( start, end )
        return JsonResponse(
            payload_utils.render_json_payload(
                ARCHIVE_TEMPLATE, _daily_context( request, state, dates ), encode = True ) )


def _daily_context( request, state, dates ) -> dict:
    count = len( dates )
    j = payload_utils.jitter
    tmax, tmin, precip = [], [], []
    for i in range( count ):
        # Jitter high and low independently, then order them so the low never
        # exceeds the high. Deterministic per day; weather code left as set.
        hi = round( j( state.temperature_c, 2.0, i, 1 ), 1 )
        lo = round( j( state.temperature_min_c, 2.0, i, 2 ), 1 )
        lo, hi = sorted( ( lo, hi ) )
        tmax.append( hi )
        tmin.append( lo )
        precip.append( round( max( 0.0, j( state.precipitation_mm, 0.8, i, 7 ) ), 1 ) )
    context = _location_context( request )
    context.update({
        'daily_time': dates,
        'daily_weathercode': [ state.weathercode ] * count,
        'daily_tmax': tmax,
        'daily_tmin': tmin,
        'daily_precip': precip,
    })
    return context


class OpenMeteoSimStateSetView( View ):
    """Auto-submit target for the inline state form. Saves the changed
    field(s) and re-renders the form fragment, which antinode swaps in
    place."""

    PANE_TEMPLATE = 'weather_sources/openmeteo/panes/state_form.html'

    def post( self, request, *args, **kwargs ):
        state = get_current_state()
        form = OpenMeteoSimStateForm( request.POST, instance = state )
        if form.is_valid():
            form.save()
            form = OpenMeteoSimStateForm( instance = state )
        return render( request, self.PANE_TEMPLATE, { 'form': form })
