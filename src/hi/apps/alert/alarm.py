from dataclasses import dataclass
from datetime import datetime

from .enums import AlarmLevel, AlarmSource, SecurityPosture


@dataclass
class Alarm:
    alarm_source         : AlarmSource
    alarm_type           : str
    alarm_level          : AlarmLevel
    title                : str
    details              : str
    security_posture     : SecurityPosture
    alarm_lifetime_secs  : int
    timestamp            : datetime

    @property
    def audio_signal(self):

        # TODO: Currently based only on the alarm level, but eventually
        # allow alarm-specific sounds. e.g., tornado siren sound when
        # there's a weather alert.
        
        return self.alarm_level.audio_signal

    @property
    def signature(self):
        return f'{self.alarm_source}.{self.alarm_type}.{self.alarm_level}'
