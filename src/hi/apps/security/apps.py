import os
from django.apps import AppConfig


class SecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.security"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) != "true":
            # Avoid double initialization when using the reloader in development
            return
        from hi.apps.monitor.monitor_manager import MonitorManager
        from hi.apps.security.security_monitor import SecurityMonitor
        security_monitor = SecurityMonitor()
        MonitorManager().register( security_monitor )
        return
