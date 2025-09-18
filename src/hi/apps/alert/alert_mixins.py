from asgiref.sync import sync_to_async
import asyncio
import logging

from .alert_manager import AlertManager

logger = logging.getLogger(__name__)


class AlertMixin:
    
    def alert_manager(self):
        if not hasattr( self, '_alert_manager' ):
            self._alert_manager = AlertManager()
            self._alert_manager.ensure_initialized()
        return self._alert_manager
        
    async def alert_manager_async(self):
        if not hasattr( self, '_alert_manager' ):
            self._alert_manager = AlertManager()
            try:
                await asyncio.shield( sync_to_async(self._alert_manager.ensure_initialized, thread_sensitive=True )())
                
            except asyncio.CancelledError:
                logger.warning( 'AlertMixin sync_to_async() was cancelled! Handling gracefully.' )
                return None

            except Exception as e:
                logger.warning( f'AlertMixin sync_to_async() exception! Handling gracefully: {e}' )
                return None
            
        return self._alert_manager
