from datetime import timedelta
from typing import Dict, List, Optional

from hi.apps.common.enums import LabeledEnum


class MonitorHealthStatusType(LabeledEnum):
    """
    Health status types for monitor health tracking and aggregation.

    These statuses represent the overall health of a monitor based on:
    - Heartbeat/responsiveness status
    - API source health aggregation
    - Error patterns and thresholds
    - Performance metrics
    """

    HEALTHY = ('Healthy', 'Monitor operating normally with all dependencies healthy')
    WARNING = ('Warning', 'Temporary issues detected, monitoring for patterns or degraded performance')
    ERROR = ('Error', 'Critical failures requiring attention or monitor not responding')

    @property
    def is_healthy(self) -> bool:
        """True if monitor is operating normally."""
        return self == MonitorHealthStatusType.HEALTHY

    @property
    def is_warning(self) -> bool:
        """True if monitor has temporary issues or degraded performance."""
        return self == MonitorHealthStatusType.WARNING

    @property
    def is_error(self) -> bool:
        """True if monitor has critical failures."""
        return self == MonitorHealthStatusType.ERROR

    @property
    def is_operational(self) -> bool:
        """True if monitor is still providing value (HEALTHY or WARNING)."""
        return self in (MonitorHealthStatusType.HEALTHY, MonitorHealthStatusType.WARNING)

    @property
    def requires_attention(self) -> bool:
        """True if monitor status requires immediate attention."""
        return self == MonitorHealthStatusType.ERROR

    @classmethod
    def from_priority(cls, priority: int) -> 'MonitorHealthStatusType':
        """
        Map priority levels to health status for backwards compatibility.
        Lower numbers = higher priority = worse health.
        """
        if priority <= 1:
            return cls.ERROR
        elif priority <= 2:
            return cls.WARNING
        else:
            return cls.HEALTHY

    @property
    def priority(self) -> int:
        """
        Priority level for sorting/escalation (lower = higher priority).
        """
        if self == MonitorHealthStatusType.ERROR:
            return 1
        elif self == MonitorHealthStatusType.WARNING:
            return 2
        else:
            return 3


class MonitorHeartbeatStatusType(LabeledEnum):
    """
    Heartbeat-specific health status based on last communication time.
    """

    ACTIVE = ('Active', 'Monitor responding within expected timeframe (< 30 seconds)')
    STALE = ('Stale', 'Monitor response delayed but within tolerance (30 seconds - 5 minutes)')
    DEAD = ('Dead', 'Monitor not responding for extended period (> 5 minutes)')

    @classmethod
    def from_last_heartbeat(cls, seconds_since_last: Optional[float]) -> 'MonitorHeartbeatStatusType':
        """
        Determine heartbeat status based on seconds since last communication.

        Args:
            seconds_since_last: Seconds since last heartbeat, None if never seen

        Returns:
            Appropriate heartbeat status
        """
        ACTIVE_THRESHOLD_SECONDS = 30
        STALE_THRESHOLD_SECONDS = 300  # 5 minutes

        if seconds_since_last is None:
            return cls.DEAD

        if seconds_since_last < ACTIVE_THRESHOLD_SECONDS:
            return cls.ACTIVE
        elif seconds_since_last < STALE_THRESHOLD_SECONDS:
            return cls.STALE
        else:
            return cls.DEAD

    def to_monitor_health_status(self) -> MonitorHealthStatusType:
        """Convert heartbeat status to overall monitor health status."""
        if self == MonitorHeartbeatStatusType.ACTIVE:
            return MonitorHealthStatusType.HEALTHY
        elif self == MonitorHeartbeatStatusType.STALE:
            return MonitorHealthStatusType.WARNING
        else:  # DEAD
            return MonitorHealthStatusType.ERROR


class ApiSourceHealthStatusType(LabeledEnum):
    """
    Health status for individual API sources used by monitors.
    """

    HEALTHY = ('Healthy', 'API responding normally with good performance')
    DEGRADED = ('Degraded', 'API responding but with performance issues or occasional failures')
    FAILING = ('Failing', 'API experiencing frequent failures or timeouts')
    UNAVAILABLE = ('Unavailable', 'API completely unresponsive or returning errors')

    @classmethod
    def from_metrics(cls,
                     success_rate: Optional[float] = None,
                     avg_response_time: Optional[float] = None,
                     consecutive_failures: int = 0,
                     total_failures: int = 0,
                     total_requests: int = 0) -> 'ApiSourceHealthStatusType':
        """
        Determine API source health status based on performance metrics.

        Args:
            success_rate: Ratio of successful requests (0.0 to 1.0)
            avg_response_time: Average response time in seconds
            consecutive_failures: Number of consecutive failures
            total_failures: Total number of failures in monitoring window
            total_requests: Total number of requests in monitoring window

        Returns:
            Appropriate API source health status
        """
        # Performance and failure thresholds
        DEGRADED_SUCCESS_RATE_THRESHOLD = 0.95  # Below 95% success rate
        FAILING_SUCCESS_RATE_THRESHOLD = 0.80   # Below 80% success rate
        DEGRADED_RESPONSE_TIME_THRESHOLD = 5.0  # Above 5 seconds average
        FAILING_RESPONSE_TIME_THRESHOLD = 10.0  # Above 10 seconds average
        CONSECUTIVE_FAILURE_WARNING_THRESHOLD = 3  # 3 consecutive failures = degraded
        CONSECUTIVE_FAILURE_ERROR_THRESHOLD = 5    # 5 consecutive failures = failing

        # Handle no data case
        if total_requests == 0:
            return cls.HEALTHY  # Assume healthy until proven otherwise

        # Check consecutive failures first (immediate problems)
        if consecutive_failures >= CONSECUTIVE_FAILURE_ERROR_THRESHOLD:
            return cls.FAILING
        elif consecutive_failures >= CONSECUTIVE_FAILURE_WARNING_THRESHOLD:
            return cls.DEGRADED

        # Calculate success rate if not provided
        if success_rate is None and total_requests > 0:
            success_rate = (total_requests - total_failures) / total_requests

        # Check success rate thresholds
        if success_rate is not None:
            if success_rate < FAILING_SUCCESS_RATE_THRESHOLD:
                return cls.FAILING
            elif success_rate < DEGRADED_SUCCESS_RATE_THRESHOLD:
                return cls.DEGRADED

        # Check response time thresholds
        if avg_response_time is not None:
            if avg_response_time > FAILING_RESPONSE_TIME_THRESHOLD:
                return cls.FAILING
            elif avg_response_time > DEGRADED_RESPONSE_TIME_THRESHOLD:
                return cls.DEGRADED

        return cls.HEALTHY

    def to_monitor_health_status(self) -> MonitorHealthStatusType:
        """Convert API source status to monitor health status contribution."""
        if self == ApiSourceHealthStatusType.HEALTHY:
            return MonitorHealthStatusType.HEALTHY
        elif self == ApiSourceHealthStatusType.DEGRADED:
            return MonitorHealthStatusType.WARNING
        else:  # FAILING or UNAVAILABLE
            return MonitorHealthStatusType.ERROR


class MonitorHealthAggregationRule(LabeledEnum):
    """
    Rules for aggregating multiple health status inputs into overall monitor health.
    """

    # Heartbeat-only monitors (no API dependencies)
    HEARTBEAT_ONLY = ('Heartbeat Only', 'Health determined solely by heartbeat status')

    # API-dependent monitors
    ALL_SOURCES_HEALTHY = ('All Sources Healthy', 'All API sources must be healthy for overall health')
    MAJORITY_SOURCES_HEALTHY = ('Majority Sources Healthy', 'Majority of API sources must be healthy')
    ANY_SOURCE_HEALTHY = ('Any Source Healthy', 'At least one API source must be healthy')

    # Custom weighting (for future enhancement)
    WEIGHTED_AVERAGE = ('Weighted Average', 'Weighted average of source health with custom priorities')

    @classmethod
    def default_for_api_count(cls, api_source_count: int) -> 'MonitorHealthAggregationRule':
        """
        Determine appropriate aggregation rule based on number of API sources.

        Args:
            api_source_count: Number of API sources the monitor depends on

        Returns:
            Recommended aggregation rule
        """
        if api_source_count == 0:
            return cls.HEARTBEAT_ONLY
        elif api_source_count == 1:
            return cls.ALL_SOURCES_HEALTHY  # Single source must be healthy
        elif api_source_count <= 3:
            return cls.MAJORITY_SOURCES_HEALTHY  # Most sources must be healthy
        else:
            return cls.ANY_SOURCE_HEALTHY  # At least one source must work


class MonitorLabelingPattern(LabeledEnum):
    """
    Standardized patterns for monitor identification and labeling.
    """

    # Technical ID patterns (kebab-case)
    FEATURE_MONITOR = ('Feature Monitor', 'Pattern: {feature}-monitor (e.g., weather-monitor)')
    SERVICE_MONITOR = ('Service Monitor', 'Pattern: {service}-monitor (e.g., alert-monitor)')
    INTEGRATION_MONITOR = ('Integration Monitor', 'Pattern: {integration}-monitor (e.g., zoneminder-monitor)')

    # User-friendly label patterns
    FEATURE_UPDATES = ('Feature Updates', 'Pattern: {Feature} Updates (e.g., Weather Updates)')
    SERVICE_PROCESSING = ('Service Processing', 'Pattern: {Service} Processing (e.g., Alert Processing)')
    INTEGRATION_HEALTH = ('Integration Health', 'Pattern: {Integration} Health (e.g., ZoneMinder Health)')

    # API source naming patterns
    EXTERNAL_API = ('External API', 'Pattern: {Provider} API (e.g., OpenWeatherMap API)')
    INTERNAL_SERVICE = ('Internal Service', 'Pattern: {Service} Service (e.g., Home Assistant Service)')

    @classmethod
    def generate_monitor_id(cls, feature_name: str, pattern: 'MonitorLabelingPattern' = None) -> str:
        """
        Generate standardized monitor ID from feature name.

        Args:
            feature_name: Name of the feature/service (e.g., 'weather', 'alert')
            pattern: Labeling pattern to use (defaults to FEATURE_MONITOR)

        Returns:
            Standardized monitor ID in kebab-case
        """
        if pattern is None:
            pattern = cls.FEATURE_MONITOR

        # Convert to kebab-case
        normalized_name = feature_name.lower().replace(' ', '-').replace('_', '-')

        if pattern in (cls.FEATURE_MONITOR, cls.SERVICE_MONITOR, cls.INTEGRATION_MONITOR):
            return f"{normalized_name}-monitor"
        else:
            return normalized_name

    @classmethod
    def generate_monitor_label(cls, feature_name: str, pattern: 'MonitorLabelingPattern' = None) -> str:
        """
        Generate user-friendly monitor label from feature name.

        Args:
            feature_name: Name of the feature/service (e.g., 'weather', 'alert')
            pattern: Labeling pattern to use (defaults to FEATURE_UPDATES)

        Returns:
            User-friendly monitor label
        """
        if pattern is None:
            pattern = cls.FEATURE_UPDATES

        # Convert to title case
        normalized_name = feature_name.replace('-', ' ').replace('_', ' ').title()

        if pattern == cls.FEATURE_UPDATES:
            return f"{normalized_name} Updates"
        elif pattern == cls.SERVICE_PROCESSING:
            return f"{normalized_name} Processing"
        elif pattern == cls.INTEGRATION_HEALTH:
            return f"{normalized_name} Health"
        else:
            return normalized_name

    @classmethod
    def generate_api_source_label(cls, provider_name: str, pattern: 'MonitorLabelingPattern' = None) -> str:
        """
        Generate standardized API source label.

        Args:
            provider_name: Name of the API provider (e.g., 'OpenWeatherMap', 'Home Assistant')
            pattern: Labeling pattern to use (defaults to EXTERNAL_API)

        Returns:
            Standardized API source label
        """
        if pattern is None:
            pattern = cls.EXTERNAL_API

        if pattern == cls.EXTERNAL_API:
            return f"{provider_name} API"
        elif pattern == cls.INTERNAL_SERVICE:
            return f"{provider_name} Service"
        else:
            return provider_name


# Legacy support - for backwards compatibility with existing integrations code
HealthStatusType = ApiSourceHealthStatusType