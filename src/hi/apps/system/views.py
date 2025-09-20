import logging

from django.http import Http404

from hi.hi_async_view import HiModalView

from hi.apps.common.asyncio_utils import BackgroundTaskMonitor
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView
from hi.apps.monitor.monitor_manager import AppMonitorManager
from hi.apps.weather.weather_source_manager import WeatherSourceManager

from .asyncio_health_status import AsyncioHealthStatusProvider

logger = logging.getLogger(__name__)


class SystemInfoView( ConfigPageView ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.SYSTEM_INFO
    
    def get_main_template_name( self ) -> str:
        return 'system/panes/system_info.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        # Get app monitor health status providers
        app_monitor_manager = AppMonitorManager()
        # Sort monitors alphabetically for consistent display
        app_monitors = sorted(
            app_monitor_manager.get_health_status_providers(),
            key=lambda m: m.get_provider_info().provider_id
        )

        # Get weather source health status
        weather_source_manager = WeatherSourceManager()
        weather_health = weather_source_manager.health_status

        # Get background task health status
        background_task_health_status = AsyncioHealthStatusProvider.get_health_status()

        return {
            'app_monitors': app_monitors,
            'weather_health': weather_health,
            'background_task_health_status': background_task_health_status,
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
            health_status = AsyncioHealthStatusProvider.get_health_status()
            context = {
                'health_status': health_status,
            }
            return self.modal_response(request, context)

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
