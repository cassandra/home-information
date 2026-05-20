import asyncio
import logging

from .frigate_manager import FrigateManager

logger = logging.getLogger(__name__)


class FrigateMixin:
    """Manager-accessor mixin for views / sync / monitor / controller.

    Mirrors ``ZoneMinderMixin``: cache the manager on first access and
    return it on subsequent calls. The async variant uses
    ``asyncio.shield`` so a cancelled init doesn't leave the mixin
    holding a half-constructed manager reference.
    """

    def frigate_manager(self) -> FrigateManager:
        if not hasattr( self, '_frigate_manager' ):
            self._frigate_manager = FrigateManager()
            self._frigate_manager.ensure_initialized()
        return self._frigate_manager

    async def frigate_manager_async(self) -> FrigateManager:
        if not hasattr( self, '_frigate_manager' ):
            self._frigate_manager = FrigateManager()
            try:
                await asyncio.shield( self._frigate_manager.ensure_initialized_async() )
            except asyncio.CancelledError:
                logger.warning( 'Frigate init ensure_initialized_async cancelled.' )
                return None
            except Exception as e:
                logger.warning( f'Frigate init failed: {e}' )
                return None
        return self._frigate_manager
