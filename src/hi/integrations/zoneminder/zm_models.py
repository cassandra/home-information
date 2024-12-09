from dataclasses import dataclass
from typing import Dict

import hi.apps.common.datetimeproxy as datetimeproxy

from pyzm.helpers.Event import Event as ZmApiEvent

from .zm_manager import ZoneMinderManager


class ZmEvent:

    def __init__( self, zm_api_event : ZmApiEvent, zm_tzname : str ):
        self._event_id = zm_api_event.id()
        self._monitor_id = zm_api_event.monitor_id()
        self._start_datetime = self._to_datetime( zm_api_event.get()['StartTime'],zm_tzname  )
        self._end_datetime = self._to_datetime( zm_api_event.get()['EndTime'], zm_tzname )
        self._cause = zm_api_event.cause()
        self._duration_secs = zm_api_event.duration()
        try:
            self._total_frame_count = zm_api_event.total_frames()
        except (TypeError, ValueError):
            self._total_frame_count = 0
        try:
            self._alarmed_frame_count = zm_api_event.alarmed_frames()
        except (TypeError, ValueError):
            self._alarmed_frame_count = 0
        self._score = zm_api_event.score()
        self._notes = zm_api_event.notes()
        self._max_score_frame_id = zm_api_event.get()['MaxScoreFrameId']
        return

    @property
    def event_id(self):
        return self._event_id
    
    @property
    def monitor_id(self):
        return self._monitor_id

    @property
    def start_datetime(self):
        return self._start_datetime
    
    @property
    def end_datetime(self):
        return self._end_datetime

    @property
    def is_closed(self):
        return bool( self._end_datetime is not None )
    
    @property
    def is_open(self):
        return bool( self._end_datetime is None )
    
    @property
    def cause(self):
        return self._cause
    
    @property
    def duration_secs(self):
        return self._duration_secs
    
    @property
    def total_frame_count(self):
        return self._total_frame_count
    
    @property
    def alarmed_frame_count(self):
        return self._alarmed_frame_count
    
    @property
    def score(self):
        return self._score
    
    @property
    def notes(self):
        return self._notes
    
    @property
    def max_score_frame_id(self):
        return self._max_score_frame_id
    
    @property
    def video_url( self, zm_manager : ZoneMinderManager ):
        return '{}/index.php?view=event&eid={}'.format(
            zm_manager.zm_client.get_portalbase(),
            self._event_id,
        )
    
    def image_url( self, zm_manager : ZoneMinderManager ):
        return '{}/index.php?view=image&eid={}&fid=snapshot'.format(
            zm_manager.zm_client.get_portalbase(),
            self._event_id,
        )
    
    def _to_datetime( self, zm_response_time : str, tzname : str ):
        if not zm_response_time:
            return None
        return datetimeproxy.iso_naive_to_datetime_utc( zm_response_time, tzname )
    
    def to_detail_attrs( self ) -> Dict[ str, str ]:
        return {
            'Event Id': self.event_id,
            'Start Time': self.start_datetime.isoformat(),
            'Score': self.score,
            'Duration (secs)': self.duration_secs,
            'Alarmed Frames': self.alarmed_frame_count,
            'Total Frames': self.total_frame_count,
            'Notes': self.notes,
        }
