from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from hi.simulator.profile.models import SimProfile

from . import constants


class OpenMeteoSimState( models.Model ):
    """Single operator-controlled Open-Meteo response set per profile.

    One row drives all three ``forecast`` variants (current / hourly /
    daily) plus the archive endpoint. The simulator fills each time
    series with the value held here and generates the time axis anchored
    to "now", so the operator controls the values and never the
    timestamps.
    """

    class Meta:
        verbose_name = 'Open-Meteo Sim State'
        verbose_name_plural = 'Open-Meteo Sim States'

    sim_profile = models.OneToOneField(
        SimProfile,
        related_name = 'openmeteo_sim_state',
        on_delete = models.CASCADE,
    )
    temperature_c = models.FloatField(
        default = 22.0,
        help_text = 'Temperature °C (current, hourly, and daily high).',
    )
    temperature_min_c = models.FloatField(
        default = 14.0,
        help_text = 'Daily low temperature °C (daily forecast and archive).',
    )
    relative_humidity_pct = models.IntegerField(
        default = 55,
        validators = [ MinValueValidator( 0 ), MaxValueValidator( 100 ) ],
        help_text = 'Relative humidity (0-100%).',
    )
    dewpoint_c = models.FloatField(
        default = 12.0,
        help_text = 'Dew point °C (current conditions).',
    )
    precipitation_mm = models.FloatField(
        default = 0.0,
        help_text = 'Precipitation in mm (per hour / daily sum).',
    )
    pressure_msl_hpa = models.FloatField(
        default = 1015.0,
        help_text = 'Mean sea-level pressure in hPa (current conditions).',
    )
    windspeed_kmh = models.FloatField(
        default = 12.0,
        help_text = 'Wind speed in km/h.',
    )
    winddirection_deg = models.IntegerField(
        default = 200,
        validators = [ MinValueValidator( 0 ), MaxValueValidator( 360 ) ],
        help_text = 'Wind direction in degrees (0-360).',
    )
    weathercode = models.IntegerField(
        choices = constants.WEATHER_CODE_CHOICES,
        default = 1,
        help_text = 'WMO weather code; the main app maps it to a description.',
    )
    is_day = models.BooleanField(
        default = True,
        help_text = 'Daytime flag for current conditions.',
    )
    updated_datetime = models.DateTimeField( auto_now = True )
