from collections import deque
from datetime import datetime, timedelta
from typing import List
import uuid

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.config.enums import AudioSignal

from .alarm import Alarm
from .enums import AlarmLevel, AlarmSource


class Alert:

    MAX_ALARM_LIST_SIZE = 50

    def __init__( self, first_alarm : Alarm ):
        
        self._id = uuid.uuid4().hex
        self._start_datetime = first_alarm.timestamp
        self._end_datetime = self._start_datetime + timedelta( seconds = first_alarm.alarm_lifetime_secs )

        # Prevent unbounded growth and kept in reverse order of arrival, so
        # most recent alarm is on the left side of list (popleft)
        #
        self._first_alarm = first_alarm
        self._latest_alarms = deque( maxlen = self.MAX_ALARM_LIST_SIZE )
        self._latest_alarms.appendleft( first_alarm )
        self._is_acknowledged = False
        return

    @property
    def id(self) -> str:
        return self._id
    
    @property
    def alarm_list(self) -> List[ Alarm ]:
        return list( self._latest_alarms )

    @property
    def start_datetime(self) -> datetime:
        return self._start_datetime

    @property
    def end_datetime(self) -> datetime:
        return self._end_datetime
    
    @property
    def audio_signal(self) -> AudioSignal:
        return self._first_alarm.audio_signal
    
    @property
    def alarm_level(self) -> AlarmLevel:
        return self._first_alarm.alarm_level

    @property
    def alarm_source(self) -> AlarmSource:
        return self._first_alarm.alarm_source

    @property
    def alarm_type(self) -> AlarmSource:
        return self._first_alarm.alarm_type

    @property
    def alarm_count(self) -> int:
        return len( self._latest_alarms )

    @property
    def title(self) -> str:
        return self._first_alarm.title

    @property
    def first_alarm(self) -> Alarm:
        return self._first_alarm

    @property
    def is_acknowledged(self) -> bool:
        return self._is_acknowledged

    @is_acknowledged.setter
    def is_acknowledged( self, value : bool ):
        self._is_acknowledged = value
        return
     
    def is_matching_alarm( self, alarm : Alarm ) -> bool:
        return self._first_alarm.sSignature == alarm.signature

    @property
    def alert_priority(self) -> int:
        # TODO: Currently just using AlarmLevel priority, but can refine
        # this to better order alerts with the same alarm priority
        return self._first_alarm.alarm_level.priority

    def add_alarm( self, alarm : Alarm ):
        self._end_datetime = datetimeproxy.now() + timedelta( seconds = alarm.alarm_lifetime_secs )
        self._latest_alarms.appendleft( alarm )
        return
        
    def get_latest_alarm(self) -> Alarm:
        if len(self._latest_alarms) > 0:
            return self._latest_alarms[0]
        return None
    
