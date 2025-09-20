from typing import Optional

from hi.apps.common.enums import LabeledEnum


class HealthStatusType(LabeledEnum):

    UNKNOWN            = ( 'Unknown',
                           'No health status was set')
    HEALTHY            = ( 'Healthy',
                           'Operating normally with all dependencies healthy')
    WARNING            = ( 'Warning',
                           'Temporary issues detected or degraded performance')
    ERROR              = ( 'Error',
                           'Critical failures requiring attention or not responding')
    DISABLED           = ( 'Disabled',
                           'Provider has been manually disabled' )

    @property
    def is_healthy(self) -> bool:
        return bool( self in (
            HealthStatusType.HEALTHY,
        ))

    @property
    def is_warning(self) -> bool:
        return bool( self in (
            HealthStatusType.WARNING,
        ))

    @property
    def is_info(self) -> bool:
        return bool( self in (
            HealthStatusType.DISABLED,
        ))
    
    @property
    def is_error(self) -> bool:
        return bool( self in (
            HealthStatusType.ERROR,
        ))

    @property
    def is_critical(self) -> bool:
        return bool( self in (
            HealthStatusType.ERROR,
        ))

    @property
    def is_operational(self) -> bool:
        return bool( self in (
            HealthStatusType.HEALTHY,
            HealthStatusType.WARNING,
        ))

    @property
    def requires_attention(self) -> bool:
        return self.is_error

    @classmethod
    def from_priority(cls, priority: int) -> 'HealthStatusType':
        """
        Map priority levels to health status.
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
        if self.is_critical:  # ERROR
            return 1
        elif self.is_warning:  # WARNING
            return 2
        elif self.is_info:  # DISABLED
            return 3
        elif self == HealthStatusType.HEALTHY:
            return 4
        else:  # UNKNOWN
            return 5


class HeartbeatStatusType(LabeledEnum):
    """
    Heartbeat-specific health status based on last communication time.
    """

    ACTIVE = ('Active', 'Responding within expected timeframe (< 30 seconds)')
    STALE = ('Stale', 'Response delayed but within tolerance (30 seconds - 5 minutes)')
    DEAD = ('Dead', 'Not responding for extended period (> 5 minutes)')

    @classmethod
    def from_last_heartbeat(cls, seconds_since_last: Optional[float]) -> 'HeartbeatStatusType':
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

    def to_health_status(self) -> HealthStatusType:
        if self == HeartbeatStatusType.ACTIVE:
            return HealthStatusType.HEALTHY
        elif self == HeartbeatStatusType.STALE:
            return HealthStatusType.WARNING
        else:  # DEAD
            return HealthStatusType.ERROR

        
class ApiCallStatusType(LabeledEnum):

    UNKNOWN    = ('Unknown'   , '')
    SUCCESS    = ('Success'   , '')
    EXCEPTION  = ('Failure'   , '')

    @property
    def is_success(self):
        return bool( self in [ ApiCallStatusType.SUCCESS ] )

    @property
    def is_failure(self):
        return bool( self in [ ApiCallStatusType.EXCEPTION ] )

    
class ApiHealthStatusType(LabeledEnum):

    UNKNOWN     = ('Unknown'     , 'No health status was set')
    HEALTHY     = ('Healthy'     , 'API responding normally with good performance')
    DEGRADED    = ('Degraded'    , 'API responding but performance or occasional issues')
    FAILING     = ('Failing'     , 'API experiencing frequent failures or timeouts')
    UNAVAILABLE = ('Unavailable' , 'API completely unresponsive or returning errors')

    @classmethod
    def from_metrics(cls,
                     success_rate: Optional[float] = None,
                     avg_response_time: Optional[float] = None,
                     consecutive_failures: int = 0,
                     total_failures: int = 0,
                     total_requests: int = 0) -> 'ApiHealthStatusType':
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

    def to_health_status(self) -> HealthStatusType:
        """Convert API source status to health status contribution."""
        if self == ApiHealthStatusType.HEALTHY:
            return HealthStatusType.HEALTHY
        elif self == ApiHealthStatusType.DEGRADED:
            return HealthStatusType.WARNING
        else:  # FAILING or UNAVAILABLE
            return HealthStatusType.ERROR


class HealthAggregationRule(LabeledEnum):
    """
    Rules for aggregating multiple health status inputs into overall health.
    """

    # Heartbeat-only (no API dependencies)
    HEARTBEAT_ONLY = ('Heartbeat Only', 'Health determined solely by heartbeat status')

    # API-dependent
    ALL_SOURCES_HEALTHY = ('All Sources Healthy', 'All API sources must be healthy for overall health')
    MAJORITY_SOURCES_HEALTHY = ('Majority Sources Healthy', 'Majority of API sources must be healthy')
    ANY_SOURCE_HEALTHY = ('Any Source Healthy', 'At least one API source must be healthy')

    # Custom weighting (for future enhancement)
    WEIGHTED_AVERAGE = ('Weighted Average', 'Weighted average of source health with custom priorities')

    @classmethod
    def default_for_api_count(cls, api_provider_count: int) -> 'HealthAggregationRule':
        """
        Determine appropriate aggregation rule based on number of API sources.

        Args:
            api_provider_count: Number of API sources this depends on

        Returns:
            Recommended aggregation rule
        """
        if api_provider_count == 0:
            return cls.HEARTBEAT_ONLY
        elif api_provider_count == 1:
            return cls.ALL_SOURCES_HEALTHY  # Single source must be healthy
        elif api_provider_count <= 3:
            return cls.MAJORITY_SOURCES_HEALTHY  # Most sources must be healthy
        else:
            return cls.ANY_SOURCE_HEALTHY  # At least one source must work
