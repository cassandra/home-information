from django.apps import AppConfig
from django.core.checks import Error, register

from hi.apps.common.asyncio_utils import start_background_event_loop


class SimulatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.simulator"


@register()
def check_start_background_tasks( app_configs, **kwargs ):
    """Start background tasks after all system checks have passed."""
    from hi.simulator.simulator_manager import SimulatorManager
    try:
        start_background_event_loop( task_function = SimulatorManager().initialize ) 
    except Exception as e:
        return [
            Error(
                "Failed to start integration background threrad or tasks.",
                hint = f"Error: {e}",
                obj = 'start_background_thread',
                id = 'hi.simulator',
            )
        ]
    return []
