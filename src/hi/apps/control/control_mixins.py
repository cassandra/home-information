from asgiref.sync import sync_to_async

from .controller_manager import ControllerManager


class ControllerMixin:
    
    def controller_manager(self):
        if not hasattr( self, '_controller_manager' ):
            self._controller_manager = ControllerManager()
            self._controller_manager.ensure_initialized()
        return self._controller_manager
        
    async def controller_manager_async(self):
        if not hasattr( self, '_controller_manager' ):
            self._controller_manager = ControllerManager()
            await sync_to_async( self._controller_manager.ensure_initialized )()
        return self._controller_manager
