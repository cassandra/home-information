from dataclasses import dataclass
from datetime import datetime
import re
from typing import Dict, List, Optional

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor
from hi.apps.sense.transient_models import SensorResponse
from .enums import VideoDispatchType


@dataclass
class TransientViewSuggestion:
    """
    Data container for transient view change suggestions.
    Contains URL and metadata for automatic view switching.
    """
    url: str
    duration_seconds: int
    priority: int = 0
    trigger_reason: str = ""
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CameraControlDisplayData:
    """
    Data container for camera control display information.
    Encapsulates entity and its primary status entity state for template rendering.
    """
    entity: Entity
    status_entity_state: Optional[EntityState] = None

    @property
    def short_name(self):
        """ Heuristic rules to reduce name length to fit in side panel narrow buttons """
        short_name = re.sub( r'camera$', '', self.entity.name, flags = re.IGNORECASE )
        return short_name.strip()

    
@dataclass
class EntitySensorHistoryData:
    """
    Data container for entity sensor history browsing functionality.
    Encapsulates all data needed for video sensor history view rendering.
    """
    sensor_responses: List[SensorResponse]
    current_sensor_response: Optional[SensorResponse]
    timeline_groups: List[Dict]
    pagination_metadata: Dict
    prev_sensor_response: Optional[SensorResponse]
    next_sensor_response: Optional[SensorResponse]
    window_start_timestamp: Optional[datetime] = None
    window_end_timestamp: Optional[datetime] = None


@dataclass
class VideoDispatchResult:
    """
    Result of video dispatch decision making.
    Encapsulates the dispatch type and all necessary parameters for routing.
    """
    dispatch_type      : VideoDispatchType
    sensor             : Sensor
    timestamp          : Optional[int] = None  # Unix timestamp for earlier/later views
    window_start       : Optional[int] = None  # Window start timestamp for context preservation
    window_end         : Optional[int] = None  # Window end timestamp for context preservation
    
    @property
    def is_live_stream(self) -> bool:
        """Check if dispatching to live stream view."""
        return self.dispatch_type == VideoDispatchType.LIVE_STREAM
    
    @property
    def is_history_view(self) -> bool:
        """Check if dispatching to any history view."""
        return self.dispatch_type in [
            VideoDispatchType.HISTORY_DEFAULT,
            VideoDispatchType.HISTORY_EARLIER,
            VideoDispatchType.HISTORY_LATER
        ]
    
    def get_view_kwargs(self) -> Dict:
        """
        Get the kwargs needed for the target view.
        Returns dict suitable for updating request kwargs.
        """
        kwargs = { 'sensor_id': self.sensor.id }
        
        if self.timestamp is not None:
            kwargs['timestamp'] = self.timestamp
        if self.window_start is not None:
            kwargs['window_start'] = self.window_start
        if self.window_end is not None:
            kwargs['window_end'] = self.window_end
            
        return kwargs
