import asyncio
import os
import signal
import threading

from django.apps import AppConfig


class CoreConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.integrations"

    def ready(self):
        from hi.integrations.integration_manager import IntegrationManager
        if os.getenv( "RUN_MAIN", None ) != "true":
            # Avoid double initialization when using the reloader in development
            return
        from django.conf import settings
        if settings.DEBUG:
            # This app.py initialization runs in synchronous mode, so we
            # need to defer the background integration manager tasks
            # creation by creating a separate thread.
            #
            # This is for development only as the gunicorn.conf.py file
            # handles this initialization when execution with gunicorn.
            #
            thread = threading.Thread( target = self._start_integrations, daemon = True )
            thread.start()

            def handle_signal(signal_number, frame):
                IntegrationManager().shutdown()
                import sys
                sys.exit(0)

            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)              
            
        return            

    def _start_integrations(self):
        from hi.integrations.integration_manager import IntegrationManager
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop( loop )
        integration_manager = IntegrationManager()
        try:
            loop.create_task( integration_manager.initialize() )
            loop.run_forever()
        except Exception as e:
            print(f"Error in event loop: {e}")

        finally:
            loop.close()
        return
