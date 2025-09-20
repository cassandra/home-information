import logging

from django.http import Http404

from hi.hi_async_view import HiModalView

from hi.apps.common.asyncio_utils import BackgroundTaskMonitor
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView

logger = logging.getLogger(__name__)


class SystemInfoView( ConfigPageView ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.SYSTEM_INFO
    
    def get_main_template_name( self ) -> str:
        return 'system/panes/system_info.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        return {
            'async_diagnostics': BackgroundTaskMonitor.get_background_task_status(),
        }


class SystemHealthStatusView(HiModalView):
    """View for displaying monitor health status in a modal."""

    def get_template_name(self) -> str:
        return 'system/modals/system_health_status.html'

    def get(self, request, *args, **kwargs):
        provider_id = kwargs.get('provider_id')
        if not provider_id:
            raise Http404("Provider ID is required")

        raise NotImplementedError("Health status integration not yet implemented")
