import logging

from django.http import Http404

from hi.hi_async_view import HiModalView

logger = logging.getLogger(__name__)


class MonitorHealthStatusView(HiModalView):
    """View for displaying monitor health status in a modal."""

    def get_template_name(self) -> str:
        return 'monitor/modals/monitor_health_status.html'

    def get(self, request, *args, **kwargs):
        """Handle GET request for monitor health status."""
        monitor_id = kwargs.get('monitor_id')
        if not monitor_id:
            raise Http404("Monitor ID is required")

        # Phase 1: Infrastructure only - actual monitor integration comes in Phase 2
        raise Http404("Monitor health status integration not yet implemented - use UI testing for development")
