from dataclasses import dataclass
from datetime import datetime

from .enums import AlarmLevel, SecurityPosture


@dataclass
class Alarm:
    title             : str
    details           : str
    security_posture  : SecurityPosture
    alarm_level       : AlarmLevel  # zzz make this AlarmLevel and move here???
    lifetime_secs     : int
    timestamp         : datetime
