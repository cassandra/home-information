import logging

from django.http import Http404

from hi.hi_async_view import HiModalView

from hi.apps.common.asyncio_utils import BackgroundTaskMonitor
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.monitor.monitor_manager import AppMonitorManager
from hi.apps.weather.weather_source_manager import WeatherSourceManager

from hi.integrations.integration_manager import IntegrationManager

from .asyncio_health_provider import AsyncioHealthStatusProvider

logger = logging.getLogger(__name__)


class SystemInfoView( ConfigPageView ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.SYSTEM_INFO
    
    def get_main_template_name( self ) -> str:
        return 'system/panes/system_info.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        app_monitor_providers = sorted(
            AppMonitorManager().get_health_status_providers(),
            key = lambda m: m.get_provider_info().provider_name
        )
        integration_providers = sorted(
            IntegrationManager().get_health_status_providers(),
            key = lambda m: m.get_provider_info().provider_name
        )
        return {
            'app_monitor_providers': app_monitor_providers,
            'integration_providers': integration_providers,
            'weather_provider': WeatherSourceManager(),
            'background_task_provider': AsyncioHealthStatusProvider(),
        }


class SystemHealthStatusView(HiModalView):
    """View for displaying monitor health status in a modal."""

    def get_template_name(self) -> str:
        return 'system/modals/health_status.html'

    def get(self, request, *args, **kwargs):
        provider_id = kwargs.get('provider_id')
        if not provider_id:
            raise Http404("Provider ID is required")

        # Handle background task health status
        if provider_id == 'hi.apps.system.background_tasks':
            return BackgroundTaskDetailsView().get(request, *args, **kwargs)

        if provider_id == 'hi.apps.weather.weather_sources':
            return WeatherHealthStatusDetailsView().get( request, *args, **kwargs )
        
        # Handle app monitor health status
        app_monitor_manager = AppMonitorManager()
        monitors = app_monitor_manager.get_health_status_providers()

        # Find the monitor with matching provider_id
        target_monitor = None
        for monitor in monitors:
            if monitor.get_provider_info().provider_id == provider_id:
                target_monitor = monitor
                break

        if not target_monitor:
            raise Http404(f"Monitor with provider_id '{provider_id}' not found")

        context = {
            'health_status': target_monitor.health_status,
        }
        return self.modal_response(request, context)

    
class SystemApiHealthStatusView(HiModalView):

    def get_template_name(self) -> str:
        return 'system/modals/api_health_status.html'

    def get(self, request, *args, **kwargs):
        provider_id = kwargs.get('provider_id')
        if not provider_id:
            raise Http404("Provider ID is required")

        if provider_id.startswith( 'hi.apps.weather.weather_sources' ):
            return WeatherHealthStatusDetailsView().get( request, *args, **kwargs )
        else:
            raise NotImplementedError(f'Api health status for "{provider_id}" not implemented.')
        
        api_health_status = None
        context = {
            'api_health_status': api_health_status
        }
        return self.modal_response(request, context)


class WeatherHealthStatusDetailsView(HiModalView):
    """View for displaying detailed background task information in a modal."""

    def get_template_name(self) -> str:
        return 'system/modals/health_status.html'

    def get(self, request, *args, **kwargs):
        context = {
            'health_status': WeatherSourceManager().health_status,
        }
        return self.modal_response(request, context)


class BackgroundTaskDetailsView(HiModalView):
    """View for displaying detailed background task information in a modal."""

    def get_template_name(self) -> str:
        return 'system/modals/background_task_status.html'

    def get(self, request, *args, **kwargs):
        async_diagnostics = BackgroundTaskMonitor.get_background_task_status()
        context = {
            'async_diagnostics': async_diagnostics,
        }
        return self.modal_response(request, context)
