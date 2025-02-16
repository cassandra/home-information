from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ConfigConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.config"
    
    def ready(self):
        from hi.apps.config.signals import SettingsInitializer

        # Populate the settings for all apps discovered to need them.
        post_migrate.connect( lambda sender, **kwargs: SettingsInitializer().run( sender, **kwargs ),
                              sender = self )
        return
    
