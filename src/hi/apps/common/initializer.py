import asyncio
import threading
from typing import Callable, Coroutine, Any


class CoordinatedInitializer:
    """
    Used for one-time initializations that are shared across threads and
    asyncio tasks to prevent race conditions and ensure a function runs only once.
    """
    
    def __init__( self, initialization_function: Callable[[], Coroutine[Any, Any, Any]] ):
        self._initialization_function = initialization_function  # async function
        self._lock = threading.Lock()  # Protects initialization across threads
        self._initialization_complete = asyncio.Event()  # Signals when initialization is done
        self._was_initialized = False  # Protects against race condition on the async event itself
        return
    
    def initialize_sync( self ):
        with self._lock:
            if self._was_initialized:
                return
            asyncio.run( self._run_async())
        return
    
    async def initialize_async( self ):
        if self._was_initialized:
            await self._initialization_complete.wait()
            return

        async with asyncio.Lock():  # Inner lock to prevent concurrent async initialization
            if self._was_initialized:  # Check again inside the async lock
                await self._initialization_complete.wait()
                return

            await self._initialization_function()
            self._was_initialized = True
            self._initialization_complete.set()
        return
    
    async def _run_async( self, initialization_function ):
        await self._initialization_function()
        return
    

# Example usage:

async def initialize_subsystems():  # Your actual initialization logic
    # ... your _discover_app_settings and _load_or_create_settings logic here ...
    await asyncio.sleep(1) # Example operation
    return ["subsystem1", "subsystem2"]


async def initialize_database_connections(): # Another example initialization
    await asyncio.sleep(1)
    # ... database connection logic ...
    return "database_connection_pool"

# Create instances of the CoordinatedInitializer:
subsystem_initializer = CoordinatedInitializer()
database_initializer = CoordinatedInitializer()


# In your Django view (synchronous):
def my_view(request):
    subsystems = subsystem_initializer.initialize_sync(initialize_subsystems)
    database = database_initializer.initialize_sync(initialize_database_connections)
    # ... rest of your view logic, using subsystems and database

# In your background thread:
def background_thread_function():
    async def run_tasks():
        subsystems = await subsystem_initializer.initialize_async(initialize_subsystems)
        database = await database_initializer.initialize_async(initialize_database_connections)
        # ... use subsystems and database in background tasks ...

    asyncio.run(run_tasks())

background_thread = threading.Thread(target=background_thread_function)
background_thread.start()
