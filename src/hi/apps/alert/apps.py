import os

from django.apps import AppConfig


class AlertConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.alert"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) != "true":
            # Avoid double initialization when using the reloader in development
            return
        from hi.apps.monitor.monitor_manager import MonitorManager
        from hi.apps.alert.alert_monitor import AlertMonitor
        alert_monitor = AlertMonitor()
        MonitorManager().register( alert_monitor )
        return
