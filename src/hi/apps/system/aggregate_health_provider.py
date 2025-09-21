from abc import ABC, abstractmethod
import copy
import logging
import threading
from typing import Optional, Sequence

import hi.apps.common.datetimeproxy as datetimeproxy

from .aggregate_health_status import AggregateHealthStatus
from .api_health_status_provider import ApiHealthStatusProvider
from .enums import HealthStatusType, HealthAggregationRule
from .provider_info import ProviderInfo

logger = logging.getLogger(__name__)


class AggregateHealthProvider(ABC):
    """
    Provider for components that aggregate API health from one or more sources.
    Provides health status tracking with API health aggregation capability.

    This provider can be used alongside ApiHealthStatusProvider for components that both
    make their own API calls and need to track/aggregate API health.

    This *should not* be used alongside HealthStatusProvider.
    """

    def _ensure_api_aggregator_setup(self):
        if hasattr(self, '_aggregated_health_status'):
            return

        self._health_lock = threading.Lock()
        self._api_health_status_providers = []  # Track API health status providers

        provider_info = self.get_provider_info()
        self._aggregated_health_status = AggregateHealthStatus(
            provider_id = provider_info.provider_id,
            provider_name = provider_info.provider_name,
            status = HealthStatusType.UNKNOWN,
            last_check = datetimeproxy.now(),
            aggregation_rule = self._get_aggregation_rule()
        )

    def _get_aggregation_rule(self) -> HealthAggregationRule:
        """Override to provide custom aggregation rule."""
        return HealthAggregationRule.ALL_SOURCES_HEALTHY

    @classmethod
    @abstractmethod
    def get_provider_info(cls) -> ProviderInfo:
        """Get the API service info for this class. Must be implemented by subclasses."""
        pass

    @property
    def health_status(self) -> AggregateHealthStatus:
        """Get aggregated health status (thread-safe, always fresh)."""
        self._ensure_api_aggregator_setup()
        with self._health_lock:
            # Always refresh from API owners before returning
            self._refresh_aggregated_health()
            return copy.deepcopy(self._aggregated_health_status)
        return
    
    def add_api_health_status_provider(
            self,
            api_health_status_provider : ApiHealthStatusProvider ) -> None:
        """Add an API health status provider to be tracked and aggregated."""
        self._ensure_api_aggregator_setup()
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
        self._ensure_api_aggregator_setup()
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
        self._ensure_api_aggregator_setup()
        with self._health_lock:
            if api_health_status_provider in self._api_health_status_providers:
                self._api_health_status_providers.remove(api_health_status_provider)
                self._refresh_aggregated_health()
        return
    
    def _refresh_aggregated_health(self) -> None:
        """Refresh API status map from all tracked API health status providers.

        Note: The aggregated health status is computed dynamically via the status property,
        so this method only needs to update the API status map.
        """
        # Clear current sources
        self._aggregated_health_status.api_status_map.clear()

        # Collect current health from all providers
        for provider in self._api_health_status_providers:
            service_info = provider.get_api_provider_info()
            api_health = provider.api_health_status
            self._aggregated_health_status.api_status_map[service_info] = api_health

        # Status is now computed dynamically via the status property in AggregateHealthStatus
        # No need to manually update it here
        return
    
    def update_health_status( self,
                              status         : HealthStatusType,
                              error_message  : Optional[str]     = None) -> None:
        """Update the base health status."""
        self._ensure_api_aggregator_setup()
        with self._health_lock:
            self._aggregated_health_status.status = status
            self._aggregated_health_status.last_check = datetimeproxy.now()
            self._aggregated_health_status.error_message = error_message

            if status.is_error:
                self._aggregated_health_status.error_count += 1
            else:
                # Reset error count on successful status
                self._aggregated_health_status.error_count = 0

        logger.debug( f'Health status updated to {status.label}:'
                      f' {error_message or "No error"}')

    def record_warning(self, error_message: str) -> None:
        self.update_health_status(HealthStatusType.WARNING, error_message)

    def record_error(self, error_message: str) -> None:
        self.update_health_status(HealthStatusType.ERROR, error_message)

    def update_heartbeat(self) -> None:
        self._ensure_api_aggregator_setup()
        with self._health_lock:
            self._aggregated_health_status.heartbeat = datetimeproxy.now()
        logger.debug("Health heartbeat updated")

    def refresh_aggregated_health(self) -> None:
        self._ensure_api_aggregator_setup()
        with self._health_lock:
            self._refresh_aggregated_health()
