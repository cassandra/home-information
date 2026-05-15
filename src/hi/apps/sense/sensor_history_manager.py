from asgiref.sync import sync_to_async
import logging
from typing import List

from hi.apps.common.singleton import Singleton

from .models import SensorHistory
from .transient_models import SensorResponse

logger = logging.getLogger(__name__)


class SensorHistoryMixin:
  
    def sensor_history_manager(self):
        if not hasattr( self, '_sensor_history_manager' ):
            self._sensor_history_manager = SensorHistoryManager()
            self._sensor_history_manager.ensure_initialized()
        return self._sensor_history_manager
        
    async def sensor_history_manager_async(self):
        if not hasattr( self, '_sensor_history_manager' ):
            self._sensor_history_manager = SensorHistoryManager()
            await sync_to_async( self._sensor_history_manager.ensure_initialized )()
        return self._sensor_history_manager

    
class SensorHistoryManager( Singleton ):
    
    def __init_singleton__( self ):
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        # Any future heavyweight initializations go here (e.g., any DB operations).
        self._was_initialized = True
        return

    async def add_to_sensor_history( self, sensor_response_list : List[ SensorResponse ] ):
        """ Side effect: Fills in the sensor_history_id for the SensorResponse instances """
        if not sensor_response_list:
            return

        # Build parallel lists to maintain the mapping between SensorResponse and SensorHistory
        sensor_history_list = list()
        response_indices = list()  # Track which responses need history

        for i, sensor_response in enumerate(sensor_response_list):
            if sensor_response.sensor and sensor_response.sensor.persist_history:
                sensor_history_list.append( sensor_response.to_sensor_history() )
                response_indices.append(i)
            continue

        created_histories = await self._bulk_create_sensor_history_async( sensor_history_list )

        # Update the sensor_history_id field in the original SensorResponse objects
        # Safety check: Only update if we got the expected number of results
        if created_histories and ( len(created_histories) == len(sensor_history_list) ):
            for i, history in enumerate(created_histories):
                response_index = response_indices[i]
                sensor_response_list[response_index].sensor_history_id = history.id
                continue
        elif created_histories:
            # Log warning if size mismatch - this shouldn't happen in normal operation
            logger.warning(
                f'SensorHistory bulk_create returned {len(created_histories)} objects '
                f'but expected {len(sensor_history_list)}. sensor_history_id not populated.'
            )

        return

    async def _bulk_create_sensor_history_async( self, sensor_history_list : List[ SensorHistory ] ):
        if not sensor_history_list:
            return []

        # bulk_create returns the list of created objects (with IDs on PostgreSQL and SQLite 3.35+)
        created_objects = await sync_to_async( SensorHistory.objects.bulk_create,
                                               thread_sensitive = True)( sensor_history_list )
        return created_objects

