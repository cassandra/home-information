from asgiref.sync import sync_to_async
import asyncio
import logging

from .hb_manager import HomeBoxManager

logger = logging.getLogger(__name__)


class HomeBoxMixin:

    def hb_manager(self) -> HomeBoxManager:
        if not hasattr( self, '_hb_manager' ):
            self._hb_manager = HomeBoxManager()
            self._hb_manager.ensure_initialized()
        return self._hb_manager

    async def hb_manager_async(self) -> HomeBoxManager:
        if not hasattr( self, '_hb_manager' ):
            self._hb_manager = HomeBoxManager()
            try:
                await asyncio.shield(
                    sync_to_async( self._hb_manager.ensure_initialized, thread_sensitive=True )())

            except asyncio.CancelledError:
                logger.warning( 'HomeBox init sync_to_async() was cancelled! Handling gracefully.' )
                return None

            except Exception as e:
                logger.warning(
                    f'HomeBox init sync_to_async() exception! Handling gracefully. ({e})' )
                return None

        return self._hb_manager
