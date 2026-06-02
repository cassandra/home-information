from django.core.validators import RegexValidator
from django.db import models

from hi.simulator.profile.models import SimProfile

from . import constants


HHMM_VALIDATOR = RegexValidator(
    regex = r'^\d{1,2}:\d{2}$',
    message = 'Enter a time as HH:MM (24-hour).',
)


class SunriseSunsetSimState( models.Model ):
    """Single operator-controlled astronomical response per profile.

    The API endpoint renders one ``results`` payload from this row on
    each request, anchored to whatever date the main app asks for, so
    the same sun times appear across the multi-day poll.
    """

    class Meta:
        verbose_name = 'Sunrise-Sunset Sim State'
        verbose_name_plural = 'Sunrise-Sunset Sim States'

    sim_profile = models.OneToOneField(
        SimProfile,
        related_name = 'sunrise_sunset_sim_state',
        on_delete = models.CASCADE,
    )
    sunrise = models.CharField(
        max_length = 5,
        default = '06:00',
        validators = [ HHMM_VALIDATOR ],
        help_text = 'Local sunrise time (HH:MM).',
    )
    sunset = models.CharField(
        max_length = 5,
        default = '20:00',
        validators = [ HHMM_VALIDATOR ],
        help_text = 'Local sunset time (HH:MM).',
    )
    solar_noon = models.CharField(
        max_length = 5,
        default = '13:00',
        validators = [ HHMM_VALIDATOR ],
        help_text = 'Local solar-noon time (HH:MM).',
    )
    utc_offset_hours = models.IntegerField(
        default = 0,
        help_text = (
            'Set to your main-app console UTC offset (e.g. -5 for EST) so the '
            'times above display as entered. The API returns UTC instants that '
            'the main app re-localizes; 0 emits the times as UTC.'
        ),
    )
    status_str = models.CharField(
        max_length = 24,
        choices = constants.STATUS_CHOICES,
        default = 'OK',
        help_text = 'Top-level API status. Anything but OK exercises the main-app error path.',
    )
    updated_datetime = models.DateTimeField( auto_now = True )
