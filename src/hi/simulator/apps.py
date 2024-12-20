import asyncio
import os
import signal
import threading

from django.apps import AppConfig


class SimulatorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.simulator"

    def ready(self):
        from hi.simulator.simulator_manager import SimulatorManager
        if os.getenv( "RUN_MAIN", None ) != "true":
            # Avoid double initialization when using the reloader in development
            return

        # This app.py initialization runs in synchronous mode, so we
        # need to defer the background simulator manager tasks
        # creation by creating a separate thread.
        #
        # This is for development only as simulator only runs in DEBUG
        #
        thread = threading.Thread( target = self._start_simulators, daemon = True )
        thread.start()

        def handle_signal(signal_number, frame):
            SimulatorManager().shutdown()
            import sys
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)              
            
        return            

    def _start_simulators(self):
        from hi.simulator.simulator_manager import SimulatorManager
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop( loop )
        simulator_manager = SimulatorManager()
        try:
            loop.create_task( simulator_manager.initialize() )
            loop.run_forever()
        except Exception as e:
            print(f"Error in event loop: {e}")

        finally:
            loop.close()
        return
