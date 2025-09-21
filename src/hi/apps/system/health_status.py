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
    last_update    : datetime                # When did provider last report
    heartbeat      : Optional[datetime]  = None
    last_message   : Optional[str]       = None
    error_count    : int                 = 0
    expected_heartbeat_interval_secs : Optional[int] = None  # Expected polling interval for dynamic heartbeat thresholds

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

    def _get_heartbeat_thresholds(self) -> tuple[int, int]:
        if self.expected_heartbeat_interval_secs:
            # Dynamic thresholds: 1.5x interval for active, 3x for stale
            active_threshold = int(self.expected_heartbeat_interval_secs * 1.5)
            stale_threshold = int(self.expected_heartbeat_interval_secs * 3.0)
        else:
            # Fixed thresholds for backward compatibility
            active_threshold = 30
            stale_threshold = 300  # 5 minutes

        return active_threshold, stale_threshold

    @property
    def heartbeat_status_text(self) -> str:
        if not self.heartbeat:
            return "Unknown"

        age = self.heartbeat_age_seconds
        if age is None:
            return "Unknown"

        active_threshold, stale_threshold = self._get_heartbeat_thresholds()

        if age < active_threshold:
            return "Active"
        elif age < stale_threshold:
            return "Stale"
        else:
            return "Dead"

    @property
    def heartbeat_css_class(self) -> str:
        if not self.heartbeat:
            return "heartbeat-dead"

        age = self.heartbeat_age_seconds
        if age is None:
            return "heartbeat-dead"

        active_threshold, stale_threshold = self._get_heartbeat_thresholds()

        if age < active_threshold:
            return "heartbeat-healthy"
        elif age < stale_threshold:
            return "heartbeat-stale"
        else:
            return "heartbeat-dead"

    @property
    def heartbeat_text_class(self) -> str:
        if not self.heartbeat:
            return "text-error-custom"

        age = self.heartbeat_age_seconds
        if age is None:
            return "text-error-custom"

        active_threshold, stale_threshold = self._get_heartbeat_thresholds()

        if age < active_threshold:
            return "text-success-custom"
        elif age < stale_threshold:
            return "text-warning-custom"
        else:
            return "text-error-custom"

    @property
    def status_badge_class(self) -> str:
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
    def border_color_class(self) -> str:
        if self.status.is_healthy:
            return "border-healthy"
        elif self.status.is_warning:
            return "border-warning"
        elif self.status.is_info:
            return "border-info"
        elif self.status.is_critical:
            return "border-error"
        elif self.status.is_error:
            return "bordder-error"
        else:  # UNKNOWN
            return "border-unknown"
        
    @property
    def status_summary_message(self) -> str:
        if self.is_healthy:
            if self.heartbeat:
                return "Is operating normally and heartbeat is active."
            else:
                return "Is operating normally."
        elif self.is_critical:
            return "Requires immediate attention."
        else:
            return "Has encountered temporary issues. The problem may resolve automatically."


