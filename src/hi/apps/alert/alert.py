from collections import deque
from datetime import datetime, timedelta
from typing import List
import uuid

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.notify.transient_models import NotificationItem

from .alarm import Alarm
from .enums import AlarmLevel, AlarmSource


class Alert:

    MAX_ALARM_LIST_SIZE = 50

    def __init__( self, first_alarm : Alarm ):
        
        self._id = uuid.uuid4().hex
        self._start_datetime = first_alarm.timestamp
        self._end_datetime = self._start_datetime + timedelta( seconds = first_alarm.alarm_lifetime_secs )
        self._queue_insertion_datetime = None

        # Prevent unbounded growth and kept in reverse order of arrival, so
        # most recent alarm is on the left side of list (popleft)
        #
        self._first_alarm = first_alarm
        self._latest_alarms = deque( maxlen = self.MAX_ALARM_LIST_SIZE )
        self._latest_alarms.appendleft( first_alarm )
        self._is_acknowledged = False
        return

    def __str__(self):
        return f'{self.alarm_source} : {self.alarm_level} : {self.alarm_type} [{self.start_datetime}, {self._end_datetime}]'
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def start_datetime(self) -> datetime:
        return self._start_datetime

    @property
    def end_datetime(self) -> datetime:
        return self._end_datetime
    
    @property
    def queue_insertion_datetime(self) -> datetime:
        return self._queue_insertion_datetime
    
    @queue_insertion_datetime.setter
    def queue_insertion_datetime(self, value: datetime):
        self._queue_insertion_datetime = value
    
    @property
    def audio_signal(self) -> AudioSignal:
        return self._first_alarm.audio_signal
    
    @property
    def alarm_source(self) -> AlarmSource:
        return self._first_alarm.alarm_source

    @property
    def alarm_type(self) -> AlarmSource:
        return self._first_alarm.alarm_type

    @property
    def alarm_level(self) -> AlarmLevel:
        return self._first_alarm.alarm_level

    @property
    def alarm_count(self) -> int:
        return len( self._latest_alarms )

    @property
    def alarm_list(self) -> List[ Alarm ]:
        return list( self._latest_alarms )

    @property
    def title(self) -> str:
        title_text = f'{self.alarm_level.label}: {self._first_alarm.title}'
        if self.alarm_count > 1:
            title_text += f' ({self.alarm_count})'
        return title_text
    
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

    @property
    def alert_priority(self) -> int:
        # TODO: Currently just using AlarmLevel priority, but can refine
        # this to better order alerts with the same alarm priority
        return self._first_alarm.alarm_level.priority

    @property
    def signature(self):
        # N.B. All alarms in an Alert should have the same signature.
        return self.first_alarm.signature

    @property
    def has_single_alarm(self):
        return bool( len(self._latest_alarms) == 1 )
    
    def is_matching_alarm( self, alarm : Alarm ) -> bool:
        return bool( self._first_alarm.signature == alarm.signature )

    def add_alarm( self, alarm : Alarm ):
        assert alarm.signature == self.first_alarm.signature
        self._end_datetime = datetimeproxy.now() + timedelta( seconds = alarm.alarm_lifetime_secs )
        self._latest_alarms.appendleft( alarm )
        return
        
    def get_latest_alarm(self) -> Alarm:
        if len(self._latest_alarms) > 0:
            return self._latest_alarms[0]
        return None
    
    def get_first_visual_content(self):
        """
        Find the first image/video content from any alarm in the alert.
        Returns dict with image info and sensor response or None if no visual content found.
        """
        for alarm in self.alarm_list:
            for sensor_response in alarm.sensor_response_list:
                # Check for video stream capability first (preferred over static source_image_url)
                if sensor_response.has_video_stream:
                    return {
                        'source_image_url': sensor_response.source_image_url,
                        'alarm': alarm,
                        'source_details': sensor_response,  # Keep for backward compatibility
                        'sensor_response': sensor_response,
                        'is_from_latest': alarm == self.alarm_list[0] if self.alarm_list else False,
                    }
                # Fallback to static source_image_url if no video stream
                elif sensor_response.source_image_url:
                    return {
                        'source_image_url': sensor_response.source_image_url,
                        'alarm': alarm,
                        'source_details': sensor_response,  # Keep for backward compatibility
                        'sensor_response': sensor_response,
                        'is_from_latest': alarm == self.alarm_list[0] if self.alarm_list else False,
                    }
        return None
    
    def get_all_video_sources(self):
        """
        Get all sensor responses with video streams from all alarms in the alert.
        Returns list of dicts with sensor_response, alarm, and index info.
        """
        video_sources = []
        for alarm in self.alarm_list:
            for sensor_response in alarm.sensor_response_list:
                if sensor_response.has_video_stream:
                    video_sources.append({
                        'sensor_response': sensor_response,
                        'alarm': alarm,
                        'index': len(video_sources) + 1,  # 1-based for UI
                    })
        return video_sources
    
    def get_video_source_count(self):
        """Get total count of video sources across all alarms in the alert."""
        return len(self.get_all_video_sources())
    
    def to_notification_item(self):
        return NotificationItem(
            signature = self.signature,
            title = self.title,
            source_obj = self,
        )
    
    def get_view_url(self) -> str:
        """
        Get a view URL associated with this alert if one can be determined.
        
        This method extracts a relevant view URL from the alert's alarms,
        typically for auto-view switching to show relevant camera feeds or
        other contextual views when alerts occur.
        
        Returns:
            A Django view URL string, or None if no view can be determined.
        """
        # For now, we'll use the first alarm's view URL
        # In the future, we might have more sophisticated logic for
        # choosing between multiple alarms' views
        if self._first_alarm:
            return self._first_alarm.get_view_url()
        return None
    
