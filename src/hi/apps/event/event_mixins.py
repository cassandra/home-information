from asgiref.sync import sync_to_async
import asyncio
import logging

from .event_manager import EventManager

logger = logging.getLogger(__name__)


class EventMixin:
    
    def event_manager(self):
        if not hasattr( self, '_event_manager' ):
            self._event_manager = EventManager()
            self._event_manager.ensure_initialized()
        return self._event_manager
        
    async def event_manager_async(self):
        if not hasattr( self, '_event_manager' ):
            self._event_manager = EventManager()
            try:
                await asyncio.shield( sync_to_async( self._event_manager.ensure_initialized,
                                                     thread_sensitive = True )())

            except asyncio.CancelledError:
                logger.warning( 'Event init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'Event init sync_to_async() exception! Handling gracefully. ({e})' )
                return None
                
        return self._event_manager
