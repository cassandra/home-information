from .models import DatabaseLock


class DatabaseLockContext:

    def __init__( self, name, timeout_seconds = 300 ):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.lock = None

    def __enter__(self):
        self.lock = DatabaseLock( name = self.name )
        if self.lock.acquire( self.timeout_seconds ):
            return self.lock
        else:
            raise RuntimeError(f'Could not acquire lock: {self.name}')

    def __exit__( self, exc_type, exc_val, exc_tb ):
        if self.lock:
            self.lock.release()
        return
