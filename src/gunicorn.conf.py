"""Need to run with: gunicorn -c gunicorn.conf.py hi.wsgi:application

TODO: This code is untested and not verified. Placeholder code was added
during local development for future reference when converting to run via
gunicorn.

"""

import asyncio
import signal

    
def post_worker_init( worker ):
    from hi.apps.monitor.monitor_manager import AppMonitorManager
    from hi.integrations.core.integration_manager import IntegrationManager
    _ = asyncio.get_event_loop()  # Ensure event loop exists, or creates it
    worker.log.info("Starting app monitor manager ...")
    asyncio.run( AppMonitorManager().initialize() )
    worker.log.info("Starting integration manager ...")
    asyncio.run( IntegrationManager().initialize() )

    def handle_signal(signal_number, frame):
        worker.log.info(f"Worker received signal {signal_number}. Cleaning up monitors...")
        AppMonitorManager().shutdown()
        IntegrationManager().shutdown()
        import sys
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    return


def on_exit(server):
    from hi.apps.monitor.monitor_manager import AppMonitorManager
    from hi.integrations.core.integration_manager import IntegrationManager
    server.log.info("Stopping all monitors on Gunicorn exit...")
    AppMonitorManager().shutdown()
    IntegrationManager().shutdown()
    return
