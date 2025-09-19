from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from hi.apps.control.transient_models import ControllerData
from hi.apps.common.svg_models import SvgIconItem
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse
from .enums import MonitorHealthStatusType, ApiSourceHealthStatusType

# For backwards compatibility
HealthStatusType = ApiSourceHealthStatusType


@dataclass
class EntityStateStatusData:
    entity_state          : EntityState
    sensor_response_list  : List[ SensorResponse ]  # Not grouped by sensor, but ordered by response time
    controller_data_list  : List[ ControllerData ]

    @property
    def latest_sensor_response(self):
        if self.sensor_response_list:
            return self.sensor_response_list[0]
        return None

    
@dataclass
class EntityStatusData:
    entity                         : Entity
    entity_state_status_data_list  : List[ EntityStateStatusData ]
    entity_for_video               : Entity                        = None
    display_only_svg_icon_item     : SvgIconItem                   = None

    def __post_init__(self):
        if not self.entity_for_video:
            self.entity_for_video = self.entity
        return
    
    def to_template_context(self):
        context = {
            'entity': self.entity,
            'entity_state_status_data_list': self.entity_state_status_data_list,
            'entity_for_video': self.entity_for_video,
            'display_only_svg_icon_item': self.display_only_svg_icon_item,
        }
        return context


@dataclass
class ApiSourceHealth:
    """Health status tracking for individual API sources within a monitor."""

    # Identification
    source_name: str          # User-friendly display name
    source_id: str           # Technical identifier

    # Health status
    status: ApiSourceHealthStatusType
    last_success: Optional[datetime] = None

    # Performance metrics
    total_calls: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    average_response_time: Optional[float] = None
    last_response_time: Optional[float] = None

    @property
    def is_healthy(self) -> bool:
        """Check if this API source is healthy."""
        return self.status == ApiSourceHealthStatusType.HEALTHY

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
            ApiSourceHealthStatusType.HEALTHY: "success",
            ApiSourceHealthStatusType.DEGRADED: "warning",
            ApiSourceHealthStatusType.FAILING: "error",
            ApiSourceHealthStatusType.UNAVAILABLE: "error"
        }[self.status]

    @property
    def status_badge_class(self) -> str:
        """Get Bootstrap badge class for status."""
        return {
            ApiSourceHealthStatusType.HEALTHY: "badge-success",
            ApiSourceHealthStatusType.DEGRADED: "monitor-status-warning",
            ApiSourceHealthStatusType.FAILING: "monitor-status-error",
            ApiSourceHealthStatusType.UNAVAILABLE: "monitor-status-error"
        }[self.status]

    @property
    def status_icon(self) -> str:
        """Get Font Awesome icon for status."""
        return {
            ApiSourceHealthStatusType.HEALTHY: "check-circle",
            ApiSourceHealthStatusType.DEGRADED: "warning",
            ApiSourceHealthStatusType.FAILING: "warning",
            ApiSourceHealthStatusType.UNAVAILABLE: "warning"
        }[self.status]

    @property
    def border_color_class(self) -> str:
        """Get border color class for API source section."""
        return {
            ApiSourceHealthStatusType.HEALTHY: "api-source-healthy",
            ApiSourceHealthStatusType.DEGRADED: "api-source-warning",
            ApiSourceHealthStatusType.FAILING: "api-source-error",
            ApiSourceHealthStatusType.UNAVAILABLE: "api-source-error"
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


@dataclass
class MonitorHealthStatus:
    """Health status tracking for PeriodicMonitor instances."""

    # Core monitor health
    status: MonitorHealthStatusType
    last_check: datetime
    error_message: Optional[str] = None
    error_count: int = 0

    # Monitor lifecycle
    monitor_heartbeat: Optional[datetime] = None

    # API source health (new requirement)
    api_sources: List[ApiSourceHealth] = field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        """Check if the monitor is healthy."""
        return self.status == MonitorHealthStatusType.HEALTHY

    @property
    def is_error(self) -> bool:
        """Check if the monitor has an error condition."""
        return self.status.is_error

    @property
    def is_critical(self) -> bool:
        """Check if the monitor has a critical error."""
        return self.status.requires_attention

    @property
    def status_display(self) -> str:
        """Get the display label for the status."""
        return self.status.label

    @property
    def overall_api_health_status(self) -> ApiSourceHealthStatusType:
        """Aggregate health status across all API sources."""
        if not self.api_sources:
            return ApiSourceHealthStatusType.HEALTHY

        # If any API source is unavailable or failing, overall status reflects worst case
        worst_status = ApiSourceHealthStatusType.HEALTHY
        for api_source in self.api_sources:
            if api_source.status == ApiSourceHealthStatusType.UNAVAILABLE:
                return ApiSourceHealthStatusType.UNAVAILABLE
            elif api_source.status == ApiSourceHealthStatusType.FAILING:
                worst_status = ApiSourceHealthStatusType.FAILING
            elif api_source.status == ApiSourceHealthStatusType.DEGRADED and worst_status == ApiSourceHealthStatusType.HEALTHY:
                worst_status = ApiSourceHealthStatusType.DEGRADED

        return worst_status

    def get_api_source(self, source_id: str) -> Optional[ApiSourceHealth]:
        """Get an API source by its ID."""
        for api_source in self.api_sources:
            if api_source.source_id == source_id:
                return api_source
        return None

    def add_or_update_api_source(self, api_source: ApiSourceHealth) -> None:
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

        # Include monitor heartbeat details if present
        if self.monitor_heartbeat is not None:
            heartbeat_age = (datetimeproxy.now() - self.monitor_heartbeat).total_seconds()
            result['monitor_heartbeat'] = self.monitor_heartbeat
            result['monitor_heartbeat_age_seconds'] = heartbeat_age

        return result

    @property
    def has_api_sources(self) -> bool:
        """Check if monitor has API sources to display."""
        return len(self.api_sources) > 0

    @property
    def monitor_heartbeat_age_seconds(self) -> Optional[int]:
        """Calculate age of monitor heartbeat in seconds."""
        if not self.monitor_heartbeat:
            return None
        import hi.apps.common.datetimeproxy as datetimeproxy
        return int((datetimeproxy.now() - self.monitor_heartbeat).total_seconds())

    @property
    def heartbeat_status_text(self) -> str:
        """Get heartbeat status description."""
        if not self.monitor_heartbeat:
            return "Unknown"

        age = self.monitor_heartbeat_age_seconds
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
        if not self.monitor_heartbeat:
            return "heartbeat-dead"

        age = self.monitor_heartbeat_age_seconds
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
        if not self.monitor_heartbeat:
            return "text-error-custom"

        age = self.monitor_heartbeat_age_seconds
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
            MonitorHealthStatusType.HEALTHY: "monitor-status-healthy",
            MonitorHealthStatusType.WARNING: "monitor-status-warning",
            MonitorHealthStatusType.ERROR: "monitor-status-error"
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
            MonitorHealthStatusType.HEALTHY: "check-circle",
            MonitorHealthStatusType.WARNING: "warning",
            MonitorHealthStatusType.ERROR: "warning"
        }[self.status]

    @property
    def status_summary_message(self) -> str:
        """Get appropriate status summary message."""
        if self.is_healthy:
            if self.has_api_sources:
                return "This monitor is operating normally. All API sources are responding correctly and heartbeat is active."
            else:
                return "This monitor is operating normally and heartbeat is active."
        elif self.is_critical:
            return "This monitor requires immediate attention. Please check the configuration settings and ensure external services are accessible."
        else:
            return "This monitor has encountered temporary issues. The problem may resolve automatically, but monitoring is recommended."


