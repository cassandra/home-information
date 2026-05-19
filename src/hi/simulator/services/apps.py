import os
import sys

from django.apps import AppConfig


class ServicesConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.services'

    def ready(self):
        import time
        from hi.apps.common.asyncio_utils import start_background_event_loop
        from .service_simulator_manager import ServiceSimulatorManager

        if os.environ.get('RUN_MAIN') != 'true':
            return

        if (( 'gunicorn' in os.environ.get( 'SERVER_SOFTWARE', '' ))
            or ( 'gunicorn' in sys.argv[0] )):
            return

        # Django's ready() fires before the system is fully usable.
        time.sleep(1)
        start_background_event_loop(
            task_function = ServiceSimulatorManager().initialize,
        )
        return
