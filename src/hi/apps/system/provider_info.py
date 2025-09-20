from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProviderInfo:
    """
    Information about an API service for health tracking.

    This container class encapsulates all the metadata needed to identify
    and describe an API service in the health tracking system.
    """

    provider_id    : str           # Technical identifier (e.g., 'hass_api', 'zm_api')
    provider_name  : str           # Human-friendly display name (e.g., 'Home Assistant API')
    description    : Optional[str]  = None  # Optional longer description

    def __str__(self) -> str:
        return f"{self.provider_name} ({self.provider_id})"

    def __hash__(self) -> int:
        return hash(self.provider_id)

    def __eq__(self, other) -> bool:
        if isinstance(other, ProviderInfo):
            return self.provider_id == other.provider_id 
        return False

    @property
    def service_id(self):
        return self.provider_id 

    @property
    def service_name(self):
        return self.provider_name
   
