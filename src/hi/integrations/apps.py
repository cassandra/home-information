import os
import sys
from django.apps import AppConfig


class IntegrationsConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.integrations"

    def ready(self):
        from hi.background_tasks import HiBackgroundTaskHelper
        
        # Notes:
        #  - This method does not run in a production-like environment using gunicorn.
        #  - When it is called, it is often called multiple times during Django initialization.
        #  - Django seem to be suing different processes on each invocation.
        
        if os.environ.get('RUN_MAIN') != 'true':  # Prevents duplicate execution in `runserver`
            return
        
        # The responsibility for replicating the logic below falls to
        # gunicorn when it is being used (via its post_fork() config file).
        #
        if (( "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""))
            or ( "gunicorn" in sys.argv[0] )):
            return

        HiBackgroundTaskHelper.start_background_tasks_delayed()
        return
    
