from threading import Lock


class Singleton:
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None: 
                    cls._instance = super().__new__(cls)
                    cls._instance.__init_singleton__()
        return cls._instance

    def __init_singleton__(self):
        """ Subclasses can override this if needed. """
        return
    

class SingletonSync:
    """ Simpler version without multithread/asyncio initialization protections. """
    _instance = None

    def __new__( cls ):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__new__( cls )
            cls._instance.__init_singleton__()
        return cls._instance
