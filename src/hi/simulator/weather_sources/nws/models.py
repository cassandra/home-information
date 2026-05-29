from django.db import models

from hi.simulator.profile.models import SimProfile

from . import constants


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
