from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from hi.simulator.profile.models import SimProfile

from . import constants


class NwsSimConditions( models.Model ):
    """Operator-controlled NWS current conditions + forecast, one row per
    profile (the same SimProfile that scopes this profile's alerts, so a
    single NWS profile defines everything).

    Drives the observations/latest endpoint plus both forecast endpoints;
    the chain's points/stations responses are fixed plumbing. Each value
    is reused across the generated forecast periods, with time axes
    anchored to "now".
    """

    class Meta:
        verbose_name = 'NWS Sim Conditions'
        verbose_name_plural = 'NWS Sim Conditions'

    sim_profile = models.OneToOneField(
        SimProfile,
        related_name = 'nws_sim_conditions',
        on_delete = models.CASCADE,
    )
    text_description = models.CharField(
        max_length = 64,
        default = 'Partly Cloudy',
        help_text = 'Short text shown for current conditions and forecast periods.',
    )
    temperature_c = models.FloatField(
        default = 22.0, help_text = 'Temperature °C (conditions and forecast).',
    )
    dewpoint_c = models.FloatField(
        default = 12.0, help_text = 'Dew point °C.',
    )
    relative_humidity_pct = models.IntegerField(
        default = 55, validators = [ MinValueValidator( 0 ), MaxValueValidator( 100 ) ],
        help_text = 'Relative humidity (0-100%).',
    )
    wind_speed_kmh = models.FloatField(
        default = 12.0, help_text = 'Wind speed in km/h.',
    )
    wind_direction_deg = models.IntegerField(
        default = 200, validators = [ MinValueValidator( 0 ), MaxValueValidator( 360 ) ],
        help_text = 'Wind direction degrees (forecast uses the nearest compass point).',
    )
    barometric_pressure_hpa = models.FloatField(
        default = 1015.0, help_text = 'Barometric pressure in hPa (emitted as Pa).',
    )
    cloud_amount = models.CharField(
        max_length = 3,
        choices = constants.CLOUD_AMOUNT_CHOICES,
        default = 'SCT',
        help_text = 'Sky cover for current conditions.',
    )
    precip_probability_pct = models.IntegerField(
        default = 10, validators = [ MinValueValidator( 0 ), MaxValueValidator( 100 ) ],
        help_text = 'Forecast probability of precipitation (0-100%).',
    )
    is_daytime = models.BooleanField(
        default = True, help_text = 'Daytime flag for the first forecast period.',
    )
    updated_datetime = models.DateTimeField( auto_now = True )


class NwsSimAlert( models.Model ):
    """One operator-managed simulated NWS alert.

    The alerts/active API endpoint converts active rows to NWS-shaped
    GeoJSON on each request, so ``effective`` and ``expires`` stay
    fresh (relative offsets, not stored timestamps).
    """

    class Meta:
        verbose_name = 'NWS Sim Alert'
        verbose_name_plural = 'NWS Sim Alerts'
        ordering = [ '-created_datetime' ]

    sim_profile = models.ForeignKey(
        SimProfile,
        related_name = 'nws_sim_alerts',
        on_delete = models.CASCADE,
    )
    is_active = models.BooleanField(
        default = True,
        help_text = 'Include this alert in the simulated active-alerts feed.',
    )
    event_code = models.CharField(
        max_length = 8,
        choices = constants.EVENT_CODE_CHOICES,
        blank = True,
        default = '',
        help_text = 'NWS three-letter event code (drives main-app event type mapping).',
    )
    event_name = models.CharField(
        max_length = 128,
        default = 'Test Alert',
        help_text = 'Human-readable event name (e.g. "Air Quality Alert").',
    )
    severity_str = models.CharField(
        max_length = 16,
        choices = constants.SEVERITY_CHOICES,
        default = 'Minor',
    )
    certainty_str = models.CharField(
        max_length = 16,
        choices = constants.CERTAINTY_CHOICES,
        default = 'Possible',
    )
    urgency_str = models.CharField(
        max_length = 16,
        choices = constants.URGENCY_CHOICES,
        default = 'Expected',
    )
    status_str = models.CharField(
        max_length = 16,
        choices = constants.STATUS_CHOICES,
        default = 'Actual',
    )
    category_str = models.CharField(
        max_length = 16,
        choices = constants.CATEGORY_CHOICES,
        default = 'met',
    )
    headline = models.CharField( max_length = 512, default = '' )
    description = models.TextField( default = '' )
    instruction = models.TextField( blank = True, default = '' )
    area_desc = models.CharField( max_length = 255, default = 'Simulator Test Area' )
    effective_offset_secs = models.IntegerField(
        default = -900,
        help_text = (
            'When the alert becomes effective, relative to "now" in seconds. '
            'Negative = in the past, positive = in the future.'
        ),
    )
    expires_offset_secs = models.IntegerField(
        default = 900,
        help_text = 'When the alert expires, relative to "now" in seconds.',
    )
    created_datetime = models.DateTimeField( auto_now_add = True )
    # Bumped on every save so the NWS-shaped feature id changes each
    # time the row is modified, matching real NWS behavior where any
    # Update / Cancel issuance carries a new identifier.
    updated_datetime = models.DateTimeField( auto_now = True )
