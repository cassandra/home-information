import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View

from hi.simulator.profile.profile_manager import ProfileManager
from hi.simulator.weather_sources import payload_utils

from .apps import UsnoWeatherSimConfig
from .forms import UsnoSimStateForm
from .models import UsnoSimState

logger = logging.getLogger(__name__)

PAYLOAD_TEMPLATE = 'weather_sources/usno/payloads/oneday.json'


def get_current_state() -> UsnoSimState:
    """The single state row for USNO's currently-selected profile,
    created on first access."""
    current_profile = ProfileManager().get_current( UsnoWeatherSimConfig.name )
    state, _created = UsnoSimState.objects.get_or_create( sim_profile = current_profile )
    return state


def _parse_coords( coords_str : str ):
    """``coords`` is ``lat,lon``; echo it back into the geometry. Defaults
    keep the payload valid if the param is missing/malformed."""
    if coords_str:
        try:
            lat_str, lon_str = coords_str.split( ',' )
            return float( lat_str ), float( lon_str )
        except ( ValueError, TypeError ):
            pass
    return 0.0, 0.0


class UsnoApiView( View ):
    """USNO ``oneday``-shaped endpoint backed by the current profile's
    state row."""

    def get( self, request, *args, **kwargs ):
        state = get_current_state()
        on_date = payload_utils.parse_request_date( request.GET.get( 'date' ) )
        latitude, longitude = _parse_coords( request.GET.get( 'coords' ) )

        context = {
            'latitude': latitude,
            'longitude': longitude,
            'sunrise': state.sunrise,
            'sunset': state.sunset,
            'solar_noon': state.solar_noon,
            'moonrise': state.moonrise,
            'moonset': state.moonset,
            'fracillum': state.fracillum_percent,
            'curphase': state.curphase_str,
            'tz': float( state.tz_offset_hours ),
            'day': on_date.day,
            'month': on_date.month,
            'year': on_date.year,
            'day_of_week': on_date.strftime( '%A' ),
        }
        return JsonResponse( payload_utils.render_json_payload( PAYLOAD_TEMPLATE, context ) )


class UsnoSimStateSetView( View ):
    """Auto-submit target for the inline state form. Saves the changed
    field(s) and re-renders the form fragment, which antinode swaps in
    place."""

    PANE_TEMPLATE = 'weather_sources/usno/panes/state_form.html'

    def post( self, request, *args, **kwargs ):
        state = get_current_state()
        form = UsnoSimStateForm( request.POST, instance = state )
        if form.is_valid():
            form.save()
            form = UsnoSimStateForm( instance = state )
        return render( request, self.PANE_TEMPLATE, { 'form': form })
