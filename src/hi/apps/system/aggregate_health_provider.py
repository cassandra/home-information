import copy
import logging
from typing import Sequence

import hi.apps.common.datetimeproxy as datetimeproxy

from .aggregate_health_status import AggregateHealthStatus
from .api_health_status_provider import ApiHealthStatusProvider
from .health_status import HealthStatus
from .health_status_provider import HealthStatusProvider
from .enums import HealthStatusType, HealthAggregationRule

logger = logging.getLogger(__name__)


class AggregateHealthProvider( HealthStatusProvider ):
    """
    Provider for components that aggregate API health from one or more sources.
    Provides health status tracking with API health aggregation capability.

    This provider can be used alongside ApiHealthStatusProvider for components that both
    make their own API calls and need to track/aggregate API health.
    """

    @property
    def initial_health_status(self) -> HealthStatus:
        provider_info = self.get_provider_info()
        return AggregateHealthStatus(
            provider_id = provider_info.provider_id,
            provider_name = provider_info.provider_name,
            status = HealthStatusType.UNKNOWN,
            last_update = datetimeproxy.now(),
            last_message = 'Initialization',
            aggregation_rule = self._get_aggregation_rule()
        )
    
    def _ensure_health_status_provider_setup(self):
        if hasattr( self, '_health_status' ):
            return
        super()._ensure_health_status_provider_setup()
        self._api_health_status_providers = []  # Track API health status providers
        return

    @property
    def health_status(self) -> AggregateHealthStatus:
        """Get aggregated health status (thread-safe, always fresh)."""
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            # Always refresh from API owners before returning
            self._refresh_aggregated_health()
            return copy.deepcopy(self._health_status)
        return

    def refresh_aggregated_health(self) -> None:
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            self._refresh_aggregated_health()
    
    def _refresh_aggregated_health(self) -> None:
        """Refresh API status map from all tracked API health status providers.

        Note: The aggregated health status is computed dynamically via the status property,
        so this method only needs to update the API status map.
        """
        # Clear current sources
        self._health_status.api_status_map.clear()

        # Collect current health from all providers
        for provider in self._api_health_status_providers:
            provider_info = provider.get_api_provider_info()
            api_health_status = provider.api_health_status
            self._health_status.api_status_map[provider_info] = api_health_status

        # Status is now computed dynamically via the status property in AggregateHealthStatus
        # No need to manually update it here
        return

    def _get_aggregation_rule(self) -> HealthAggregationRule:
        """Override to provide custom aggregation rule."""
        return HealthAggregationRule.ALL_SOURCES_HEALTHY
    
    def add_api_health_status_provider(
            self,
            api_health_status_provider : ApiHealthStatusProvider ) -> None:
        """Add an API health status provider to be tracked and aggregated."""
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            if api_health_status_provider not in self._api_health_status_providers:
                self._api_health_status_providers.append( api_health_status_provider )
                self._refresh_aggregated_health()
        return
    
    def add_api_health_status_provider_multi(
            self,
            api_health_status_provider_sequence : Sequence[ ApiHealthStatusProvider ]
    ) -> None:
        """Add API health status providers to be tracked and aggregated."""
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            for api_health_status_provider in api_health_status_provider_sequence:
                if api_health_status_provider not in self._api_health_status_providers:
                    self._api_health_status_providers.append(api_health_status_provider)
                continue
            self._refresh_aggregated_health()
        return
            
    def remove_api_health_status_provider(
            self,
            api_health_status_provider : ApiHealthStatusProvider
    ) -> None:
        """Remove an API health status provider from tracking."""
        self._ensure_health_status_provider_setup()
        with self._health_lock:
            if api_health_status_provider in self._api_health_status_providers:
                self._api_health_status_providers.remove(api_health_status_provider)
                self._refresh_aggregated_health()
        return
