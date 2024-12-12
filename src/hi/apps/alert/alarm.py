from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from hi.apps.console.audio_signal import AudioSignal
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

        # TODO: Currently based only on the alarm level, but eventually
        # allow alarm-specific sounds. e.g., tornado siren sound when
        # there's a weather alert.
        
        return AudioSignal.from_alarm_level( self.alarm_level )

    @property
    def signature(self):
        return f'{self.alarm_source}.{self.alarm_type}.{self.alarm_level}'
