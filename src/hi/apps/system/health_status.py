from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from .enums import HealthStatusType


@dataclass
class HealthStatus:
    """Health status tracking for PeriodicMonitor instances."""

    # Identification
    provider_name   : str                    # User-friendly display name
    provider_id     : str                    # Technical identifier
    
    status         : HealthStatusType        # When did we last check
    last_check     : datetime                # When did provider last report
    heartbeat      : Optional[datetime]  = None
    error_message  : Optional[str]       = None
    error_count    : int                 = 0

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatusType.HEALTHY

    @property
    def is_error(self) -> bool:
        return self.status.is_error

    @property
    def is_critical(self) -> bool:
        return self.status.is_critical

    @property
    def status_display(self) -> str:
        return self.status.label

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
        if self.status.is_healthy:
            return "monitor-status-healthy"
        elif self.status.is_warning:
            return "monitor-status-warning"
        elif self.status.is_info:
            return "monitor-status-info"
        elif self.status.is_critical:
            return "monitor-status-critical"
        elif self.status.is_error:
            return "monitor-status-error"
        else:  # UNKNOWN
            return "monitor-status-unknown"

    @property
    def status_alert_class(self) -> str:
        """Get alert class for status summary."""
        if self.is_healthy:
            return "alert-success"
        elif self.status.is_info:
            return "alert-info"
        elif self.is_critical:
            return "alert-danger"
        else:
            return "alert-warning"

    @property
    def status_icon(self) -> str:
        """Get Font Awesome icon for status."""
        if self.status.is_healthy:
            return "check-circle"
        elif self.status.is_warning:
            return "warning"
        elif self.status.is_info:
            return "info-circle"
        elif self.status.is_critical:
            return "times-circle"
        elif self.status.is_error:
            return "exclamation-circle"
        else:  # UNKNOWN
            return "question-circle"

    @property
    def status_summary_message(self) -> str:
        """Get appropriate status summary message."""
        if self.is_healthy:
            return "Is operating normally and heartbeat is active."
        elif self.is_critical:
            return "Requires immediate attention. Please check the configuration settings and ensure external services are accessible."
        else:
            return "Has encountered temporary issues. The problem may resolve automatically, but monitoring is recommended."


