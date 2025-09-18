import asyncio
import logging

from .zm_manager import ZoneMinderManager

logger = logging.getLogger(__name__)


class ZoneMinderMixin:
    
    def zm_manager(self) -> ZoneMinderManager:
        if not hasattr( self, '_zm_manager' ):
            self._zm_manager = ZoneMinderManager()
            self._zm_manager.ensure_initialized()
        return self._zm_manager
        
    async def zm_manager_async(self) -> ZoneMinderManager:
        if not hasattr( self, '_zm_manager' ):
            self._zm_manager = ZoneMinderManager()
            try:
                # ensure_initialized_async() already handles thread_sensitive=True internally
                await asyncio.shield(self._zm_manager.ensure_initialized_async())
            except asyncio.CancelledError:
                logger.warning( 'ZM init ensure_initialized_async() was cancelled! Handling gracefully.')
                return None
            except Exception as e:
                logger.warning( f'ZM init ensure_initialized_async() exception! Handling gracefully. ({e})' )
                return None

        return self._zm_manager
