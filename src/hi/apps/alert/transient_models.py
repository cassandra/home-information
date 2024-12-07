from dataclasses import dataclass
from datetime import datetime

from .enums import AlarmLevel, SecurityPosture


@dataclass
class Alarm:
    title                : str
    details              : str
    security_posture     : SecurityPosture
    alarm_level          : AlarmLevel
    alarm_lifetime_secs  : int
    timestamp            : datetime

    @property
    def audio_signal_name(self):

        # TODO: Currently based only on the alarm level, but eventually
        # allow alarm-specific sounds. e.g., tornado siren sound when
        # there's a weather alert.
        
        return str(self.alarm_level.audio_signal)
    
