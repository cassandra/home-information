from typing import Dict, List, Optional

from hi.apps.sense.sensor_response_manager import SensorResponseManager

from .transient_models import IntegrationKey


class IntegrationConverterMixin:
    """Shared capabilities for integration converters. The current
    capability is sibling state-value lookup, used by integrations
    whose outbound calls compose values from multiple HI EntityStates
    that share a single upstream device (one-to-many decomposition
    on the inbound side becomes many-to-one composition on the
    outbound side)."""

    @classmethod
    def get_latest_state_values(
            cls, integration_keys : List[IntegrationKey],
    ) -> Dict[IntegrationKey, Optional[str]]:
        response_map = SensorResponseManager().get_latest_sensor_response_map(
            integration_keys = integration_keys,
        )
        return {
            integration_key: ( response.value if response else None )
            for integration_key, response in response_map.items()
        }
