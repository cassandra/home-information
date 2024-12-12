from asgiref.sync import sync_to_async

from .sensor_response_manager import SensorResponseManager


class SensorResponseMixin:
    
    def sensor_response_manager(self):
        if not hasattr( self, '_sensor_response_manager' ):
            self._sensor_response_manager = SensorResponseManager()
        return self._sensor_response_manager
        
    async def sensor_response_manager_async(self):
        if not hasattr( self, '_sensor_response_manager' ):
            self._sensor_response_manager = await sync_to_async( SensorResponseManager )()
        return self._sensor_response_manager
