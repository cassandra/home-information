from datetime import timedelta
from django.shortcuts import render
from django.views.generic import View

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.system.api_health import ApiHealthStatus
from hi.apps.system.api_health_aggregator import ApiHealthAggregator
from hi.apps.system.api_service_info import ApiServiceInfo
from hi.apps.system.enums import HealthStatusType, ApiHealthStatusType, HealthAggregationRule
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
        provider_type = kwargs.get('monitor_type', 'zoneminder')  # Keep 'monitor_type' for URL compatibility

        # Create synthetic health status based on provider type
        health_status = self._create_synthetic_health_status(provider_type)
        provider_label = self._get_provider_label(provider_type)

        # Render template directly with synthetic data
        context = {
            'health_status': health_status,
            'monitor_label': provider_label,  # Keep template key for compatibility
            'monitor_id': provider_type,
        }
        return render(request, 'system/modals/health_status.html', context)

    def _get_provider_label(self, provider_id: str) -> str:
        """Get display label for health status provider based on ID."""
        provider_labels = {
            'zoneminder': 'ZoneMinder Integration Provider',
            'hass': 'Home Assistant Integration Provider',
            'weather': 'Weather Updates Provider',
            'alert': 'Alert Processing Provider',
            'security': 'Security Provider',
            'notify': 'Notification Provider',
            'config_error': 'Configuration Error Test Provider',
            'connection_error': 'Connection Error Test Provider',
            'temporary_error': 'Temporary Error Test Provider',
            'disabled': 'Disabled Test Provider',
        }
        return provider_labels.get(provider_id, f'Health Status Provider {provider_id}')

    def _create_synthetic_health_status(self, provider_type: str):
        """Create synthetic health status data for UI testing."""
        now = datetimeproxy.now()

        if provider_type == 'zoneminder':
            api_sources = {
                ApiServiceInfo(
                    service_name="ZoneMinder API",
                    service_id="zoneminder_api"
                ): ApiHealthStatus(
                    service_name = "ZoneMinder API",
                    service_id = "zoneminder_api",
                    status = ApiHealthStatusType.HEALTHY,
                    last_success = now,
                    total_calls = 1247,
                    total_failures = 10,
                    consecutive_failures = 0,
                    average_response_time = 0.23,
                    last_response_time = 0.21
                )
            }
            return ApiHealthAggregator(
                status = HealthStatusType.HEALTHY,
                last_check = now,
                heartbeat = now,
                api_sources = api_sources,
                aggregation_rule = HealthAggregationRule.ALL_SOURCES_HEALTHY
            )

        elif provider_type == 'weather':
            api_sources = {
                ApiServiceInfo(
                    service_name="National Weather Service",
                    service_id="nws_api"): ApiHealthStatus(
                        service_name = "National Weather Service",
                        service_id = "nws_api",
                        status = ApiHealthStatusType.HEALTHY,
                        last_success = now,
                        total_calls = 456,
                        total_failures = 5,
                        consecutive_failures = 0,
                        average_response_time = 0.34,
                        last_response_time = 0.28
                    ),
                ApiServiceInfo(service_name="OpenWeatherMap API", service_id="openweather_api"): ApiHealthStatus(
                    service_name = "OpenWeatherMap API",
                    service_id = "openweather_api",
                    status = ApiHealthStatusType.DEGRADED,
                    last_success = now - timedelta(minutes = 2),
                    total_calls = 342,
                    total_failures = 49,
                    consecutive_failures = 3,
                    average_response_time = 1.45,
                    last_response_time = 2.31
                ),
                ApiServiceInfo(service_name="WeatherAPI.com", service_id="weatherapi_com"): ApiHealthStatus(
                    service_name = "WeatherAPI.com",
                    service_id = "weatherapi_com",
                    status = ApiHealthStatusType.HEALTHY,
                    last_success = now - timedelta(seconds = 5),
                    total_calls = 156,
                    total_failures = 0,
                    consecutive_failures = 0,
                    average_response_time = 0.67,
                    last_response_time = 0.52
                ),
                ApiServiceInfo(service_name="Weather Underground", service_id="weather_underground"): ApiHealthStatus(
                    service_name = "Weather Underground",
                    service_id = "weather_underground",
                    status = ApiHealthStatusType.FAILING,
                    last_success = now - timedelta(hours = 1),
                    total_calls = 89,
                    total_failures = 68,
                    consecutive_failures = 15,
                    average_response_time = None,
                    last_response_time = None
                )
            }
            return ApiHealthAggregator(
                status = HealthStatusType.WARNING,
                last_check = now,
                heartbeat = now,
                error_message = "Some weather API sources are failing - degraded service",
                api_sources = api_sources,
                aggregation_rule = HealthAggregationRule.MAJORITY_SOURCES_HEALTHY
            )

        elif provider_type == 'alert':
            return HealthStatus(
                status = HealthStatusType.ERROR,
                last_check = now,
                heartbeat = now - timedelta(minutes = 65),
                error_message = "Provider has stopped responding - requires restart",
                error_count = 15
            )

        elif provider_type == 'config_error':
            return HealthStatus(
                status = HealthStatusType.CONFIG_ERROR,
                last_check = now,
                heartbeat = now,
                error_message = "Configuration validation failed: missing required API key",
                error_count = 1,
            )

        elif provider_type == 'connection_error':
            return HealthStatus(
                status = HealthStatusType.CONNECTION_ERROR,
                last_check = now,
                heartbeat = now,
                error_message = "Unable to establish connection to external service",
                error_count = 3,
            )

        elif provider_type == 'disabled':
            return HealthStatus(
                status = HealthStatusType.DISABLED,
                last_check = now,
                heartbeat = now,
                error_message = "Provider has been manually disabled for maintenance",
            )

        elif provider_type == 'temporary_error':
            return HealthStatus(
                status = HealthStatusType.TEMPORARY_ERROR,
                last_check = now,
                heartbeat = now,
                error_message = "Experiencing temporary issues with rate limiting",
                error_count = 2,
            )

        else:
            # Default healthy provider
            return HealthStatus(
                status = HealthStatusType.HEALTHY,
                last_check = now,
                heartbeat = now,
            )
