import asyncio
import signal

    
def post_worker_init( worker ):
    """ Start all bacxkground monitoring processes via asyncio """
    from hi.apps.monitor.monitor_manager import AppMonitorManager
    from hi.integrations.integration_manager import IntegrationManager

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    worker.log.info('Starting app monitor manager ...')
    monitor_manager = AppMonitorManager()
    loop.create_task( monitor_manager.initialize() )

    worker.log.info('Starting integration manager ...')
    integration_manager = IntegrationManager()
    loop.create_task( integration_manager.initialize() )

    worker.log.info('Worker background event loop is running.')

    def handle_signal(signal_number, frame):
        worker.log.info( f'Worker received signal {signal_number}. Cleaning up monitors...' )
        loop.run_until_complete( monitor_manager.shutdown() )
        loop.run_until_complete( integration_manager.shutdown() )
        loop.stop()
        import sys
        sys.exit(0)

    signal.signal( signal.SIGINT, handle_signal )
    signal.signal( signal.SIGTERM, handle_signal )
    return


def on_exit(server):
    from hi.apps.monitor.monitor_manager import AppMonitorManager
    from hi.integrations.integration_manager import IntegrationManager
    server.log.info('Stopping all monitors on Gunicorn exit...')
    AppMonitorManager().shutdown()
    IntegrationManager().shutdown()
    return
