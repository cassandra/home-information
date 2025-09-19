from dataclasses import dataclass, field
from typing import Dict

from .health_status import HealthStatus
from .api_health import ApiHealthStatus
from .api_service_info import ApiServiceInfo
from .enums import HealthStatusType, ApiHealthStatusType, HealthAggregationRule


@dataclass
class ApiHealthAggregator(HealthStatus):
    """
    Extends HealthStatus to add API source tracking and aggregation.
    """
    # Current aggregated API health data
    api_sources      : Dict[ApiServiceInfo, ApiHealthStatus] = field(default_factory=dict)
    aggregation_rule : HealthAggregationRule     = HealthAggregationRule.ALL_SOURCES_HEALTHY

    def aggregate_health(self) -> HealthStatusType:
        """
        Returns the computed health based on aggregation rule.
        """
        if not self.api_sources:
            return self.status  # No API sources, use base health

        api_statuses = [ api.status for api in self.api_sources.values() ]

        if self.aggregation_rule == HealthAggregationRule.ALL_SOURCES_HEALTHY:
            # All must be healthy
            if all( s == ApiHealthStatusType.HEALTHY for s in api_statuses ):
                return HealthStatusType.HEALTHY
            elif any( s in [ ApiHealthStatusType.FAILING,
                             ApiHealthStatusType.UNAVAILABLE ]
                      for s in api_statuses) :
                return HealthStatusType.ERROR
            else:
                return HealthStatusType.WARNING

        elif self.aggregation_rule == HealthAggregationRule.MAJORITY_SOURCES_HEALTHY:
            # Majority must be healthy
            healthy_count = sum( 1 for s in api_statuses
                                 if s == ApiHealthStatusType.HEALTHY )
            if healthy_count > len(api_statuses) / 2:
                return HealthStatusType.HEALTHY
            else:
                return HealthStatusType.WARNING

        elif self.aggregation_rule == HealthAggregationRule.ANY_SOURCE_HEALTHY:
            # At least one must be healthy
            if any( s == ApiHealthStatusType.HEALTHY for s in api_statuses ):
                return HealthStatusType.HEALTHY
            else:
                return HealthStatusType.ERROR

        return self.status  # Fallback to base status

    @property
    def overall_status(self) -> HealthStatusType:
        """
        Get overall status considering both base health and API health.
        """
        api_health = self.aggregate_health()

        # Return worst of base status and aggregated API status using priority
        statuses = [self.status, api_health]

        # Return status with highest priority (lowest priority number)
        return min(statuses, key=lambda s: s.priority)

    def to_dict(self) -> dict:
        # Start with base class dict
        result = super().to_dict()

        # Add our api_sources
        result['api_sources'] = [api.to_dict() for api in self.api_sources.values()]
        result['aggregation_rule'] = self.aggregation_rule.value
        result['overall_status'] = self.overall_status.value

        return result
