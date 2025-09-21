from django.http import Http404
from django.shortcuts import render
from django.views.generic import View

from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider
from hi.apps.system.provider_info import ProviderInfo
from hi.apps.system.tests.synthetic_data import SystemSyntheticData


class SystemTestUiHomeView(View):

    def get(self, request, *args, **kwargs):
        context = {
            'app_name': 'monitor',
        }
        return render(request, 'system/tests/ui/home.html', context)


class SystemTestUiHealthStatusView(View):
    """
    View for testing health status modals with various synthetic data scenarios.
    Supports all HealthStatusType values with both regular HealthStatus and AggregateHealthStatus data.

    URL patterns:
    - /test/health-status/<status_type>/<api_flag>/
    - status_type: unknown, healthy, warning, error, disabled
    - api_flag: with-api, no-api
    """

    def get(self, request, *args, **kwargs):
        status_type = kwargs.get('status_type', 'healthy')
        api_flag = kwargs.get('api_flag', 'no-api')

        # Validate parameters using enum parsing
        try:
            # Convert status_type to HealthStatusType enum
            status_enum = HealthStatusType.from_name(status_type.upper())
            status_type = str(status_enum)
        except (ValueError, AttributeError):
            raise Http404(f"Invalid status type: {status_type}")

        # Validate api_flag
        if api_flag not in ['with-api', 'no-api', 'withapi', 'noapi']:
            raise Http404(f"Invalid api flag: {api_flag}")

        with_api_data = api_flag in ['with-api', 'withapi']

        # Create health status for the requested scenario
        health_status = SystemSyntheticData.create_health_status_for_testing(
            status_type,
            with_api_data = with_api_data,
        )

        class TestProvider( HealthStatusProvider ):
            @classmethod
            def get_provider_info(cls) -> ProviderInfo:
                return SystemSyntheticData.create_provider_info()

        health_status_provider = TestProvider()
        health_status_provider._health_status = health_status
        
        # Render template with scenario data (matching existing modal template expectations)
        context = {
            'health_status_provider': health_status_provider,
        }
        return render(request, 'system/modals/health_status.html', context)
