from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.entity.enums import EntityStateValue

from .pyzm_client.helpers.Event import Event as ZmApiEvent

from .constants import ZmDetailKeys
from .zm_manager import ZoneMinderManager


class ZmEvent:

    def __init__( self, zm_api_event : ZmApiEvent, zm_tzname : str ):
        zm_event_dict = zm_api_event.get()
        self._event_id = zm_api_event.id()
        self._monitor_id = zm_api_event.monitor_id()
        self._start_datetime = self._to_datetime( zm_event_dict['StartTime'], zm_tzname  )
        self._end_datetime = self._to_datetime( zm_event_dict['EndTime'], zm_tzname )
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
        self._max_score_frame_id = zm_event_dict['MaxScoreFrameId']
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
            ZmDetailKeys.EVENT_ID_ATTR_NAME: self.event_id,
            ZmDetailKeys.START_TIME: self.start_datetime.isoformat(),
            ZmDetailKeys.SCORE: self.score,
            ZmDetailKeys.DURATION_SECS: self.duration_secs,
            ZmDetailKeys.ALARMED_FRAMES: self.alarmed_frame_count,
            ZmDetailKeys.TOTAL_FRAMES: self.total_frame_count,
            ZmDetailKeys.NOTES: self.notes,
        }


@dataclass
class AggregatedMonitorState:
    """
    Represents the current aggregated state of a ZoneMinder monitor,
    derived from analyzing all events for that monitor.
    """
    monitor_id: int
    current_state: EntityStateValue
    effective_timestamp: datetime
    canonical_event: ZmEvent
    all_events: List[ZmEvent]
    
    @property
    def is_active(self) -> bool:
        """True if monitor is currently in ACTIVE state."""
        return self.current_state == EntityStateValue.ACTIVE
    
    @property
    def is_idle(self) -> bool:
        """True if monitor is currently in IDLE state."""
        return self.current_state == EntityStateValue.IDLE
