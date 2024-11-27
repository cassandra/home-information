from asgiref.sync import sync_to_async
import logging
from typing import List

from hi.apps.common.singleton import Singleton

from .models import SensorHistory
from .transient_models import SensorResponse

logger = logging.getLogger(__name__)


class SensorHistoryManager( Singleton ):
    
    def __init_singleton__( self ):
        return
    
    async def add_to_sensor_response_history( self, sensor_response_list : List[ SensorResponse ] ):
        if not sensor_response_list:
            return

        sensor_history_list = list()
        for sensor_response in sensor_response_list:
            if sensor_response.sensor and sensor_response.sensor.persist_history:
                sensor_history_list.append(
                    SensorHistory(
                        sensor = sensor_response.sensor,
                        value = sensor_response.value[0:255],
                        response_datetime = sensor_response.timestamp,
                    )
                )
            continue

        await self._bulk_create_sensor_history_async( sensor_history_list )
        return
        
    async def _bulk_create_sensor_history_async( self, sensor_history_list : List[ SensorHistory ] ):
        await sync_to_async( SensorHistory.objects.bulk_create)( sensor_history_list )
        return
