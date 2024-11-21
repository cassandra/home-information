import asyncio

from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.monitor"

    def ready(self):
        from hi.apps.monitor.monitor_manager import MonitorManager
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task( MonitorManager().start_all() )
        else:
            asyncio.run( MonitorManager().start_all() )
        return
