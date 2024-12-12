from asgiref.sync import sync_to_async

from .hass_manager import HassManager


class HassMixin:
    
    def hass_manager(self):
        if not hasattr( self, '_hass_manager' ):
            self._hass_manager = HassManager()
        return self._hass_manager
        
    async def hass_manager_async(self):
        if not hasattr( self, '_hass_manager' ):
            self._hass_manager = await sync_to_async( HassManager )()
        return self._hass_manager
