from asgiref.sync import sync_to_async

from .security_manager import SecurityManager


class SecurityMixin:
    
    def security_manager(self):
        if not hasattr( self, '_security_manager' ):
            self._security_manager = SecurityManager()
        return self._security_manager
        
    async def security_manager_async(self):
        if not hasattr( self, '_security_manager' ):
            self._security_manager = await sync_to_async( SecurityManager )()
        return self._security_manager
