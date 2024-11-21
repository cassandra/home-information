import os


from django.apps import AppConfig


class ZoneminderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.integrations.zoneminder"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) != "true":
            # Avoid double initialization when using the reloader in development
            return
        from hi.integrations.core.integration_factory import IntegrationFactory
        from .zm_gateway import ZoneMinderGateway
        IntegrationFactory().register( ZoneMinderGateway() )
        return
