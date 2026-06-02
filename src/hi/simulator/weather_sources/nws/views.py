import logging
from datetime import timedelta
from typing import Any, Dict, List

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
import hi.apps.common.datetimeproxy as datetimeproxy
from hi.simulator.profile.profile_manager import ProfileManager
from hi.simulator.weather_sources import payload_utils

from .apps import NwsWeatherSimConfig
from .forms import NwsSimAlertForm, NwsSimConditionsForm
from .models import NwsSimAlert, NwsSimConditions

logger = logging.getLogger(__name__)

# Fixed identifiers for the simulated points→stations→observations
# chain. Their exact values don't matter to the main app (it follows
# whatever URLs our points/stations responses hand back); they only
# need to be self-consistent across the chain's routes.
SIM_OFFICE = 'SIM'
SIM_GRID = '1,1'
SIM_STATION = 'SIM'

PAYLOAD_DIR = 'weather_sources/nws/payloads'
POINTS_TEMPLATE = f'{PAYLOAD_DIR}/points.json'
STATIONS_TEMPLATE = f'{PAYLOAD_DIR}/stations.json'
OBSERVATIONS_TEMPLATE = f'{PAYLOAD_DIR}/observations.json'
FORECAST_TEMPLATE = f'{PAYLOAD_DIR}/forecast.json'

TWELVE_HOUR_PERIODS = 14
HOURLY_PERIODS = 24

_COMPASS_16 = [ 'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW' ]


def _deg_to_compass( degrees : int ) -> str:
    return _COMPASS_16[ int( ( degrees % 360 ) / 22.5 + 0.5 ) % 16 ]


def _iso( dt ) -> str:
    return dt.strftime( '%Y-%m-%dT%H:%M:%S+00:00' )


def get_current_conditions() -> NwsSimConditions:
    """Conditions/forecast state for NWS's currently-selected profile —
    the same SimProfile that scopes this profile's alerts."""
    current_profile = ProfileManager().get_current( NwsWeatherSimConfig.name )
    state, _created = NwsSimConditions.objects.get_or_create( sim_profile = current_profile )
    return state


def _build_periods( state : NwsSimConditions, count : int, hours_each : int,
                    named : bool ) -> List[ Dict[ str, Any ] ]:
    """Generate forecast periods reusing the operator's values, with the
    time axis anchored to now. 12h periods get day/night names and
    alternate ``isDaytime``; hourly periods derive it from the hour."""
    start = payload_utils.now_hour()
    first_is_day = state.is_daytime
    periods = []
    for index in range( count ):
        period_start = start + timedelta( hours = hours_each * index )
        period_end = period_start + timedelta( hours = hours_each )
        if named:
            is_daytime = ( ( index % 2 == 0 ) == first_is_day )
            weekday = period_start.strftime( '%A' )
            name = weekday if is_daytime else f'{weekday} Night'
        else:
            is_daytime = ( 6 <= period_start.hour < 18 )
            name = ''
        # Light per-period jitter around the operator's values so the
        # forecast isn't a flat line; deterministic per index (stable
        # across polls). Condition text is left as set.
        temperature = round( payload_utils.jitter( state.temperature_c, 2.0, index, 1 ), 1 )
        dewpoint = round( payload_utils.jitter( state.dewpoint_c, 1.5, index, 2 ), 1 )
        humidity = int( payload_utils.clamp(
            payload_utils.jitter( state.relative_humidity_pct, 8, index, 3 ), 0, 100 ) )
        wind_speed = round( max( 0.0, payload_utils.jitter( state.wind_speed_kmh, 4.0, index, 4 ) ), 1 )
        precip = int( payload_utils.clamp(
            payload_utils.jitter( state.precip_probability_pct, 15, index, 5 ), 0, 100 ) )
        wind_deg = int( payload_utils.jitter( state.wind_direction_deg, 25, index, 6 ) ) % 360
        periods.append({
            'number': index + 1,
            'name': name,
            'startTime': _iso( period_start ),
            'endTime': _iso( period_end ),
            'isDaytime': is_daytime,
            'temperature': { 'unitCode': 'wmoUnit:degC', 'value': temperature },
            'probabilityOfPrecipitation': { 'unitCode': 'wmoUnit:percent', 'value': precip },
            'dewpoint': { 'unitCode': 'wmoUnit:degC', 'value': dewpoint },
            'relativeHumidity': { 'unitCode': 'wmoUnit:percent', 'value': humidity },
            'windSpeed': { 'unitCode': 'wmoUnit:km_h-1', 'value': wind_speed },
            'windDirection': _deg_to_compass( wind_deg ),
            'shortForecast': state.text_description,
            'detailedForecast': state.text_description if named else '',
        })
    return periods


class NwsPointsView( View ):
    """Entry point of the chain. Hands the main app simulator-hosted URLs
    for stations and both forecasts so the rest of the chain stays here."""

    def get( self, request, coords, *args, **kwargs ):
        try:
            lat_str, lon_str = coords.split( ',' )
            latitude, longitude = float( lat_str ), float( lon_str )
        except ( ValueError, TypeError ):
            latitude = longitude = 0.0

        def abs_url( name ):
            return request.build_absolute_uri(
                reverse( name, kwargs = { 'office': SIM_OFFICE, 'grid': SIM_GRID } ) )

        context = {
            'grid_id': SIM_OFFICE,
            'forecast_office': request.build_absolute_uri( '/weather/nws/' ),
            'observation_stations_url': abs_url( 'simulator_weather_nws_stations' ),
            'forecast_url': abs_url( 'simulator_weather_nws_forecast' ),
            'forecast_hourly_url': abs_url( 'simulator_weather_nws_forecast_hourly' ),
            'geometry': { 'type': 'Point', 'coordinates': [ longitude, latitude ] },
        }
        return JsonResponse(
            payload_utils.render_json_payload( POINTS_TEMPLATE, context, encode = True ) )


class NwsStationsView( View ):
    """One observation station whose ``@id`` points back at our
    observations endpoint (the main app appends ``/observations/latest``)."""

    def get( self, request, office, grid, *args, **kwargs ):
        observations_path = reverse(
            'simulator_weather_nws_observations', kwargs = { 'station_id': SIM_STATION } )
        station_id_url = request.build_absolute_uri(
            observations_path[ : -len( '/observations/latest' ) ] )
        feature = {
            'geometry': { 'type': 'Point', 'coordinates': [ 0.0, 0.0 ] },
            'properties': {
                '@id': station_id_url,
                '@type': 'wx:ObservationStation',
                'stationIdentifier': SIM_STATION,
                'name': 'Simulator Station',
                'elevation': { 'unitCode': 'wmoUnit:m', 'value': 10 },
            },
        }
        return JsonResponse(
            payload_utils.render_json_payload(
                STATIONS_TEMPLATE, { 'features': [ feature ] }, encode = True ) )


class NwsObservationsView( View ):
    """Current conditions from the profile's conditions state."""

    def get( self, request, station_id, *args, **kwargs ):
        state = get_current_conditions()
        cloud_layers = [ {
            'base': { 'unitCode': 'wmoUnit:m', 'value': 3000 },
            'amount': state.cloud_amount,
        } ]
        context = {
            # Stamp the actual current time (not the top of the hour) so each
            # poll presents a strictly newer source_datetime; otherwise the
            # main app's same-source freshness gate keeps the prior value and
            # operator edits don't surface until the hour rolls over.
            'timestamp': _iso( datetimeproxy.now() ),
            'text_description': state.text_description,
            'temperature': state.temperature_c,
            'dewpoint': state.dewpoint_c,
            'wind_direction': state.wind_direction_deg,
            'wind_speed': state.wind_speed_kmh,
            # NWS reports barometric pressure in pascals.
            'barometric_pressure': int( round( state.barometric_pressure_hpa * 100 ) ),
            'relative_humidity': state.relative_humidity_pct,
            'cloud_layers': cloud_layers,
        }
        return JsonResponse(
            payload_utils.render_json_payload( OBSERVATIONS_TEMPLATE, context, encode = True ) )


class NwsForecastView( View ):
    """12-hour forecast (feeds the main app's daily slot)."""

    def get( self, request, office, grid, *args, **kwargs ):
        periods = _build_periods(
            get_current_conditions(), TWELVE_HOUR_PERIODS, hours_each = 12, named = True )
        context = { 'generated_at': _iso( datetimeproxy.now() ), 'periods': periods }
        return JsonResponse(
            payload_utils.render_json_payload( FORECAST_TEMPLATE, context, encode = True ) )


class NwsForecastHourlyView( View ):
    """Hourly forecast."""

    def get( self, request, office, grid, *args, **kwargs ):
        periods = _build_periods(
            get_current_conditions(), HOURLY_PERIODS, hours_each = 1, named = False )
        context = { 'generated_at': _iso( datetimeproxy.now() ), 'periods': periods }
        return JsonResponse(
            payload_utils.render_json_payload( FORECAST_TEMPLATE, context, encode = True ) )


class NwsSimConditionsSetView( View ):
    """Auto-submit target for the inline conditions form; saves and
    re-renders the fragment for in-place swap."""

    PANE_TEMPLATE = 'weather_sources/nws/panes/conditions_form.html'

    def post( self, request, *args, **kwargs ):
        state = get_current_conditions()
        form = NwsSimConditionsForm( request.POST, instance = state )
        if form.is_valid():
            form.save()
            form = NwsSimConditionsForm( instance = state )
        return render( request, self.PANE_TEMPLATE, { 'form': form } )


class NwsAlertsActiveView( View ):
    """NWS-shaped /alerts/active endpoint backed by NwsSimAlert rows."""

    def get( self, request, *args, **kwargs ):
        features : List[ Dict[str, Any] ] = []
        now = datetimeproxy.now()
        for alert in NwsSimAlert.objects.filter( is_active = True ):
            effective = now + timedelta( seconds = alert.effective_offset_secs )
            expires = now + timedelta( seconds = alert.expires_offset_secs )
            properties : Dict[ str, Any ] = {
                'event': alert.event_name,
                'headline': alert.headline,
                'description': alert.description,
                'instruction': alert.instruction,
                'areaDesc': alert.area_desc,
                'status': alert.status_str,
                'severity': alert.severity_str,
                'urgency': alert.urgency_str,
                'certainty': alert.certainty_str,
                'category': alert.category_str,
                'effective': effective.isoformat(),
                'expires': expires.isoformat(),
                'onset': effective.isoformat(),
                'ends': expires.isoformat(),
            }
            if alert.event_code:
                properties['eventCode'] = {
                    'NationalWeatherService': [ alert.event_code ],
                }
            # Feature id changes on each row save (toggle / edit) so
            # the main app treats each issuance as distinct, matching
            # real NWS where every Update / Cancel publishes a new
            # identifier. Repeat polls of an unchanged row share the
            # same id.
            issuance = int( alert.updated_datetime.timestamp() )
            features.append({
                'id': f'sim-nws-alert-{alert.id}-{issuance}',
                'properties': properties,
            })
        return JsonResponse( { 'features': features } )


class NwsSimAlertAddView( View ):

    MODAL_TEMPLATE = 'weather_sources/nws/modals/alert_form.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'form': NwsSimAlertForm(),
            'is_add': True,
        }
        return render( request, self.MODAL_TEMPLATE, context )

    def post( self, request, *args, **kwargs ):
        form = NwsSimAlertForm( request.POST )
        if not form.is_valid():
            return render( request, self.MODAL_TEMPLATE, {
                'form': form,
                'is_add': True,
            })
        # The form has no sim_profile field; new alerts belong to NWS's
        # currently-selected profile (the same one that scopes the alert
        # list and this profile's conditions).
        alert = form.save( commit = False )
        alert.sim_profile = ProfileManager().get_current( NwsWeatherSimConfig.name )
        alert.save()
        return antinode.refresh_response()


class NwsSimAlertEditView( View ):

    MODAL_TEMPLATE = 'weather_sources/nws/modals/alert_form.html'

    def get( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        context = {
            'form': NwsSimAlertForm( instance = alert ),
            'alert': alert,
            'is_add': False,
        }
        return render( request, self.MODAL_TEMPLATE, context )

    def post( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        form = NwsSimAlertForm( request.POST, instance = alert )
        if not form.is_valid():
            return render( request, self.MODAL_TEMPLATE, {
                'form': form,
                'alert': alert,
                'is_add': False,
            })
        form.save()
        return antinode.refresh_response()


class NwsSimAlertDeleteView( View ):

    MODAL_TEMPLATE = 'weather_sources/nws/modals/alert_delete.html'

    def get( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        return render( request, self.MODAL_TEMPLATE, { 'alert': alert })

    def post( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        alert.delete()
        return antinode.refresh_response()


class NwsSimAlertToggleView( View ):

    def post( self, request, alert_id, *args, **kwargs ):
        alert = get_object_or_404( NwsSimAlert, id = alert_id )
        alert.is_active = not alert.is_active
        # Save the whole row (not just is_active) so the auto_now
        # ``updated_datetime`` is bumped — that timestamp drives the
        # NWS-shaped feature id, and the main app's alarm dedup needs
        # to see a fresh id when a previously-inactive alert is
        # re-activated.
        alert.save()
        return antinode.refresh_response()
