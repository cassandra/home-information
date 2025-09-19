"""
Business logic service for aggregating monitor health status.

This service implements the domain rules defined in MonitorHealthAggregationRule
and provides centralized logic for determining overall monitor health from
multiple status inputs (heartbeat, API sources, etc.).
"""

import logging
from datetime import datetime
from typing import List, Optional

import hi.apps.common.datetimeproxy as datetimeproxy
from .enums import (
    MonitorHealthStatusType,
    MonitorHeartbeatStatusType,
    ApiSourceHealthStatusType,
    MonitorHealthAggregationRule
)
from .transient_models import MonitorHealthStatus, ApiSourceHealth

logger = logging.getLogger(__name__)


class MonitorHealthAggregationService:
    """
    Service for aggregating monitor health status using domain business rules.

    This service encapsulates the complex logic for determining overall monitor
    health based on multiple factors including heartbeat status, API source health,
    and configurable aggregation rules.
    """

    @staticmethod
    def calculate_heartbeat_status(last_heartbeat: Optional[datetime]) -> MonitorHeartbeatStatusType:
        """
        Calculate heartbeat status based on last heartbeat timestamp.

        Args:
            last_heartbeat: Timestamp of last heartbeat, None if never seen

        Returns:
            Appropriate heartbeat status
        """
        if last_heartbeat is None:
            return MonitorHeartbeatStatusType.DEAD

        seconds_since_last = (datetimeproxy.now() - last_heartbeat).total_seconds()
        return MonitorHeartbeatStatusType.from_last_heartbeat(seconds_since_last)

    @staticmethod
    def calculate_api_source_health(
        success_rate: Optional[float] = None,
        avg_response_time: Optional[float] = None,
        consecutive_failures: int = 0,
        total_failures: int = 0,
        total_requests: int = 0
    ) -> ApiSourceHealthStatusType:
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
        return ApiSourceHealthStatusType.from_metrics(
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            consecutive_failures=consecutive_failures,
            total_failures=total_failures,
            total_requests=total_requests
        )

    @classmethod
    def aggregate_api_source_health(
        cls,
        api_sources: List[ApiSourceHealth],
        aggregation_rule: MonitorHealthAggregationRule
    ) -> MonitorHealthStatusType:
        """
        Aggregate health status across multiple API sources using specified rule.

        Args:
            api_sources: List of API source health status objects
            aggregation_rule: Rule to use for aggregation

        Returns:
            Aggregated monitor health status
        """
        if not api_sources:
            if aggregation_rule == MonitorHealthAggregationRule.HEARTBEAT_ONLY:
                return MonitorHealthStatusType.HEALTHY  # No API dependencies
            else:
                return MonitorHealthStatusType.HEALTHY  # No sources to fail

        # Convert API source statuses to monitor health statuses
        api_health_statuses = [source.status.to_monitor_health_status() for source in api_sources]

        # Count each status type
        healthy_count = sum(1 for status in api_health_statuses if status == MonitorHealthStatusType.HEALTHY)
        warning_count = sum(1 for status in api_health_statuses if status == MonitorHealthStatusType.WARNING)
        error_count = sum(1 for status in api_health_statuses if status == MonitorHealthStatusType.ERROR)

        total_sources = len(api_sources)

        # Apply aggregation rule
        if aggregation_rule == MonitorHealthAggregationRule.ALL_SOURCES_HEALTHY:
            # All sources must be healthy
            if error_count > 0:
                return MonitorHealthStatusType.ERROR
            elif warning_count > 0:
                return MonitorHealthStatusType.WARNING
            else:
                return MonitorHealthStatusType.HEALTHY

        elif aggregation_rule == MonitorHealthAggregationRule.MAJORITY_SOURCES_HEALTHY:
            # Majority of sources must be healthy
            majority_threshold = (total_sources + 1) // 2  # More than half

            if error_count >= majority_threshold:
                return MonitorHealthStatusType.ERROR
            elif (error_count + warning_count) >= majority_threshold:
                return MonitorHealthStatusType.WARNING
            else:
                return MonitorHealthStatusType.HEALTHY

        elif aggregation_rule == MonitorHealthAggregationRule.ANY_SOURCE_HEALTHY:
            # At least one source must be healthy
            if healthy_count > 0:
                return MonitorHealthStatusType.HEALTHY
            elif warning_count > 0:
                return MonitorHealthStatusType.WARNING
            else:
                return MonitorHealthStatusType.ERROR

        elif aggregation_rule == MonitorHealthAggregationRule.WEIGHTED_AVERAGE:
            # Future enhancement - for now, use majority rule
            logger.warning("Weighted average aggregation not yet implemented, using majority rule")
            return cls.aggregate_api_source_health(api_sources, MonitorHealthAggregationRule.MAJORITY_SOURCES_HEALTHY)

        else:  # HEARTBEAT_ONLY or unknown
            return MonitorHealthStatusType.HEALTHY

    @classmethod
    def calculate_overall_monitor_health(
        cls,
        monitor_health_status: MonitorHealthStatus,
        aggregation_rule: Optional[MonitorHealthAggregationRule] = None
    ) -> MonitorHealthStatusType:
        """
        Calculate overall monitor health status from all available inputs.

        This is the primary business logic entry point that combines:
        - Current monitor status
        - Heartbeat status
        - API source health aggregation
        - Aggregation rule logic

        Args:
            monitor_health_status: Current monitor health status object
            aggregation_rule: Rule to use for aggregation (auto-determined if None)

        Returns:
            Overall calculated monitor health status
        """
        # Auto-determine aggregation rule if not provided
        if aggregation_rule is None:
            api_count = len(monitor_health_status.api_sources)
            aggregation_rule = MonitorHealthAggregationRule.default_for_api_count(api_count)

        # Calculate heartbeat status
        heartbeat_status = cls.calculate_heartbeat_status(monitor_health_status.monitor_heartbeat)
        heartbeat_health = heartbeat_status.to_monitor_health_status()

        # Calculate API source aggregated health
        api_health = cls.aggregate_api_source_health(monitor_health_status.api_sources, aggregation_rule)

        # Combine heartbeat and API health using worst-case logic
        # (if either heartbeat or API sources are unhealthy, overall is unhealthy)
        combined_statuses = [heartbeat_health, api_health]

        # Apply priority-based worst-case logic
        if MonitorHealthStatusType.ERROR in combined_statuses:
            return MonitorHealthStatusType.ERROR
        elif MonitorHealthStatusType.WARNING in combined_statuses:
            return MonitorHealthStatusType.WARNING
        else:
            return MonitorHealthStatusType.HEALTHY

    @classmethod
    def should_update_monitor_status(
        cls,
        current_status: MonitorHealthStatusType,
        calculated_status: MonitorHealthStatusType,
        error_count: int = 0
    ) -> bool:
        """
        Determine if monitor status should be updated based on business rules.

        This implements hysteresis logic to prevent status flapping and ensures
        that status changes are meaningful and stable.

        Args:
            current_status: Current monitor health status
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
        monitor_health_status: MonitorHealthStatus,
        aggregation_rule: Optional[MonitorHealthAggregationRule] = None
    ) -> str:
        """
        Generate a human-readable health summary message.

        Args:
            monitor_health_status: Current monitor health status
            aggregation_rule: Rule used for aggregation

        Returns:
            Human-readable summary of monitor health
        """
        overall_status = cls.calculate_overall_monitor_health(monitor_health_status, aggregation_rule)

        # Calculate component status
        heartbeat_status = cls.calculate_heartbeat_status(monitor_health_status.monitor_heartbeat)
        api_count = len(monitor_health_status.api_sources)
        healthy_api_count = sum(
            1 for source in monitor_health_status.api_sources
            if source.status == ApiSourceHealthStatusType.HEALTHY
        )

        if overall_status == MonitorHealthStatusType.HEALTHY:
            if api_count > 0:
                return f"Monitor is healthy. Heartbeat is {heartbeat_status.label.lower()} and all {api_count} API sources are responding normally."
            else:
                return f"Monitor is healthy. Heartbeat is {heartbeat_status.label.lower()}."

        elif overall_status == MonitorHealthStatusType.WARNING:
            issues = []
            if heartbeat_status != MonitorHeartbeatStatusType.ACTIVE:
                issues.append(f"heartbeat is {heartbeat_status.label.lower()}")
            if api_count > 0 and healthy_api_count < api_count:
                issues.append(f"{healthy_api_count}/{api_count} API sources are healthy")

            issue_text = " and ".join(issues) if issues else "experiencing temporary issues"
            return f"Monitor has warnings: {issue_text}. Monitoring recommended."

        else:  # ERROR
            issues = []
            if heartbeat_status == MonitorHeartbeatStatusType.DEAD:
                issues.append("heartbeat is dead")
            if api_count > 0:
                failing_count = sum(
                    1 for source in monitor_health_status.api_sources
                    if source.status in (
                        ApiSourceHealthStatusType.FAILING,
                        ApiSourceHealthStatusType.UNAVAILABLE
                    )
                )
                if failing_count > 0:
                    issues.append(f"{failing_count}/{api_count} API sources are failing")

            issue_text = " and ".join(issues) if issues else "experiencing critical errors"
            return f"Monitor requires immediate attention: {issue_text}. Please check configuration and external service availability."
