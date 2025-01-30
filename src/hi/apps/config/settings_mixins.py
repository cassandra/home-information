from asgiref.sync import sync_to_async
import asyncio
import logging

from .settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class SettingsMixin:
    
    def settings_manager(self):
        if not hasattr( self, '_settings_manager' ):
            self._settings_manager = SettingsManager()
            self._settings_manager.ensure_initialized()
        return self._settings_manager
        
    async def settings_manager_async(self):
        if not hasattr( self, '_settings_manager' ):
            self._settings_manager = SettingsManager()
            try:
                await asyncio.shield( sync_to_async( self._settings_manager.ensure_initialized,
                                                     thread_sensitive = True )())

            except asyncio.CancelledError:
                logger.warning( 'Settings init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'Settings init sync_to_async() exception! Handling gracefully. ({e})' )
                return None
            
        return self._settings_manager
