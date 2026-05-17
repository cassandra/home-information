from django.apps import AppConfig


class DeviceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.entity"

    def ready(self):
        from hi.apps.entity.state_panel_registry import EntityStatusPanelRegistry
        EntityStatusPanelRegistry().discover()
        return
