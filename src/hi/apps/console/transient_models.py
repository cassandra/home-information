from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor


@dataclass
class VideoStreamEntity:
    entity           : Entity
    entity_state     : EntityState
    sensor           : Sensor

    @property
    def name(self) -> str:
        name = self.entity.name
        if name.lower().endswith('camera') and len(name) > len('camera'):
            name = name[:-len('camera')].strip()
        return name

    @property
    def motion_detection_state(self) -> Optional[EntityState]:
        """
        Returns the motion detection (MOVEMENT) EntityState for this camera entity if it exists.
        Camera entities typically have a MOVEMENT state for motion detection.
        """
        for entity_state in self.entity.states.all():
            if entity_state.entity_state_type == EntityStateType.MOVEMENT:
                return entity_state
        return None


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
