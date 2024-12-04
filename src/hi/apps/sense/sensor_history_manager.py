from asgiref.sync import sync_to_async
import logging
from typing import Dict, List

from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity

from .models import Sensor, SensorHistory
from .transient_models import SensorResponse

logger = logging.getLogger(__name__)


class SensorHistoryManager( Singleton ):
    
    def __init_singleton__( self ):
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
        await sync_to_async( SensorHistory.objects.bulk_create)( sensor_history_list )
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
