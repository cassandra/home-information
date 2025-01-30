from asgiref.sync import async_to_sync, sync_to_async
import asyncio
import threading
from threading import Lock
from concurrent.futures import ThreadPoolExecutor


class SingletonSync:
    _instance = None

    def __new__( cls ):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__new__( cls )
            cls._instance.__init_singleton__()
        return cls._instance

    
class AsyncSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-check locking
                    cls._instance = super( Singleton, cls ).__new__( cls )
                    cls._instance.__init_singleton__()
        return cls._instance

    def __init_singleton__(self):
        """ Synchronous initializer, wraps async init if necessary. """
        if not hasattr(self, "_initialized"):
            self._initialized = False
            self._async_lock = asyncio.Lock()  # ✅ Prevent multiple async inits
            async_to_sync( self.__async_init_singleton__ )()  # ✅ Sync wrapper for async init

    async def __async_init_singleton__(self):
        """ Asynchronous initializer """
        if self._initialized:
            return
        self._initialized = True  # ✅ Prevent duplicate async init
        # Perform any async setup here (e.g., DB connections, API setup)
    


class SingletonGemini:
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            # print( 'ABOUT TO LOCK' )
            with cls._lock:
                # print( 'LOCK ACQUIRED' )
                if cls._instance is None: 
                    # print( 'PRE-SUPER' )
                    cls._instance = super().__new__(cls)
                    # print( 'POST-SUPER' )
                    cls._instance.__init_singleton_internal__()
                    # print( 'POST-INIT' )
        return cls._instance

    def __init_singleton_internal__(self):
        # print( 'INIT CALLED' )
        if not self._initialized:
            self._initialized = True
            # print( 'PRE-USER-INIT' )
            self.__init_singleton__()
            # print( 'POST-USER-INIT' )
        return

    def __init_singleton__(self):
        """ Subclasses can override this if needed. """
        # print( 'BASE-USER-INIT' )
        return


class Singleton( SingletonGemini ):
    pass
    


class SingletonGeminiThreads:
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None: 
                    print( 'PRE-SUPER' )
                    cls._instance = super().__new__(cls)
                    print( 'POST-SUPER' )
                    with ThreadPoolExecutor( max_workers = 1 ) as executor:
                        executor.submit( cls._instance.__init_singleton_internal__ ).result()
                    print( 'POST-INIT' )
        return cls._instance

    def __init_singleton_internal__(self):
        print( 'INIT CALLED' )
        if not self._initialized:
            self._initialized = True
            print( 'PRE-USER-INIT' )
            self.__init_singleton__()
            print( 'POST-USER-INIT' )
        return
    
    def __init_singleton__(self):
        """ Subclasses can override this if needed. """
        print( 'BASE-USER-INIT' )
        return
    
    


class SingletonGeminiAsyncio:
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            print( 'ABOUT TO LOCK' )
            with cls._lock:
                print( 'LOCK ACQUIRED' )
                if cls._instance is None: 
                    print( 'PRE-SUPER' )
                    cls._instance = super().__new__(cls)
                    print( 'POST-SUPER' )
                    asyncio.create_task( cls._instance.__init_singleton_internal__() ) 
                    print( 'POST-INIT' )
        return cls._instance

    async def __init_singleton_internal__ZZZ(self):
        print( 'INIT CALLED' )
        if not self._initialized:
            self._initialized = True
            print( 'PRE-USER-INIT' )
            await sync_to_async( self.__init_singleton__ )()
            print( 'POST-USER-INIT' )
        return
    
    def __init_singleton__(self):
        """ Subclasses can override this if needed. """
        print( 'BASE-USER-INIT' )
        return
    
