from django.apps import AppConfig
from django.core.checks import Error, register

from hi.apps.common.asyncio_utils import start_background_event_loop


class MonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.monitor"


@register()
def check_start_background_tasks( app_configs, **kwargs ):
    """Start background tasks after all system checks have passed."""
    from hi.apps.monitor.monitor_manager import AppMonitorManager
    try:
        start_background_event_loop( task_function = AppMonitorManager().initialize ) 
    except Exception as e:
        return [
            Error(
                "Failed to start background tasks.",
                hint=f"Error: {e}",
                obj='background_tasks',
                id='hi.apps.monitor',
            )
        ]
    return []
