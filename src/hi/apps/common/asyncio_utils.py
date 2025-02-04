import asyncio
from threading import Thread


def start_background_event_loop( task_function, pass_event_loop = False ):
    """
    Generic function to start a background thread running an async task.
    
    :param task_function: Async function to be executed inside the thread.
    """
    def run_background_task_in_thread():

        background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop( background_loop )
                
        async def run_background_task():
            if pass_event_loop:
                await task_function( background_loop )
            else:
                await task_function()
            return
        
        background_loop.call_soon_threadsafe( asyncio.create_task, run_background_task() )
        background_loop.run_forever()
        return

    background_thread = Thread( target = run_background_task_in_thread )
    background_thread.daemon = True
    background_thread.start()
    return
