from asgiref.sync import sync_to_async

from .notification_manager import NotificationManager


class NotificationMixin:
    
    def notification_manager(self):
        if not hasattr( self, '_notification_manager' ):
            self._notification_manager = NotificationManager()
            self._notification_manager.ensure_initialized()
        return self._notification_manager
        
    async def notification_manager_async(self):
        if not hasattr( self, '_notification_manager' ):
            self._notification_manager = NotificationManager()
            await sync_to_async( self._notification_manager.ensure_initialized )()
        return self._notification_manager
    
