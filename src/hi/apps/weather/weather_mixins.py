from asgiref.sync import sync_to_async
import asyncio
import logging

logger = logging.getLogger(__name__)


class WeatherMixin:
    
    def weather_manager(self):
        from .weather_manager import WeatherManager
        if not hasattr( self, '_weather_manager' ):
            self._weather_manager = WeatherManager()
            self._weather_manager.ensure_initialized()
        return self._weather_manager
        
    async def weather_manager_async(self):
        from .weather_manager import WeatherManager
        if not hasattr( self, '_weather_manager' ):
            self._weather_manager = WeatherManager()
            try:
                await asyncio.shield( sync_to_async( self._weather_manager.ensure_initialized,
                                                     thread_sensitive = True )())

            except asyncio.CancelledError:
                logger.warning( 'Weather init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'Weather init sync_to_async() exception! Handling gracefully. ({e})' )
                return None
            
        return self._weather_manager
