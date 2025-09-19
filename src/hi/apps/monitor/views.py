import logging
from datetime import timedelta

from django.http import Http404

from hi.hi_async_view import HiModalView
from hi.apps.monitor.transient_models import MonitorHealthStatus, ApiSourceHealth
from hi.apps.monitor.enums import MonitorHealthStatusType, ApiSourceHealthStatusType
import hi.apps.common.datetimeproxy as datetimeproxy

logger = logging.getLogger(__name__)


class MonitorHealthStatusView(HiModalView):
    """View for displaying monitor health status in a modal."""

    def get_template_name(self) -> str:
        return 'monitor/modals/monitor_health_status.html'

    def get(self, request, *args, **kwargs):
        """Handle GET request for monitor health status."""
        # Get monitor identifier from URL kwargs
        monitor_id = kwargs.get('monitor_id')
        if not monitor_id:
            raise Http404("Monitor ID is required")

        # For Phase 1, we'll create sample data
        # In future phases, this will get actual health status from PeriodicMonitor
        health_status = self._get_sample_health_status(monitor_id)
        monitor_label = self._get_monitor_label(monitor_id)

        context = {
            'health_status': health_status,
            'monitor_label': monitor_label,
            'monitor_id': monitor_id,
        }

        return self.modal_response(request, context)

    def _get_monitor_label(self, monitor_id: str) -> str:
        """Get display label for monitor based on ID."""
        # This will be replaced with actual monitor lookup in future phases
        monitor_labels = {
            'zoneminder': 'ZoneMinder Integration',
            'hass': 'Home Assistant Integration',
            'weather': 'Weather Updates Monitor',
            'alert': 'Alert Processing Monitor',
            'security': 'Security Monitor',
            'notify': 'Notification Monitor',
        }
        return monitor_labels.get(monitor_id, f'Monitor {monitor_id}')

    def _get_sample_health_status(self, monitor_id: str) -> MonitorHealthStatus:
        """Generate sample health status data for different monitor types."""
        now = datetimeproxy.now()

        if monitor_id == 'zoneminder':
            return MonitorHealthStatus(
                status=MonitorHealthStatusType.HEALTHY,
                last_check=now,
                monitor_heartbeat=now,
                api_sources=[
                    ApiSourceHealth(
                        source_name="ZoneMinder API",
                        source_id="zoneminder_api",
                        status=ApiSourceHealthStatusType.HEALTHY,
                        last_success=now,
                        total_calls=1247,
                        total_failures=10,
                        consecutive_failures=0,
                        average_response_time=0.23,
                        last_response_time=0.21
                    )
                ]
            )

        elif monitor_id == 'hass':
            return MonitorHealthStatus(
                status=MonitorHealthStatusType.WARNING,
                last_check=now,
                monitor_heartbeat=now - timedelta(minutes=1),
                error_message="Intermittent connection timeouts detected",
                error_count=3,
                api_sources=[
                    ApiSourceHealth(
                        source_name="Home Assistant API",
                        source_id="hass_api",
                        status=ApiSourceHealthStatusType.DEGRADED,
                        last_success=now - timedelta(minutes=2),
                        total_calls=892,
                        total_failures=78,
                        consecutive_failures=2,
                        average_response_time=0.87,
                        last_response_time=1.45
                    )
                ]
            )

        elif monitor_id == 'weather':
            return MonitorHealthStatus(
                status=MonitorHealthStatusType.WARNING,
                last_check=now,
                monitor_heartbeat=now,
                error_message="Some weather API sources are failing - degraded service",
                api_sources=[
                    ApiSourceHealth(
                        source_name="National Weather Service",
                        source_id="nws_api",
                        status=ApiSourceHealthStatusType.HEALTHY,
                        last_success=now,
                        total_calls=456,
                        total_failures=5,
                        consecutive_failures=0,
                        average_response_time=0.34,
                        last_response_time=0.28
                    ),
                    ApiSourceHealth(
                        source_name="OpenWeatherMap API",
                        source_id="openweather_api",
                        status=ApiSourceHealthStatusType.DEGRADED,
                        last_success=now - timedelta(minutes=2),
                        total_calls=342,
                        total_failures=49,
                        consecutive_failures=3,
                        average_response_time=1.45,
                        last_response_time=2.31
                    ),
                    ApiSourceHealth(
                        source_name="WeatherAPI.com",
                        source_id="weatherapi_com",
                        status=ApiSourceHealthStatusType.HEALTHY,
                        last_success=now - timedelta(seconds=5),
                        total_calls=156,
                        total_failures=0,
                        consecutive_failures=0,
                        average_response_time=0.67,
                        last_response_time=0.52
                    ),
                    ApiSourceHealth(
                        source_name="Weather Underground",
                        source_id="weather_underground",
                        status=ApiSourceHealthStatusType.FAILING,
                        last_success=now - timedelta(hours=1),
                        total_calls=89,
                        total_failures=68,
                        consecutive_failures=15,
                        average_response_time=None,  # Timeout
                        last_response_time=None
                    )
                ]
            )

        elif monitor_id == 'alert':
            return MonitorHealthStatus(
                status=MonitorHealthStatusType.ERROR,
                last_check=now,
                monitor_heartbeat=now - timedelta(minutes=65),
                error_message="Monitor has stopped responding - requires restart",
                error_count=15,
                api_sources=[]  # No external API sources for alert monitor
            )

        else:
            # Default healthy monitor
            return MonitorHealthStatus(
                status=MonitorHealthStatusType.HEALTHY,
                last_check=now,
                monitor_heartbeat=now,
                api_sources=[]
            )
