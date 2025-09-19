from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ApiServiceInfo:
    """
    Information about an API service for health tracking.

    This container class encapsulates all the metadata needed to identify
    and describe an API service in the health tracking system.
    """

    service_id    : str           # Technical identifier (e.g., 'hass_api', 'zm_api')
    service_name  : str           # Human-friendly display name (e.g., 'Home Assistant API')
    description   : Optional[str]  = None  # Optional longer description

    def __str__(self) -> str:
        return f"{self.service_name} ({self.service_id})"

    def __hash__(self) -> int:
        return hash(self.service_id)

    def __eq__(self, other) -> bool:
        if isinstance(other, ApiServiceInfo):
            return self.service_id == other.service_id
        return False
