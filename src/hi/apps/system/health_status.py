from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from .api_health import ApiHealthStatus
from .enums import HealthStatusType, ApiHealthStatusType


@dataclass
class HealthStatus:
    """Health status tracking for PeriodicMonitor instances."""

    status         : HealthStatusType
    last_check     : datetime
    heartbeat      : Optional[datetime]  = None
    error_message  : Optional[str]       = None
    error_count    : int                 = 0

    # API source health (new requirement)
    api_sources: List[ApiHealthStatus] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatusType.HEALTHY

    @property
    def is_error(self) -> bool:
        return self.status.is_error

    @property
    def is_critical(self) -> bool:
        return self.status.requires_attention

    @property
    def status_display(self) -> str:
        return self.status.label

    @property
    def overall_api_health_status(self) -> ApiHealthStatusType:
        if not self.api_sources:
            return ApiHealthStatusType.HEALTHY

        # If any API source is unavailable or failing, overall status reflects worst case
        worst_status = ApiHealthStatusType.HEALTHY
        for api_source in self.api_sources:
            if api_source.status == ApiHealthStatusType.UNAVAILABLE:
                return ApiHealthStatusType.UNAVAILABLE
            elif api_source.status == ApiHealthStatusType.FAILING:
                worst_status = ApiHealthStatusType.FAILING
            elif ( api_source.status == ApiHealthStatusType.DEGRADED
                   and worst_status == ApiHealthStatusType.HEALTHY ):
                worst_status = ApiHealthStatusType.DEGRADED

        return worst_status

    def get_api_source(self, source_id: str) -> Optional[ApiHealthStatus]:
        """Get an API source by its ID."""
        for api_source in self.api_sources:
            if api_source.source_id == source_id:
                return api_source
        return None

    def add_or_update_api_source(self, api_source: ApiHealthStatus) -> None:
        """Add a new API source or update an existing one."""
        existing = self.get_api_source(api_source.source_id)
        if existing:
            # Update existing source
            existing.source_name = api_source.source_name
            existing.status = api_source.status
            existing.last_success = api_source.last_success
            existing.total_calls = api_source.total_calls
            existing.total_failures = api_source.total_failures
            existing.consecutive_failures = api_source.consecutive_failures
            existing.average_response_time = api_source.average_response_time
            existing.last_response_time = api_source.last_response_time
        else:
            # Add new source
            self.api_sources.append(api_source)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        import hi.apps.common.datetimeproxy as datetimeproxy

        result = {
            'status': self.status.value,
            'status_display': self.status_display,
            'last_check': self.last_check,
            'error_message': self.error_message,
            'error_count': self.error_count,
            'is_healthy': self.is_healthy,
            'is_error': self.is_error,
            'is_critical': self.is_critical,
            'overall_api_health_status': self.overall_api_health_status.value,
            'api_sources': [api_source.to_dict() for api_source in self.api_sources],
        }

        # Include heartbeat details if present
        if self.heartbeat is not None:
            heartbeat_age = (datetimeproxy.now() - self.heartbeat).total_seconds()
            result['heartbeat'] = self.heartbeat
            result['heartbeat_age_seconds'] = heartbeat_age

        return result

    @property
    def has_api_sources(self) -> bool:
        return len(self.api_sources) > 0

    @property
    def heartbeat_age_seconds(self) -> Optional[int]:
        if not self.heartbeat:
            return None
        import hi.apps.common.datetimeproxy as datetimeproxy
        return int((datetimeproxy.now() - self.heartbeat).total_seconds())

    @property
    def heartbeat_status_text(self) -> str:
        """Get heartbeat status description."""
        if not self.heartbeat:
            return "Unknown"

        age = self.heartbeat_age_seconds
        if age is None:
            return "Unknown"
        elif age < 30:
            return "Active"
        elif age < 300:  # 5 minutes
            return "Stale"
        else:
            return "Dead"

    @property
    def heartbeat_css_class(self) -> str:
        """Get CSS class for heartbeat indicator."""
        if not self.heartbeat:
            return "heartbeat-dead"

        age = self.heartbeat_age_seconds
        if age is None:
            return "heartbeat-dead"
        elif age < 30:
            return "heartbeat-healthy"
        elif age < 300:  # 5 minutes
            return "heartbeat-stale"
        else:
            return "heartbeat-dead"

    @property
    def heartbeat_text_class(self) -> str:
        """Get text color class for heartbeat status."""
        if not self.heartbeat:
            return "text-error-custom"

        age = self.heartbeat_age_seconds
        if age is None:
            return "text-error-custom"
        elif age < 30:
            return "text-success-custom"
        elif age < 300:  # 5 minutes
            return "text-warning-custom"
        else:
            return "text-error-custom"

    @property
    def status_badge_class(self) -> str:
        """Get Bootstrap badge class for overall status."""
        return {
            HealthStatusType.HEALTHY: "monitor-status-healthy",
            HealthStatusType.WARNING: "monitor-status-warning",
            HealthStatusType.ERROR: "monitor-status-error"
        }[self.status]

    @property
    def status_alert_class(self) -> str:
        """Get alert class for status summary."""
        if self.is_healthy:
            return "alert-success"
        elif self.is_critical:
            return "alert-danger"
        else:
            return "alert-warning"

    @property
    def status_icon(self) -> str:
        """Get Font Awesome icon for status."""
        return {
            HealthStatusType.HEALTHY: "check-circle",
            HealthStatusType.WARNING: "warning",
            HealthStatusType.ERROR: "warning"
        }[self.status]

    @property
    def status_summary_message(self) -> str:
        """Get appropriate status summary message."""
        if self.is_healthy:
            if self.has_api_sources:
                return "Is operating normally. All API sources are responding correctly and heartbeat is active."
            else:
                return "Is operating normally and heartbeat is active."
        elif self.is_critical:
            return "Requires immediate attention. Please check the configuration settings and ensure external services are accessible."
        else:
            return "Has encountered temporary issues. The problem may resolve automatically, but monitoring is recommended."


