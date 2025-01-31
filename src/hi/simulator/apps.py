import os
import sys
from django.apps import AppConfig


class SimulatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.simulator"

    def ready(self):
        import time
        from hi.apps.common.asyncio_utils import start_background_event_loop
        from hi.simulator.simulator_manager import SimulatorManager

        # Notes:
        #  - This method does not run in a production-like environment using gunicorn.
        #  - When it is called, it is often called multiple times during Django initialization.
        #  - Django seem to be suing different processes on each invocation.
        
        if os.environ.get('RUN_MAIN') != 'true':  # Prevents duplicate execution in `runserver`
            return

        # The responsibility for replicating the logic below falls to
        # gunicorn when it is being used (via its post_fork() config file).
        #
        # However, the simulator is not currently set up for anything but
        # runserver execution.
        #
        if (( "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""))
            or ( "gunicorn" in sys.argv[0] )):
            return

        time.sleep(1)
        start_background_event_loop( task_function = SimulatorManager().initialize ) 
        return
