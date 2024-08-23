from .models import DatabaseLock


class ExclusionLockContext:
    """ Basic mutual exclusion lock using the database. """
    
    def __init__( self, name, timeout_seconds = 300 ):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.lock = None

    def __enter__(self):

        self.lock = DatabaseLock.acquire( name = self.name,
                                          timeout_seconds = self.timeout_seconds,
                                          for_initialization = False )
        if self.lock:
            return self.lock
        else:
            raise RuntimeError(f'Could not acquire lock: {self.name}')

    def __exit__( self, exc_type, exc_val, exc_tb ):
        if self.lock:
            self.lock.release()
        return


class InitializationLockContext:
    """
    Grabs a lock for a specific duration so that only one thread performs
    an operation in the given time period.
    """
    
    def __init__( self, name, timeout_seconds = 300 ):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.lock = None

    def __enter__(self):

        self.lock = DatabaseLock.acquire( name = self.name,
                                          timeout_seconds = self.timeout_seconds,
                                          for_initialization = True )
        if self.lock:
            return self.lock
        else:
            raise RuntimeError(f'Could not acquire lock: {self.name}')

    def __exit__( self, exc_type, exc_val, exc_tb ):
        if self.lock:
            self.lock.mark_initialized()
        return
    
