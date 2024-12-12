from asgiref.sync import sync_to_async

from .event_manager import EventManager


class EventMixin:
    
    def event_manager(self):
        if not hasattr( self, '_event_manager' ):
            self._event_manager = EventManager()
            self._event_manager.ensure_initialized()
        return self._event_manager
        
    async def event_manager_async(self):
        if not hasattr( self, '_event_manager' ):
            self._event_manager = EventManager()
            await sync_to_async( self._event_manager.ensure_initialized )()
        return self._event_manager
