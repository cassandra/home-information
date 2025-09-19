from datetime import timedelta
from django.shortcuts import render
from django.views.generic import View

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.system.api_health import ApiHealthStatus
from hi.apps.system.enums import HealthStatusType, ApiHealthStatusType
from hi.apps.system.health_status import HealthStatus


class SystemTestUiHomeView(View):

    def get(self, request, *args, **kwargs):
        context = {
            'app_name': 'monitor',
        }
        return render(request, 'system/tests/ui/home.html', context)


class SystemTestUiHealthStatusView(View):
    """
    View for testing health status modals with various synthetic data scenarios.
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
        return render(request, 'system/modals/health_status.html', context)

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

    def _create_synthetic_health_status(self, monitor_type: str) -> HealthStatus:
        """Create synthetic health status data for UI testing."""
        now = datetimeproxy.now()

        if monitor_type == 'zoneminder':
            return HealthStatus(
                status = HealthStatusType.HEALTHY,
                last_check = now,
                heartbeat = now,
                api_sources = [
                    ApiHealthStatus(
                        source_name = "ZoneMinder API",
                        source_id = "zoneminder_api",
                        status = ApiHealthStatusType.HEALTHY,
                        last_success = now,
                        total_calls = 1247,
                        total_failures = 10,
                        consecutive_failures = 0,
                        average_response_time = 0.23,
                        last_response_time = 0.21
                    )
                ]
            )

        elif monitor_type == 'weather':
            return HealthStatus(
                status = HealthStatusType.WARNING,
                last_check = now,
                heartbeat = now,
                error_message = "Some weather API sources are failing - degraded service",
                api_sources = [
                    ApiHealthStatus(
                        source_name = "National Weather Service",
                        source_id = "nws_api",
                        status = ApiHealthStatusType.HEALTHY,
                        last_success = now,
                        total_calls = 456,
                        total_failures = 5,
                        consecutive_failures = 0,
                        average_response_time = 0.34,
                        last_response_time = 0.28
                    ),
                    ApiHealthStatus(
                        source_name = "OpenWeatherMap API",
                        source_id = "openweather_api",
                        status = ApiHealthStatusType.DEGRADED,
                        last_success = now - timedelta(minutes = 2),
                        total_calls = 342,
                        total_failures = 49,
                        consecutive_failures = 3,
                        average_response_time = 1.45,
                        last_response_time = 2.31
                    ),
                    ApiHealthStatus(
                        source_name = "WeatherAPI.com",
                        source_id = "weatherapi_com",
                        status = ApiHealthStatusType.HEALTHY,
                        last_success = now - timedelta(seconds = 5),
                        total_calls = 156,
                        total_failures = 0,
                        consecutive_failures = 0,
                        average_response_time = 0.67,
                        last_response_time = 0.52
                    ),
                    ApiHealthStatus(
                        source_name = "Weather Underground",
                        source_id = "weather_underground",
                        status = ApiHealthStatusType.FAILING,
                        last_success = now - timedelta(hours = 1),
                        total_calls = 89,
                        total_failures = 68,
                        consecutive_failures = 15,
                        average_response_time = None,
                        last_response_time = None
                    )
                ]
            )

        elif monitor_type == 'alert':
            return HealthStatus(
                status = HealthStatusType.ERROR,
                last_check = now,
                heartbeat = now - timedelta(minutes = 65),
                error_message = "Monitor has stopped responding - requires restart",
                error_count = 15,
                api_sources = []
            )

        else:
            # Default healthy monitor
            return HealthStatus(
                status = HealthStatusType.HEALTHY,
                last_check = now,
                heartbeat = now,
                api_sources = []
            )
