from datetime import timedelta
from django.shortcuts import render
from django.views.generic import View

from hi.apps.monitor.transient_models import MonitorHealthStatus, ApiSourceHealth
from hi.apps.monitor.enums import MonitorHealthStatusType, ApiSourceHealthStatusType
import hi.apps.common.datetimeproxy as datetimeproxy


class TestUiMonitorHomeView(View):

    def get(self, request, *args, **kwargs):
        context = {
            'app_name': 'monitor',
        }
        return render(request, 'monitor/tests/ui/home.html', context)


class TestUiMonitorHealthStatusView(View):
    """
    View for testing monitor health status modals with various synthetic data scenarios.
    Renders the template directly without modifying system state.
    """

    def get(self, request, *args, **kwargs):
        monitor_type = kwargs.get('monitor_type', 'zoneminder')

        # Create synthetic health status based on type
        health_status = self._create_synthetic_health_status(monitor_type)
        monitor_label = self._get_monitor_label(monitor_type)

        # Render template directly with synthetic data
        context = {
            'health_status': health_status,
            'monitor_label': monitor_label,
            'monitor_id': monitor_type,
        }
        return render(request, 'monitor/modals/monitor_health_status.html', context)

    def _get_monitor_label(self, monitor_id: str) -> str:
        """Get display label for monitor based on ID."""
        monitor_labels = {
            'zoneminder': 'ZoneMinder Integration',
            'hass': 'Home Assistant Integration',
            'weather': 'Weather Updates Monitor',
            'alert': 'Alert Processing Monitor',
            'security': 'Security Monitor',
            'notify': 'Notification Monitor',
        }
        return monitor_labels.get(monitor_id, f'Monitor {monitor_id}')

    def _create_synthetic_health_status(self, monitor_type: str) -> MonitorHealthStatus:
        """Create synthetic health status data for UI testing."""
        now = datetimeproxy.now()

        if monitor_type == 'zoneminder':
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

        elif monitor_type == 'weather':
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
                        average_response_time=None,
                        last_response_time=None
                    )
                ]
            )

        elif monitor_type == 'alert':
            return MonitorHealthStatus(
                status=MonitorHealthStatusType.ERROR,
                last_check=now,
                monitor_heartbeat=now - timedelta(minutes=65),
                error_message="Monitor has stopped responding - requires restart",
                error_count=15,
                api_sources=[]
            )

        else:
            # Default healthy monitor
            return MonitorHealthStatus(
                status=MonitorHealthStatusType.HEALTHY,
                last_check=now,
                monitor_heartbeat=now,
                api_sources=[]
            )
