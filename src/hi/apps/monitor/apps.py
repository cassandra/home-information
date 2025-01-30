import asyncio
import os
import signal
from threading import Thread

from django.apps import AppConfig

import hi.apps.common.debug_utils as debug_utils


class MonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hi.apps.monitor"

    def ready(self):
        if os.getenv( "RUN_MAIN", None ) is not None:
            # Avoid double initialization when using the reloader in development
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



        
            
            #print( f'PRE-ASYNCIO-RUN: %s' % debug_utils.get_event_loop_context() )



            ###asyncio.run( self._delayed_start() )
            pass
        
        return            

    async def _delayed_start(self):



        return




        
        """ Runs after Django's startup to avoid event loop issues """
        from hi.apps.monitor.monitor_manager import AppMonitorManager

        await asyncio.sleep( 0 )  # Ensure we're in an event loop
        monitor_manager = AppMonitorManager()






        print( f'PRE-THREAD' )


            
        background_loop = asyncio.new_event_loop()
        background_thread = Thread( target = background_loop.run_forever )
        background_thread.start()
        
        
        
        print( f'POST-THREAD' )
        
        
        async def run_background_tasks():
            from hi.apps.monitor.monitor_manager import AppMonitorManager
            monitor_manager = AppMonitorManager()


            print( f'PRE-INITIALIZE: %s' % debug_utils.get_event_loop_context() )


            await monitor_manager.initialize()
            return

        background_loop.run_until_complete( run_background_tasks() )
        return











        

        
        print( f'PRE-INITIALIZE: %s' % debug_utils.get_event_loop_context() )
        

        
        task = asyncio.create_task( monitor_manager.initialize() )
        await task

        def handle_signal( signal_number, frame ):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete( monitor_manager.shutdown() )
            loop.close()
            import sys
            sys.exit( 0 )

        signal.signal( signal.SIGINT, handle_signal )
        signal.signal( signal.SIGTERM, handle_signal )
        return





import tracemalloc
tracemalloc.start()  # Start tracing memory allocations


    
from django.core.checks import Error, register

@register()
def check_start_background_tasks( app_configs, **kwargs ):
    """Start background tasks after all system checks have passed."""

    print('CHECKING BACKGROUND THREADS')

    try:
        start_background_thread() 
    except Exception as e:
        return [
            Error(
                "Failed to start background tasks.",
                hint=f"Error: {e}",
                obj='background_tasks',
                id='hi.simulator.W001',
            )
        ]
    return []






def start_background_thread():
    print('STARTING BACKGROUND THREADS')

    def run_background_tasks_in_thread():  # New function


        print(f'RUN-BG: %s' % debug_utils.get_event_loop_context())

        
        async def run_background_tasks():
            from hi.apps.monitor.monitor_manager import AppMonitorManager
            monitor_manager = AppMonitorManager()

            print('PRE-INITIALIZE: %s' % debug_utils.get_event_loop_context())

            await monitor_manager.initialize()
            return

        background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop( background_loop )

        
        background_loop.call_soon_threadsafe( asyncio.create_task, run_background_tasks() )
        background_loop.run_forever()

        #asyncio.create_task( run_background_tasks() )                
        
        import time
        time.sleep( 3 )
    


    print(f'PRE-THREAD')

    background_thread = Thread( target = run_background_tasks_in_thread )
    background_thread.daemon = True
    background_thread.start()


    print(f'POST-THREAD')
    return



    
def start_background_thread_OLD():
    print('STARTING BACKGROUND THREADS')
    
    from hi.apps.monitor.monitor_manager import AppMonitorManager

    monitor_manager = AppMonitorManager()






    print( f'PRE-THREAD' )



    background_loop = asyncio.new_event_loop()
    background_thread = Thread( target = background_loop.run_forever )
    background_thread.daemon = True 
    background_thread.start()



    print( f'POST-THREAD' )


    async def run_background_tasks():
        from hi.apps.monitor.monitor_manager import AppMonitorManager
        monitor_manager = AppMonitorManager()


        print( f'PRE-INITIALIZE: %s' % debug_utils.get_event_loop_context() )


        await monitor_manager.initialize()
        return

    background_loop.run_until_complete( run_background_tasks() )
    return
