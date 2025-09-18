from asgiref.sync import sync_to_async
import logging
from typing import Dict, List

from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity

from .models import Sensor, SensorHistory
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
        if not sensor_response_list:
            return

        sensor_history_list = list()
        for sensor_response in sensor_response_list:
            if sensor_response.sensor and sensor_response.sensor.persist_history:
                sensor_history_list.append( sensor_response.to_sensor_history() )
            continue

        await self._bulk_create_sensor_history_async( sensor_history_list )
        return
        
    async def _bulk_create_sensor_history_async( self, sensor_history_list : List[ SensorHistory ] ):
        if not sensor_history_list:
            logger.info(f'SENSOR_HISTORY: Skipped bulk_create. No records')
            return
        
        logger.info(f'SENSOR_HISTORY: Starting bulk_create of {len(sensor_history_list)} sensor history records')
        await sync_to_async( SensorHistory.objects.bulk_create,
                             thread_sensitive = True)( sensor_history_list )
        logger.info(f'SENSOR_HISTORY: Completed bulk_create of {len(sensor_history_list)} sensor history records')
        return

    def get_latest_entity_sensor_history( self,
                                          entity     : Entity,
                                          max_items  : int    = 5 ) -> Dict[ Sensor, List[ SensorHistory ] ]:

        entity_state_list = list( entity.states.all() )
        entity_state_delegations = entity.entity_state_delegations.select_related('entity_state').all()
        entity_state_list.extend([ x.entity_state for x in entity_state_delegations ])

        sensor_list = list()
        for entity_state in entity_state_list:
            sensor_list.extend( entity_state.sensors.all() )
            continue

        sensor_history_list_map = dict()
        for sensor in sensor_list:
            sensor_history_list = SensorHistory.objects.filter( sensor = sensor )[0:max_items]
            sensor_history_list_map[sensor] = sensor_history_list
            continue

        return sensor_history_list_map
