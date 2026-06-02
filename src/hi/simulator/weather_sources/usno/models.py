from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from hi.simulator.profile.models import SimProfile

from . import constants


HHMM_VALIDATOR = RegexValidator(
    regex = r'^\d{1,2}:\d{2}$',
    message = 'Enter a time as HH:MM (24-hour).',
)


class UsnoSimState( models.Model ):
    """Single operator-controlled USNO ``oneday`` response per profile.

    USNO returns times already in local wall-clock (the main app sends
    a tz offset on the request), so the HH:MM values here are emitted
    directly — no UTC conversion needed.
    """

    class Meta:
        verbose_name = 'USNO Sim State'
        verbose_name_plural = 'USNO Sim States'

    sim_profile = models.OneToOneField(
        SimProfile,
        related_name = 'usno_sim_state',
        on_delete = models.CASCADE,
    )
    sunrise = models.CharField(
        max_length = 5, default = '05:44', validators = [ HHMM_VALIDATOR ],
        help_text = 'Local sunrise time (HH:MM).',
    )
    sunset = models.CharField(
        max_length = 5, default = '20:28', validators = [ HHMM_VALIDATOR ],
        help_text = 'Local sunset time (HH:MM).',
    )
    solar_noon = models.CharField(
        max_length = 5, default = '13:06', validators = [ HHMM_VALIDATOR ],
        help_text = 'Local solar-noon (upper-transit) time (HH:MM).',
    )
    moonrise = models.CharField(
        max_length = 5, default = '22:55', validators = [ HHMM_VALIDATOR ],
        help_text = 'Local moonrise time (HH:MM).',
    )
    moonset = models.CharField(
        max_length = 5, default = '07:06', validators = [ HHMM_VALIDATOR ],
        help_text = 'Local moonset time (HH:MM).',
    )
    fracillum_percent = models.IntegerField(
        default = 95,
        validators = [ MinValueValidator( 0 ), MaxValueValidator( 100 ) ],
        help_text = 'Moon illuminated fraction (0-100%).',
    )
    curphase_str = models.CharField(
        max_length = 24,
        choices = constants.MOON_PHASE_CHOICES,
        default = 'Waning Gibbous',
        help_text = 'Current moon phase; drives the waxing/waning flag.',
    )
    tz_offset_hours = models.IntegerField(
        default = 0,
        help_text = 'Cosmetic tz value echoed in the payload; the main app ignores it.',
    )
    updated_datetime = models.DateTimeField( auto_now = True )
