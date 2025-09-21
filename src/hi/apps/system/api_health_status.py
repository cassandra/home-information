from dataclasses import dataclass
from typing import Optional
from datetime import datetime

import hi.apps.common.datetimeproxy as datetimeproxy
from .enums import ApiCallStatusType, ApiHealthStatusType


@dataclass
class ApiCallContext:
    operation_name  : str
    start_time      : float   # from time.time()   
    status          : ApiCallStatusType       = ApiCallStatusType.UNKNOWN,
    duration        : float                   = None
    error           : str                     = None

    
@dataclass
class ApiHealthStatus:
    """Health status tracking for individual API sources."""

    # Identification
    provider_name          : str          # User-friendly display name
    provider_id            : str          # Technical identifier

    status                 : ApiHealthStatusType
    last_success           : Optional[datetime]  = None
    total_calls            : int                 = 0
    total_failures         : int                 = 0
    consecutive_failures   : int                 = 0
    average_response_time  : Optional[float]     = None
    last_response_time     : Optional[float]     = None
    cache_hits             : int                 = 0
    cache_misses           : int                 = 0
    last_error_message     : str                 = None
    
    def record_api_call( self, api_call_context : ApiCallContext ):
        self.total_calls += 1
        if api_call_context.status.is_success:
            self.last_success = datetimeproxy.now()
            self.record_healthy()
        else:
            self.record_error( 'API call failure' )

        if api_call_context.duration is not None:
            self.last_response_time = api_call_context.duration
            if self.average_response_time is None:
                self.average_response_time = api_call_context.duration
            else:
                # Simple moving average (can be enhanced with more sophisticated algorithms)
                self.average_response_time = (( self.average_response_time * 0.8 )
                                              + ( api_call_context.duration * 0.2  ))
        return

    def record_healthy( self ):
        self.status = ApiHealthStatusType.HEALTHY
        self.consecutive_failures = 0
        return
    
    def record_error( self, message : str = None ):
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_error_message = message
        self.status = ApiHealthStatusType.from_metrics(
            consecutive_failures = self.consecutive_failures,
            total_failures = self.total_failures,
            total_requests = self.total_calls,
            avg_response_time = self.average_response_time
        )
        return
    
    def record_cache_hit(self) -> int:
        self.cache_hits += 1
        self.status = ApiHealthStatusType.HEALTHY
        return
    
    def record_cache_miss(self) -> int:
        self.cache_misses += 1
        self.status = ApiHealthStatusType.HEALTHY
        return

    @property
    def cache_hit_rate(self) -> float:
        cache_attempts = self.cache_hits + self.cache_misses
        if cache_attempts < 1:
            return 0.0
        return ( self.cache_hits / cache_attempts )

    @property
    def cache_hit_rate_percent(self) -> float:
        return self.cache_hit_rate * 100.0

    # This happens alongside record_api_call(), record_cache_hit() and record_cache_miss()
    @property
    def is_healthy(self) -> bool:
        """Check if this API source is healthy."""
        return self.status == ApiHealthStatusType.HEALTHY

    @property
    def failure_rate(self) -> float:
        """Calculate the failure rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.total_failures / self.total_calls) * 100.0

    @property
    def success_rate_percentage(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_calls == 0:
            return 100.0
        return ((self.total_calls - self.total_failures) / self.total_calls) * 100

    @property
    def status_display(self) -> str:
        return self.status.label

    @property
    def status_css_class(self) -> str:
        return {
            ApiHealthStatusType.HEALTHY: "success",
            ApiHealthStatusType.DEGRADED: "warning",
            ApiHealthStatusType.UNKNOWN: "warning",
            ApiHealthStatusType.FAILING: "error",
            ApiHealthStatusType.UNAVAILABLE: "error",
            ApiHealthStatusType.DISABLED: "info"
        }[self.status]

    @property
    def status_badge_class(self) -> str:
        return {
            ApiHealthStatusType.UNKNOWN: "monitor-status-unknown",
            ApiHealthStatusType.HEALTHY: "monitor-status-healthy",
            ApiHealthStatusType.DEGRADED: "monitor-status-warning",
            ApiHealthStatusType.FAILING: "monitor-status-error",
            ApiHealthStatusType.UNAVAILABLE: "monitor-status-error",
            ApiHealthStatusType.DISABLED: "monitor-status-info"
        }[self.status]

    @property
    def status_icon(self) -> str:
        return {
            ApiHealthStatusType.HEALTHY: "check-circle",
            ApiHealthStatusType.DEGRADED: "warning",
            ApiHealthStatusType.UNKNOWN: "question-circle",
            ApiHealthStatusType.FAILING: "times-circle",
            ApiHealthStatusType.UNAVAILABLE: "exclamation-circle",
            ApiHealthStatusType.DISABLED: "minus-circle"
        }[self.status]

    @property
    def border_color_class(self) -> str:
        return {
            ApiHealthStatusType.HEALTHY: "api-source-healthy",
            ApiHealthStatusType.DEGRADED: "api-source-warning",
            ApiHealthStatusType.UNKNOWN: "api-source-warning",
            ApiHealthStatusType.FAILING: "api-source-error",
            ApiHealthStatusType.UNAVAILABLE: "api-source-error",
            ApiHealthStatusType.DISABLED: "api-source-info"
        }[self.status]
