from asgiref.sync import sync_to_async

from .hass_manager import HassManager


class HassMixin:
    
    def hass_manager(self) -> HassManager:
        if not hasattr( self, '_hass_manager' ):
            self._hass_manager = HassManager()
            self._hass_manager.ensure_initialized()
        return self._hass_manager
        
    async def hass_manager_async(self) -> HassManager:
        if not hasattr( self, '_hass_manager' ):
            self._hass_manager = HassManager()
            await sync_to_async( self._hass_manager.ensure_initialized )()
        return self._hass_manager
