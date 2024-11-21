import os

from django.apps import AppConfig


class HassConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.integrations.hass"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) != "true":
            # Avoid double initialization when using the reloader in development
            return
        from hi.integrations.core.integration_factory import IntegrationFactory
        from .hass_gateway import HassGateway
        IntegrationFactory().register( HassGateway() )
        return
    
