from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse


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
