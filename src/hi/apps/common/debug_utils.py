import asyncio
import os
import threading


def get_process_context() -> str:
    pid = os.getpid()
    tid = threading.get_ident()
    return f'ProcessId={pid}, ThreadId={tid}'


def get_event_loop_context() -> str:
    # Maybe add:
    #
    # task.get_coro()
    # task.get_stack(): 
    try:
        loop = asyncio.get_running_loop()
        tasks = asyncio.all_tasks( loop )
        task_list = [ f'Task={x}, State={x._state}, Name={x.get_name()}'
                      for x in tasks ]
        return f'EventLoopId={id(loop)}, Tasks={task_list}'
    except RuntimeError:
        return 'No event loop is running.'
