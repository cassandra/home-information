import os

from django.apps import AppConfig


class NotifyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.notify"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) != "true":
            # Avoid double initialization when using the reloader in development
            return
        from hi.apps.monitor.monitor_manager import MonitorManager
        from hi.apps.notify.notification_monitor import NotificationMonitor
        notification_monitor = NotificationMonitor()
        MonitorManager().register( notification_monitor )
        return
