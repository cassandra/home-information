from asgiref.sync import sync_to_async
import asyncio
import logging

from .security_manager import SecurityManager

logger = logging.getLogger(__name__)


class SecurityMixin:
    
    def security_manager(self):
        if not hasattr( self, '_security_manager' ):
            self._security_manager = SecurityManager()
            self._security_manager.ensure_initialized()
        return self._security_manager
        
    async def security_manager_async(self):
        if not hasattr( self, '_security_manager' ):
            self._security_manager = SecurityManager()
            try:
                await asyncio.shield( sync_to_async( self._security_manager.ensure_initialized,
                                                     thread_sensitive = True )())

            except asyncio.CancelledError:
                logger.warning( 'Security init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'Security init sync_to_async() exception! Handling gracefully. ({e})' )
                return None

        return self._security_manager
