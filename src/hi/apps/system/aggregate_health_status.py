from dataclasses import dataclass, field
from typing import Dict

from .health_status import HealthStatus
from .api_health_status import ApiHealthStatus
from .provider_info import ProviderInfo
from .enums import HealthStatusType, ApiHealthStatusType, HealthAggregationRule


@dataclass
class AggregateHealthStatus( HealthStatus ):
    """
    Extends HealthStatus to add API source tracking and aggregation.
    The status property returns the aggregated health status combined with base status.
    """
    # Current aggregated API health data
    api_status_map    : Dict[ProviderInfo, ApiHealthStatus] = field(default_factory=dict)
    aggregation_rule  : HealthAggregationRule     = HealthAggregationRule.ALL_SOURCES_HEALTHY

    # Store the base status separately (for provider's own health issues)
    _base_status      : HealthStatusType = field(default=HealthStatusType.HEALTHY, init=False)

    @property
    def status(self) -> HealthStatusType:
        """
        Override status to return the combined health status.
        Returns the worst of base status and aggregated API status.
        """
        api_health = self.aggregate_health()

        # Return worst of base status and aggregated API status using priority
        # Lower priority number = worse health
        return min([ self._base_status, api_health ], key=lambda s: s.priority )

    @status.setter
    def status(self, value: HealthStatusType) -> None:
        """Allow setting the base status (for provider's own health issues)."""
        self._base_status = value

    def aggregate_health(self) -> HealthStatusType:
        """
        Returns the computed health based on aggregation rule.
        DISABLED sources are excluded from health calculations.
        """
        if not self.api_status_map:
            return self._base_status  # No API sources, use base health

        # Filter out DISABLED sources - they don't contribute to health calculations
        active_api_statuses = [ api.status for api in self.api_status_map.values()
                                if api.status != ApiHealthStatusType.DISABLED ]

        # If all sources are disabled, use base health status
        if not active_api_statuses:
            return self._base_status

        # Count status types we need for decision making
        healthy_count = sum( 1 for s in active_api_statuses
                             if s == ApiHealthStatusType.HEALTHY )
        failing_count = sum( 1 for s in active_api_statuses
                             if s == ApiHealthStatusType.FAILING )
        unavailable_count = sum( 1 for s in active_api_statuses
                                 if s == ApiHealthStatusType.UNAVAILABLE )

        total_active = len(active_api_statuses)

        # Apply aggregation rule
        if self.aggregation_rule == HealthAggregationRule.ALL_SOURCES_HEALTHY:
            # All active sources must be healthy
            if healthy_count == total_active:
                return HealthStatusType.HEALTHY
            elif failing_count > 0 or unavailable_count > 0:
                return HealthStatusType.ERROR
            else:  # Has degraded or unknown sources
                return HealthStatusType.WARNING

        elif self.aggregation_rule == HealthAggregationRule.MAJORITY_SOURCES_HEALTHY:
            # Majority of active sources must be healthy
            if healthy_count > total_active / 2:
                return HealthStatusType.HEALTHY
            elif failing_count > 0 or unavailable_count > 0:
                return HealthStatusType.ERROR
            else:
                return HealthStatusType.WARNING

        elif self.aggregation_rule == HealthAggregationRule.ANY_SOURCE_HEALTHY:
            # At least one active source must be healthy
            if healthy_count > 0:
                return HealthStatusType.HEALTHY
            elif failing_count > 0 or unavailable_count > 0:
                return HealthStatusType.ERROR
            else:  # Only degraded/unknown sources
                return HealthStatusType.WARNING

        # Fallback to base status for unknown aggregation rules
        return self._base_status
