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
    source_name: str          # User-friendly display name
    source_id: str           # Technical identifier

    # Health status
    status: ApiHealthStatusType
    last_success: Optional[datetime] = None

    # Performance metrics
    total_calls: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    average_response_time: Optional[float] = None
    last_response_time: Optional[float] = None

    def record_api_call( self, api_call_context : ApiCallContext ):
        self.total_calls += 1
        if api_call_context.status.is_success:
            self.last_success = datetimeproxy.now()
            self.consecutive_failures = 0
            self.status = ApiHealthStatusType.HEALTHY
        else:
            self.total_failures += 1
            self.consecutive_failures += 1

            self.status = ApiHealthStatusType.from_metrics(
                consecutive_failures = self.consecutive_failures,
                total_failures = self.total_failures,
                total_requests = self.total_calls,
                avg_response_time = self.average_response_time
            )

        if api_call_context.duration is not None:
            self.last_response_time = api_call_context.duration
            if self.average_response_time is None:
                self.average_response_time = api_call_context.duration
            else:
                # Simple moving average (can be enhanced with more sophisticated algorithms)
                self.average_response_time = (( self.average_response_time * 0.8 )
                                              + ( api_call_context.duration * 0.2  ))
        return
    
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
    def status_css_class(self) -> str:
        """Get CSS class for status styling."""
        return {
            ApiHealthStatusType.HEALTHY: "success",
            ApiHealthStatusType.DEGRADED: "warning",
            ApiHealthStatusType.FAILING: "error",
            ApiHealthStatusType.UNAVAILABLE: "error"
        }[self.status]

    @property
    def status_badge_class(self) -> str:
        """Get Bootstrap badge class for status."""
        return {
            ApiHealthStatusType.HEALTHY: "badge-success",
            ApiHealthStatusType.DEGRADED: "monitor-status-warning",
            ApiHealthStatusType.FAILING: "monitor-status-error",
            ApiHealthStatusType.UNAVAILABLE: "monitor-status-error"
        }[self.status]

    @property
    def status_icon(self) -> str:
        """Get Font Awesome icon for status."""
        return {
            ApiHealthStatusType.HEALTHY: "check-circle",
            ApiHealthStatusType.DEGRADED: "warning",
            ApiHealthStatusType.FAILING: "warning",
            ApiHealthStatusType.UNAVAILABLE: "warning"
        }[self.status]

    @property
    def border_color_class(self) -> str:
        """Get border color class for API source section."""
        return {
            ApiHealthStatusType.HEALTHY: "api-source-healthy",
            ApiHealthStatusType.DEGRADED: "api-source-warning",
            ApiHealthStatusType.FAILING: "api-source-error",
            ApiHealthStatusType.UNAVAILABLE: "api-source-error"
        }[self.status]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'source_name': self.source_name,
            'source_id': self.source_id,
            'status': self.status.value,
            'status_display': self.status.label,
            'last_success': self.last_success,
            'total_calls': self.total_calls,
            'total_failures': self.total_failures,
            'consecutive_failures': self.consecutive_failures,
            'average_response_time': self.average_response_time,
            'last_response_time': self.last_response_time,
            'is_healthy': self.is_healthy,
            'failure_rate': self.failure_rate,
        }
