from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from hi.apps.entity.models import Entity, EntityState


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
