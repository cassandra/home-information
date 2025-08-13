from threading import Lock

# Global dictionary to store locks for each singleton class
_singleton_locks = {}


class Singleton:
    _instance = None
    _initialized = False

    def __new__(cls):
        # Get or create a lock specific to this class
        if cls not in _singleton_locks:
            _singleton_locks[cls] = Lock()
        
        if cls._instance is None:
            with _singleton_locks[cls]:
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
