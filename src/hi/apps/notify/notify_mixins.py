from asgiref.sync import sync_to_async
import asyncio
import logging

from .notification_manager import NotificationManager

logger = logging.getLogger(__name__)


class NotificationMixin:
    
    def notification_manager(self):
        if not hasattr( self, '_notification_manager' ):
            self._notification_manager = NotificationManager()
            self._notification_manager.ensure_initialized()
        return self._notification_manager
        
    async def notification_manager_async(self):
        if not hasattr( self, '_notification_manager' ):
            self._notification_manager = NotificationManager()
            try:
                await asyncio.shield( sync_to_async( self._notification_manager.ensure_initialized, thread_sensitive=True )())
   
            except asyncio.CancelledError:
                logger.warning( 'Notification init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'Notification init sync_to_async() exception! Handling gracefully. ({e})' )
                return None
              
        return self._notification_manager
    
