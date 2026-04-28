from dataclasses import dataclass, field
from typing import Dict

from .health_status import HealthStatus
from .api_health_status import ApiHealthStatus
from .provider_info import ProviderInfo
from .enums import HealthStatusType, ApiHealthStatusType, HealthAggregationRule


@dataclass
class AggregateHealthStatus( HealthStatus ):
    """
    Extends HealthStatus to add aggregation across multiple status
    sources. The `status` property returns the worst-of:
      - This provider's own base status (set via record_* on itself).
      - The API source aggregate (api_status_map, with aggregation_rule).
      - Each registered subordinate provider's current status
        (subordinate_status_map, populated on read by the
        AggregateHealthProvider).

    Per-source slots exist because a single status field would alias.
    A successful reload setting _base_status=HEALTHY must not silently
    overwrite a separate subordinate (e.g., a polling monitor) that is
    still reporting ERROR.
    """
    # Current aggregated API health data
    api_status_map         : Dict[ProviderInfo, ApiHealthStatus]  = field(default_factory=dict)

    # Snapshot of subordinate HealthStatusProvider statuses, populated
    # on read of the parent AggregateHealthProvider. Mirrors
    # api_status_map's shape: keyed by ProviderInfo, valued by the
    # subordinate's full HealthStatus so the modal / detail views can
    # render last_message, heartbeat, error_count, etc.
    subordinate_status_map : Dict[ProviderInfo, HealthStatus] = field(default_factory=dict)

    aggregation_rule       : HealthAggregationRule  = HealthAggregationRule.ALL_SOURCES_HEALTHY

    # Store the base status separately (for provider's own health issues)
    _base_status           : HealthStatusType = field(default=HealthStatusType.HEALTHY, init=False)

    @property
    def status(self) -> HealthStatusType:
        """
        Override status to return the combined health status.
        Returns the worst of base status, aggregated API status, and
        every registered subordinate's status.
        """
        candidates = [ self._base_status, self.aggregate_health() ]
        candidates.extend( hs.status for hs in self.subordinate_status_map.values() )

        # Lower priority number = worse health
        return min( candidates, key=lambda s: s.priority )

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
