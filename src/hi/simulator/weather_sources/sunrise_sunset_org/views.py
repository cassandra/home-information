import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View

from hi.simulator.profile.profile_manager import ProfileManager
from hi.simulator.weather_sources import payload_utils

from .apps import SunriseSunsetWeatherSimConfig
from .constants import TWILIGHT_OFFSETS_MINUTES
from .forms import SunriseSunsetSimStateForm
from .models import SunriseSunsetSimState

logger = logging.getLogger(__name__)

PAYLOAD_TEMPLATE = 'weather_sources/sunrise_sunset_org/payloads/astronomical.json'


def get_current_state() -> SunriseSunsetSimState:
    """The single state row for Sunrise-Sunset's currently-selected
    profile, created on first access."""
    current_profile = ProfileManager().get_current( SunriseSunsetWeatherSimConfig.name )
    state, _created = SunriseSunsetSimState.objects.get_or_create(
        sim_profile = current_profile,
    )
    return state


class SunriseSunsetApiView( View ):
    """Sunrise-Sunset.org-shaped ``/json`` endpoint backed by the
    current profile's state row."""

    def get( self, request, *args, **kwargs ):
        state = get_current_state()
        on_date = payload_utils.parse_request_date( request.GET.get( 'date' ) )

        sunrise = payload_utils.local_hhmm_to_utc_iso(
            state.sunrise, state.utc_offset_hours, on_date )
        sunset = payload_utils.local_hhmm_to_utc_iso(
            state.sunset, state.utc_offset_hours, on_date )
        solar_noon = payload_utils.local_hhmm_to_utc_iso(
            state.solar_noon, state.utc_offset_hours, on_date )

        context = {
            'sunrise': sunrise,
            'sunset': sunset,
            'solar_noon': solar_noon,
            'civil_begin': payload_utils.shift_utc_iso(
                sunrise, -TWILIGHT_OFFSETS_MINUTES['civil'] ),
            'civil_end': payload_utils.shift_utc_iso(
                sunset, TWILIGHT_OFFSETS_MINUTES['civil'] ),
            'nautical_begin': payload_utils.shift_utc_iso(
                sunrise, -TWILIGHT_OFFSETS_MINUTES['nautical'] ),
            'nautical_end': payload_utils.shift_utc_iso(
                sunset, TWILIGHT_OFFSETS_MINUTES['nautical'] ),
            'astronomical_begin': payload_utils.shift_utc_iso(
                sunrise, -TWILIGHT_OFFSETS_MINUTES['astronomical'] ),
            'astronomical_end': payload_utils.shift_utc_iso(
                sunset, TWILIGHT_OFFSETS_MINUTES['astronomical'] ),
            'status': state.status_str,
        }
        return JsonResponse( payload_utils.render_json_payload( PAYLOAD_TEMPLATE, context ) )


class SunriseSunsetSimStateSetView( View ):
    """Auto-submit target for the inline state form. Saves the changed
    field(s) and re-renders the form fragment, which antinode swaps in
    place."""

    PANE_TEMPLATE = 'weather_sources/sunrise_sunset_org/panes/state_form.html'

    def post( self, request, *args, **kwargs ):
        state = get_current_state()
        form = SunriseSunsetSimStateForm( request.POST, instance = state )
        if form.is_valid():
            form.save()
            form = SunriseSunsetSimStateForm( instance = state )
        return render( request, self.PANE_TEMPLATE, { 'form': form })
