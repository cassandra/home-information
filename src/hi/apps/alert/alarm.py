from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.transient_models import SensorResponse

from .enums import AlarmLevel, AlarmSource


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
        # The lifetime field drives ``Alert.end_datetime``; zero or
        # negative values produce an already-expired alert (a
        # historical bug with the previous "0 = until acknowledged"
        # convention) and values above MAX exceed the practical
        # "never expires" intent. Enforce the supported range here so
        # mistakes show up at construction, not silently as
        # vanished alarms.
        assert self.alarm_lifetime_secs > 0
        return

    @property
    def audio_signal(self):
        # Enhanced to support alarm-specific sounds based on level, source, and type.
        # Weather alerts get different sounds from event alerts, and tornado alerts
        # get special treatment regardless of level.
        return AudioSignal.from_alarm_attributes( self.alarm_level, self.alarm_source, self.alarm_type )

    @property
    def signature(self):
        return f'{self.alarm_source}.{self.alarm_type}.{self.alarm_level}'
    
    def get_view_url(self) -> str:
        """
        Extract a view URL from this alarm's source details.
        
        Delegates to ViewUrlUtils for the actual URL generation logic.
        
        Returns:
            A Django view URL string, or None if no view can be determined.
        """
        from hi.apps.console.view_url_utils import ViewUrlUtils
        return ViewUrlUtils.get_view_url_for_alarm(self)
