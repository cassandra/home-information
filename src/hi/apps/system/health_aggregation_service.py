"""
Business logic service for aggregating health status.

This service implements the domain rules defined in HealthAggregationRule
and provides centralized logic for determining overall health from
multiple status inputs (heartbeat, API sources, etc.).
"""

import logging
from datetime import datetime
from typing import List, Optional

import hi.apps.common.datetimeproxy as datetimeproxy

from .api_health import ApiHealthStatus
from .enums import (
    HealthStatusType,
    HeartbeatStatusType,
    ApiHealthStatusType,
    HealthAggregationRule
)
from .health_status import HealthStatus

logger = logging.getLogger(__name__)


class HealthAggregationService:
    """
    Service for aggregating health status using domain business rules.

    This service encapsulates the complex logic for determining overall
    health based on multiple factors including heartbeat status, API source health,
    and configurable aggregation rules.
    """

    @staticmethod
    def calculate_heartbeat_status(last_heartbeat: Optional[datetime]) -> HeartbeatStatusType:
        """
        Calculate heartbeat status based on last heartbeat timestamp.

        Args:
            last_heartbeat: Timestamp of last heartbeat, None if never seen

        Returns:
            Appropriate heartbeat status
        """
        if last_heartbeat is None:
            return HeartbeatStatusType.DEAD

        seconds_since_last = (datetimeproxy.now() - last_heartbeat).total_seconds()
        return HeartbeatStatusType.from_last_heartbeat(seconds_since_last)

    @staticmethod
    def calculate_api_source_health(
        success_rate: Optional[float] = None,
        avg_response_time: Optional[float] = None,
        consecutive_failures: int = 0,
        total_failures: int = 0,
        total_requests: int = 0
    ) -> ApiHealthStatusType:
        """
        Calculate API source health status using business logic thresholds.

        Args:
            success_rate: Ratio of successful requests (0.0 to 1.0)
            avg_response_time: Average response time in seconds
            consecutive_failures: Number of consecutive failures
            total_failures: Total number of failures in monitoring window
            total_requests: Total number of requests in monitoring window

        Returns:
            Appropriate API source health status
        """
        return ApiHealthStatusType.from_metrics(
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            consecutive_failures=consecutive_failures,
            total_failures=total_failures,
            total_requests=total_requests
        )

    @classmethod
    def aggregate_api_source_health(
        cls,
        api_sources: List[ApiHealthStatus],
        aggregation_rule: HealthAggregationRule
    ) -> HealthStatusType:
        """
        Aggregate health status across multiple API sources using specified rule.

        Args:
            api_sources: List of API source health status objects
            aggregation_rule: Rule to use for aggregation

        Returns:
            Aggregated health status
        """
        if not api_sources:
            if aggregation_rule == HealthAggregationRule.HEARTBEAT_ONLY:
                return HealthStatusType.HEALTHY  # No API dependencies
            else:
                return HealthStatusType.HEALTHY  # No sources to fail

        # Convert API source statuses to health statuses
        api_health_statuses = [source.status.to_health_status() for source in api_sources]

        # Count each status type
        healthy_count = sum(1 for status in api_health_statuses if status == HealthStatusType.HEALTHY)
        warning_count = sum(1 for status in api_health_statuses if status == HealthStatusType.WARNING)
        error_count = sum(1 for status in api_health_statuses if status == HealthStatusType.ERROR)

        total_sources = len(api_sources)

        # Apply aggregation rule
        if aggregation_rule == HealthAggregationRule.ALL_SOURCES_HEALTHY:
            # All sources must be healthy
            if error_count > 0:
                return HealthStatusType.ERROR
            elif warning_count > 0:
                return HealthStatusType.WARNING
            else:
                return HealthStatusType.HEALTHY

        elif aggregation_rule == HealthAggregationRule.MAJORITY_SOURCES_HEALTHY:
            # Majority of sources must be healthy
            majority_threshold = (total_sources + 1) // 2  # More than half

            if error_count >= majority_threshold:
                return HealthStatusType.ERROR
            elif (error_count + warning_count) >= majority_threshold:
                return HealthStatusType.WARNING
            else:
                return HealthStatusType.HEALTHY

        elif aggregation_rule == HealthAggregationRule.ANY_SOURCE_HEALTHY:
            # At least one source must be healthy
            if healthy_count > 0:
                return HealthStatusType.HEALTHY
            elif warning_count > 0:
                return HealthStatusType.WARNING
            else:
                return HealthStatusType.ERROR

        elif aggregation_rule == HealthAggregationRule.WEIGHTED_AVERAGE:
            # Future enhancement - for now, use majority rule
            logger.warning("Weighted average aggregation not yet implemented, using majority rule")
            return cls.aggregate_api_source_health(api_sources, HealthAggregationRule.MAJORITY_SOURCES_HEALTHY)

        else:  # HEARTBEAT_ONLY or unknown
            return HealthStatusType.HEALTHY

    @classmethod
    def calculate_overall_health(
        cls,
        health_status: HealthStatus,
        aggregation_rule: Optional[HealthAggregationRule] = None
    ) -> HealthStatusType:
        """
        Calculate overall health status from all available inputs.

        This is the primary business logic entry point that combines:
        - Current status
        - Heartbeat status
        - API source health aggregation
        - Aggregation rule logic

        Args:
            health_status: Current health status object
            aggregation_rule: Rule to use for aggregation (auto-determined if None)

        Returns:
            Overall calculated health status
        """
        # Auto-determine aggregation rule if not provided
        if aggregation_rule is None:
            api_count = len(health_status.api_sources)
            aggregation_rule = HealthAggregationRule.default_for_api_count(api_count)

        # Calculate heartbeat status
        heartbeat_status = cls.calculate_heartbeat_status(health_status.heartbeat)
        heartbeat_health = heartbeat_status.to_health_status()

        # Calculate API source aggregated health
        api_health = cls.aggregate_api_source_health(health_status.api_sources, aggregation_rule)

        # Combine heartbeat and API health using worst-case logic
        # (if either heartbeat or API sources are unhealthy, overall is unhealthy)
        combined_statuses = [heartbeat_health, api_health]

        # Apply priority-based worst-case logic
        if HealthStatusType.ERROR in combined_statuses:
            return HealthStatusType.ERROR
        elif HealthStatusType.WARNING in combined_statuses:
            return HealthStatusType.WARNING
        else:
            return HealthStatusType.HEALTHY

    @classmethod
    def should_update_status(
        cls,
        current_status: HealthStatusType,
        calculated_status: HealthStatusType,
        error_count: int = 0
    ) -> bool:
        """
        Determine if status should be updated based on business rules.

        This implements hysteresis logic to prevent status flapping and ensures
        that status changes are meaningful and stable.

        Args:
            current_status: Current health status
            calculated_status: Newly calculated health status
            error_count: Current error count for stability assessment

        Returns:
            True if status should be updated
        """
        # Always update if status is improving
        if calculated_status.priority > current_status.priority:
            return True

        # Always update if status is significantly degrading
        if calculated_status.priority < current_status.priority:
            return True

        # For same status, update if this represents a meaningful change
        # (this could be enhanced with more sophisticated logic)
        return False

    @classmethod
    def get_health_summary_message(
        cls,
        health_status: HealthStatus,
        aggregation_rule: Optional[HealthAggregationRule] = None
    ) -> str:
        """
        Generate a human-readable health summary message.

        Args:
            health_status: Current health status
            aggregation_rule: Rule used for aggregation

        Returns:
            Human-readable summary of health
        """
        overall_status = cls.calculate_overall_health(health_status, aggregation_rule)

        # Calculate component status
        heartbeat_status = cls.calculate_heartbeat_status(health_status.heartbeat)
        api_count = len(health_status.api_sources)
        healthy_api_count = sum(
            1 for source in health_status.api_sources
            if source.status == ApiHealthStatusType.HEALTHY
        )

        if overall_status == HealthStatusType.HEALTHY:
            if api_count > 0:
                return f"Is healthy. Heartbeat is {heartbeat_status.label.lower()} and all {api_count} API sources are responding normally."
            else:
                return f"Is healthy. Heartbeat is {heartbeat_status.label.lower()}."

        elif overall_status == HealthStatusType.WARNING:
            issues = []
            if heartbeat_status != HeartbeatStatusType.ACTIVE:
                issues.append(f"heartbeat is {heartbeat_status.label.lower()}")
            if api_count > 0 and healthy_api_count < api_count:
                issues.append(f"{healthy_api_count}/{api_count} API sources are healthy")

            issue_text = " and ".join(issues) if issues else "experiencing temporary issues"
            return f"Has warnings: {issue_text}. Monitoring recommended."

        else:  # ERROR
            issues = []
            if heartbeat_status == HeartbeatStatusTypey.DEAD:
                issues.append("heartbeat is dead")
            if api_count > 0:
                failing_count = sum(
                    1 for source in health_status.api_sources
                    if source.status in (
                        ApiHealthStatusType.FAILING,
                        ApiHealthStatusType.UNAVAILABLE
                    )
                )
                if failing_count > 0:
                    issues.append(f"{failing_count}/{api_count} API sources are failing")

            issue_text = " and ".join(issues) if issues else "experiencing critical errors"
            return f"Requires immediate attention: {issue_text}. Please check configuration and external service availability."
