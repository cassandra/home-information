from asgiref.sync import sync_to_async
import asyncio
import logging

from .console_manager import ConsoleManager

logger = logging.getLogger(__name__)


class ConsoleMixin:
    
    def console_manager(self):
        if not hasattr( self, '_console_manager' ):
            self._console_manager = ConsoleManager()
            self._console_manager.ensure_initialized()
        return self._console_manager
        
    async def console_manager_async(self):
        if not hasattr( self, '_console_manager' ):
            self._console_manager = ConsoleManager()
            try:
                await asyncio.shield( sync_to_async( self._console_manager.ensure_initialized )())

            except asyncio.CancelledError:
                logger.warning( 'Console init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'Console init sync_to_async() exception! Handling gracefully. ({e})' )
                return None
            
        return self._console_manager
