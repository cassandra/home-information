from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.security.enums import SecurityLevel

from .enums import AlarmLevel, AlarmSource


@dataclass
class AlarmSourceDetails:

    detail_attrs         : Dict[ str, str ]
    image_url            : str               = None

    
@dataclass
class Alarm:
    alarm_source         : AlarmSource
    alarm_type           : str
    alarm_level          : AlarmLevel
    title                : str
    source_details_list  : List[ AlarmSourceDetails ]
    security_level       : SecurityLevel
    alarm_lifetime_secs  : int
    timestamp            : datetime

    @property
    def audio_signal(self):
        # Enhanced to support alarm-specific sounds based on level, source, and type.
        # Weather alerts get different sounds from event alerts, and tornado alerts
        # get special treatment regardless of level.
        return AudioSignal.from_alarm_attributes( self.alarm_level, self.alarm_source, self.alarm_type )

    @property
    def signature(self):
        return f'{self.alarm_source}.{self.alarm_type}.{self.alarm_level}'
