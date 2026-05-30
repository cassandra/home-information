from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.transient_models import SensorResponse

from .enums import AlarmLevel, AlarmSource


@dataclass(frozen=True)
class AlarmSignature:
    """Domain identity for a class of alarms that dedupe together.

    Two alarms with the same signature surface as one Alert in the
    queue. Producers construct an ``AlarmSignature`` to target alerts
    for clearing on state recovery without having to know the alert
    module's internal storage representation.
    """

    alarm_source : AlarmSource
    alarm_type   : str
    alarm_level  : AlarmLevel

    def __str__(self):
        return f'{self.alarm_source.name}.{self.alarm_type}.{self.alarm_level.name}'


@dataclass
class Alarm:

    alarm_source         : AlarmSource
    alarm_type           : str
    alarm_level          : AlarmLevel
    title                : str
    sensor_response_list : List[ SensorResponse ]
    security_level       : SecurityLevel
    alarm_lifetime_secs  : int
    timestamp            : datetime

    # Optional caller-supplied identifier for the *specific incident*
    # this alarm represents. When set, Alert.upsert_alarm uses it to
    # recognize repeated submissions of the same incident (NWS poll
    # returning the same alert each cycle, motion sensor re-firing on
    # the same trigger, etc.) and refresh expiry without incrementing
    # the alarm count. None preserves legacy "every submission
    # counts" behavior.
    source_alarm_id      : Optional[str] = None

    def __post_init__(self):
        # ``Alert.end_datetime`` is derived from this field; zero or
        # negative values produce an already-expired alert (a
        # historical failure mode of the previous "0 = until
        # acknowledged" convention). Raise rather than assert so the
        # check survives ``python -O``.
        if self.alarm_lifetime_secs <= 0:
            raise ValueError(
                f'alarm_lifetime_secs must be positive, got '
                f'{self.alarm_lifetime_secs}'
            )
        return

    @property
    def audio_signal(self):
        # Enhanced to support alarm-specific sounds based on level, source, and type.
        # Weather alerts get different sounds from event alerts, and tornado alerts
        # get special treatment regardless of level.
        return AudioSignal.from_alarm_attributes( self.alarm_level, self.alarm_source, self.alarm_type )

    @property
    def signature(self) -> AlarmSignature:
        return AlarmSignature(
            alarm_source = self.alarm_source,
            alarm_type   = self.alarm_type,
            alarm_level  = self.alarm_level,
        )
    
    def get_view_url(self) -> str:
        """
        Extract a view URL from this alarm's source details.
        
        Delegates to ViewUrlUtils for the actual URL generation logic.
        
        Returns:
            A Django view URL string, or None if no view can be determined.
        """
        from hi.apps.console.view_url_utils import ViewUrlUtils
        return ViewUrlUtils.get_view_url_for_alarm(self)
