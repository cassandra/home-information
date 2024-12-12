from asgiref.sync import sync_to_async

from .zm_manager import ZoneMinderManager


class ZoneMinderMixin:
    
    def zm_manager(self):
        if not hasattr( self, '_zm_manager' ):
            self._zm_manager = ZoneMinderManager()
        return self._zm_manager
        
    async def zm_manager_async(self):
        if not hasattr( self, '_zm_manager' ):
            self._zm_manager = await sync_to_async( ZoneMinderManager )()
        return self._zm_manager
