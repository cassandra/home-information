from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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
