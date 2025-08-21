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
    def start_datetime(self) -> datetime:
        return self._start_datetime

    @property
    def end_datetime(self) -> datetime:
        return self._end_datetime
    
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
        Returns dict with image info or None if no visual content found.
        """
        for alarm in self.alarm_list:
            for source_details in alarm.source_details_list:
                if source_details.image_url:
                    return {
                        'image_url': source_details.image_url,
                        'alarm': alarm,
                        'is_from_latest': alarm == self.alarm_list[0] if self.alarm_list else False,
                    }
        return None
    
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
        
        IMPORTANT: HiGridView Constraint
        ===============================
        The returned URL MUST point to a Django view that subclasses HiGridView.
        This constraint exists because:
        
        1. Auto-view switching uses asynchronous content loading via antinode.js
        2. The antinode.js system expects HiGridView response format and structure  
        3. HiGridView provides proper HTML templates and response handling
        4. Other view types will not work with the auto-view switching mechanism
        
        Currently implemented URLs:
        - SensorVideoStreamView: /console/sensor/{sensor_id}/video_stream/
        
        Future URLs must also point to HiGridView subclasses to be compatible.
        
        Returns:
            A Django view URL string, or None if no view can be determined.
        """
        # For now, we'll use the first alarm's view URL
        # In the future, we might have more sophisticated logic for
        # choosing between multiple alarms' views
        if self._first_alarm:
            return self._extract_view_url_from_alarm(self._first_alarm)
        return None
    
    def _extract_view_url_from_alarm(self, alarm: Alarm) -> str:
        """
        Extract a view URL from an alarm's source details.
        
        This method knows how to navigate the alarm's data structure
        to find relevant view information based on the alarm source type.
        """
        if alarm.alarm_source == AlarmSource.EVENT:
            return self._extract_event_view_url(alarm)
        # Future: Add handlers for other alarm sources
        # elif alarm.alarm_source == AlarmSource.WEATHER:
        #     return self._extract_weather_view_url(alarm)
        
        return None
    
    def _extract_event_view_url(self, alarm: Alarm) -> str:
        """
        Extract view URL for EVENT alarms (e.g., motion detection).
        
        For EVENT alarms, we look for sensor_id in the source details
        and generate a URL to the sensor's video stream view.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Look through source_details_list for sensor/entity information
        for source_details in alarm.source_details_list:
            detail_attrs = source_details.detail_attrs
            
            # Try to find sensor_id in the detail attributes
            sensor_id = detail_attrs.get('sensor_id')
            if sensor_id:
                try:
                    # Construct camera URL using the sensor video stream view
                    # SensorVideoStreamView subclasses HiGridView as required
                    from django.urls import reverse
                    return reverse('console_sensor_video_stream', kwargs={'sensor_id': sensor_id})
                except Exception as e:
                    logger.warning(f"Could not construct camera URL for sensor_id {sensor_id}: {e}")
            
            # Try other possible keys that might contain sensor/entity information
            entity_id = detail_attrs.get('entity_id')
            if entity_id:
                # TODO: Implement entity_id → sensor_id mapping if needed
                # This would require looking up the entity and find associated sensors
                logger.debug(f"Found entity_id {entity_id} but no direct mapping to view URL yet")
        
        logger.debug(f"No view URL found for EVENT alarm: {alarm.alarm_type}")
        return None
