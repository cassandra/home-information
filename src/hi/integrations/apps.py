import asyncio
import os
import signal
from threading import Thread

from django.apps import AppConfig
from django.core.checks import Error, register


class CoreConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.integrations"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) is not None:
            # Avoid initialization when using the reloader in development
            return



        return


        
        # Note: This can be called multiple times by Django for the same
        # process and thread. Ensure idempotency if needed.
        
        from django.conf import settings
        if settings.DEBUG:
            # This app.py initialization runs in synchronous mode, so we
            # need to delay the background monitor tasks creation until the
            # asyncio event loop exists.
            #
            # This is for development only as the gunicorn.conf.py file
            # handles this initialization when execution with gunicorn.
            #
            asyncio.run( self._delayed_start() )
            
        return            

    async def _delayed_start(self):
        """ Runs after Django's startup to avoid event loop issues """
        from hi.integrations.integration_manager import IntegrationManager

        await asyncio.sleep( 0 )  # Ensure we're in an event loop
        integration_manager = IntegrationManager()
        asyncio.create_task( integration_manager.initialize() )
        
        def handle_signal( signal_number, frame ):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete( integration_manager.shutdown() )
            loop.close()
            import sys
            sys.exit( 0 )

        signal.signal( signal.SIGINT, handle_signal )
        signal.signal( signal.SIGTERM, handle_signal )
        return



@register()
def check_start_background_tasks( app_configs, **kwargs ):
    """Start background tasks after all system checks have passed."""
    try:
        start_background_thread() 
    except Exception as e:
        return [
            Error(
                "Failed to start integration background threrad or tasks.",
                hint = f"Error: {e}",
                obj = 'start_background_thread',
                id = 'hi.apps.integraton',
            )
        ]
    return []


def start_background_thread():

    def run_background_task_in_thread():  # New function

        async def run_background_task():
            from hi.integrations.integration_manager import IntegrationManager
            integration_manager = IntegrationManager()
            await integration_manager.initialize()
            return

        background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop( background_loop )
        background_loop.call_soon_threadsafe( asyncio.create_task, run_background_task() )
        background_loop.run_forever()
        return
    
    background_thread = Thread( target = run_background_task_in_thread )
    background_thread.daemon = True
    background_thread.start()
    return
    
