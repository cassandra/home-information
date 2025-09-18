from asgiref.sync import sync_to_async
import asyncio
import logging

from .hass_manager import HassManager

logger = logging.getLogger(__name__)


class HassMixin:
    
    def hass_manager(self) -> HassManager:
        if not hasattr( self, '_hass_manager' ):
            self._hass_manager = HassManager()
            self._hass_manager.ensure_initialized()
        return self._hass_manager
        
    async def hass_manager_async(self) -> HassManager:
        if not hasattr( self, '_hass_manager' ):
            self._hass_manager = HassManager()
            try:
                await asyncio.shield( sync_to_async( self._hass_manager.ensure_initialized, thread_sensitive=True )())

            except asyncio.CancelledError:
                logger.warning( 'HAss init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'HAss init sync_to_async() exception! Handling gracefully. ({e})' )
                return None
            
        return self._hass_manager
