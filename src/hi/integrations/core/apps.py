import logging
import asyncio
import sys
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.integrations.core"

    INITIALIZATION_LOCK_NAME = 'integration_initialization'
    INITIALIZATION_LOCK_TIME_SECS = 10
    
    def ready(self):
        if not self.is_runserver_command():
            return
        threading.Thread( target = self.initialize ).start()
        return
    
    def initialize(self):
        from hi.apps.common.database_lock import InitializationLockContext
        from .initialize import initialize_integrations  # Need to be inside this method

        try:
            # Ensure this only runs once on startup.  The ready() method
            # could be called multiple times and there could be multiple
            # processes / threads.
            with InitializationLockContext( name = self.INITIALIZATION_LOCK_NAME,
                                            timeout_seconds = self.INITIALIZATION_LOCK_TIME_SECS ):
                logger.info( 'Initializing integrations ...' )
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete( initialize_integrations() )
                loop.close()

        except RuntimeError:
            pass 
        
        return

    def is_runserver_command(self):
        return bool( len(sys.argv) > 1 and sys.argv[1] == 'runserver' )
