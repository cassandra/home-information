import asyncio
import sys
import threading

from django.apps import AppConfig


class IntegrationCommonConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.integrations.core"

    INITIALIZATION_LOCK_NAME = 'integration_initialization'
    
    def ready(self):
        if not self.is_runserver_command():
            return
        threading.Thread( target = self.initialize_integrations ).start()
        return
    
    def initialize_integrations(self):
        from hi.apps.common.database_lock import DatabaseLockContext
        from .initialize import initialize_integrations  # Need to be inside this method

        try:
            with DatabaseLockContext( name = self.INITIALIZATION_LOCK_NAME ):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete( initialize_integrations() )
                loop.close()

        except RuntimeError:
            pass 
        
        return

    def is_runserver_command(self):
        return bool( len(sys.argv) > 1 and sys.argv[1] == 'runserver' )
