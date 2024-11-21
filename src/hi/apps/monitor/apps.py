import asyncio
import os
import signal
import threading

from django.apps import AppConfig
from hi.apps.monitor.monitor_manager import MonitorManager


class MonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.monitor"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) != "true":
            # Avoid double initialization when using the reloader in development
            return
        from django.conf import settings
        if settings.DEBUG:
            # This app.py initialization runs in synchronous mode, so we
            # need to defer the background monitor tasks creation by
            # creating a sepaarte thread.
            #
            # This is for development only as the gunicorn.conf.py file
            # handles this initialization when execution with gunicorn.
            #
            thread = threading.Thread( target = self._start_monitors, daemon = True )
            thread.start()

            def handle_signal(signal_number, frame):
                MonitorManager().shutdown()
                import sys
                sys.exit(0)

            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)              
            
        return            

    def _start_monitors(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop( loop )
        monitor_manager = MonitorManager()
        try:
            loop.create_task( monitor_manager.initialize() )
            loop.run_forever()
        except Exception as e:
            print(f"Error in event loop: {e}")

        finally:
            loop.close()
        return
