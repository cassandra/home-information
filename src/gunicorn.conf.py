"""
Need to run with: gunicorn -c gunicorn.conf.py hi.wsgi:application
"""

import signal
from hi.apps.monitor.monitor_manager import MonitorManager

    
def post_worker_init( worker ):
    worker.log.info("Starting monitors in worker...")
    MonitorManager().start_all()

    def handle_signal(signal_number, frame):
        worker.log.info(f"Worker received signal {signal_number}. Cleaning up monitors...")
        MonitorManager().stop_all()
        import sys
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    return


def on_exit(server):
    server.log.info("Stopping all monitors on Gunicorn exit...")
    MonitorManager().stop_all()
    return
