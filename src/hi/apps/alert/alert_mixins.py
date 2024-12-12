from asgiref.sync import sync_to_async

from .alert_manager import AlertManager


class AlertMixin:
    
    def alert_manager(self):
        if not hasattr( self, '_alert_manager' ):
            self._alert_manager = AlertManager()
            return self._alert_manager
        
    async def alert_manager_async(self):
        if not hasattr( self, '_alert_manager' ):
            self._alert_manager = await sync_to_async( AlertManager )()
        return self._alert_manager
    
    
