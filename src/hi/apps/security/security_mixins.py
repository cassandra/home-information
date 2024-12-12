from asgiref.sync import sync_to_async

from .security_manager import SecurityManager


class SecurityMixin:
    
    def security_manager(self):
        if not hasattr( self, '_security_manager' ):
            self._security_manager = SecurityManager()
            self._security_manager.ensure_initialized()
        return self._security_manager
        
    async def security_manager_async(self):
        if not hasattr( self, '_security_manager' ):
            self._security_manager = await sync_to_async( SecurityManager )()
            await self._security_manager.ensure_initialized_async()
        return self._security_manager
