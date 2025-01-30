from django.apps import AppConfig
from django.core.checks import Error, register

from hi.apps.common.asyncio_utils import start_background_event_loop


class CoreConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.integrations"


@register()
def check_start_background_tasks( app_configs, **kwargs ):
    """Start background tasks after all system checks have passed."""
    from hi.integrations.integration_manager import IntegrationManager
    try:
        start_background_event_loop( task_function = IntegrationManager().initialize ) 
    except Exception as e:
        return [
            Error(
                "Failed to start integration background threrad or tasks.",
                hint = f"Error: {e}",
                obj = 'start_background_thread',
                id = 'hi.apps.integraton',
            )
        ]
    return []
