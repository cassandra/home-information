import asyncio
import os
import signal

from django.apps import AppConfig


class SimulatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.simulator"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) is not None:
            # Avoid double initialization when using the reloader in development
            return



        return


        
        # Note: This can be called multiple times by Django for the same
        # process and thread. Ensure idempotency if needed.

        # This app.py initialization runs in synchronous mode, so we
        # need to delay the background monitor tasks creation until the
        # asyncio event loop exists.
        #
        # This is for development only as simulator only runs in DEBUG
        #
        asyncio.run( self._delayed_start() )
        return            

    async def _delayed_start(self):
        """ Runs after Django's startup to avoid event loop issues """
        from hi.simulator.simulator_manager import SimulatorManager

        await asyncio.sleep( 0 )  # Ensure we're in an event loop
        simulator_manager = SimulatorManager()
        asyncio.create_task( simulator_manager.initialize() )

        def handle_signal( signal_number, frame ):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete( simulator_manager.shutdown() )
            loop.close()
            import sys
            sys.exit( 0 )

        signal.signal( signal.SIGINT, handle_signal )
        signal.signal( signal.SIGTERM, handle_signal )
        return
