import asyncio
import weakref
import threading
from threading import Thread


class BackgroundTaskMonitor:
    """Monitor for background event loops and tasks running in daemon threads"""
    _instances = {}  # task_function_name -> monitor info

    @classmethod
    def register_background_task(cls, name, loop, thread):
        """Register a background task for monitoring"""
        cls._instances[name] = {
            'loop_ref': weakref.ref(loop) if loop else None,
            'thread_ref': weakref.ref(thread) if thread else None,
            'thread_name': thread.name if thread else None,
            'registered_at': threading.current_thread().name,
        }

    @classmethod
    def get_background_task_status(cls):
        """Get comprehensive status of all background tasks and loops"""
        status = {
            'main_thread': {
                'name': threading.main_thread().name,
                'is_alive': threading.main_thread().is_alive(),
            },
            'current_thread': {
                'name': threading.current_thread().name,
                'active_count': threading.active_count(),
            },
            'background_tasks': {}
        }

        for task_name, info in cls._instances.items():
            task_status = {
                'registered_from': info.get('registered_at'),
                'thread_name': info.get('thread_name'),
            }

            # Check thread status
            thread = info['thread_ref']() if info['thread_ref'] else None
            task_status['thread'] = {
                'exists': thread is not None,
                'is_alive': thread.is_alive() if thread else False,
                'is_daemon': thread.daemon if thread else None,
            }

            # Check event loop status
            loop = info['loop_ref']() if info['loop_ref'] else None
            if loop:
                try:
                    # Get tasks from the background loop
                    tasks = asyncio.all_tasks(loop)
                    task_details = []

                    for task in tasks:
                        try:
                            task_info = {
                                'name': getattr(task, 'get_name', lambda: 'unnamed')(),
                                'done': task.done(),
                                'cancelled': task.cancelled(),
                            }

                            # Try to get coroutine name safely
                            try:
                                coro = task.get_coro()
                                if hasattr(coro, '__name__'):
                                    task_info['coro_name'] = coro.__name__
                                elif hasattr(coro, '__qualname__'):
                                    task_info['coro_name'] = coro.__qualname__
                                else:
                                    task_info['coro_name'] = str(type(coro).__name__)
                            except:
                                task_info['coro_name'] = 'unknown'

                            task_details.append(task_info)
                        except Exception as e:
                            task_details.append({'error': f'Task info error: {e}'})

                    task_status['event_loop'] = {
                        'exists': True,
                        'is_running': loop.is_running(),
                        'is_closed': loop.is_closed(),
                        'total_tasks': len(tasks),
                        'active_tasks': len([t for t in tasks if not t.done()]),
                        'task_details': task_details,
                    }
                except Exception as e:
                    task_status['event_loop'] = {
                        'exists': True,
                        'error': f'Loop access error: {e}'
                    }
            else:
                task_status['event_loop'] = {
                    'exists': False,
                    'error': 'Event loop reference is dead'
                }

            status['background_tasks'][task_name] = task_status

        return status


def start_background_event_loop( task_function, pass_event_loop = False ):
    """
    Generic function to start a background thread running an async task.

    :param task_function: Async function to be executed inside the thread.
    """
    # Generate a name for this background task
    task_name = getattr(task_function, '__name__', str(task_function))
    if hasattr(task_function, '__self__'):
        # This is a method, include the class name
        class_name = task_function.__self__.__class__.__name__
        task_name = f"{class_name}.{task_name}"

    def run_background_task_in_thread():
        background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop( background_loop )

        # Register this task for monitoring
        current_thread = threading.current_thread()
        current_thread.name = f"Background-{task_name}"
        BackgroundTaskMonitor.register_background_task(task_name, background_loop, current_thread)

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
