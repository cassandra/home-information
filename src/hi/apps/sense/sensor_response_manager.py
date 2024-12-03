from asgiref.sync import sync_to_async
from cachetools import TTLCache
import logging
from typing import Dict, List

from hi.apps.common.redis_client import get_redis_client
from hi.apps.common.singleton import Singleton
from hi.integrations.core.integration_key import IntegrationKey

from .models import Sensor
from .sensor_history_manager import SensorHistoryManager
from .transient_models import SensorResponse

logger = logging.getLogger(__name__)


class SensorResponseManager( Singleton ):
    """
    Integrations are responsible for monitoring sensor values and
    normalizing them into SensorResponse objects.  This module take it from
    there to store these for tracking the latest state.  i.e., Integrations
    should be using this module to submit sensor values changes.

    N.B., Since the cached sensor responses are updated and fetched very
    frequently, a design principle of this module is to avoid any database
    queries.

    Caching Strategy:

      - For each sensor, we will cache the latest 'N' sensor responses in a
        Redis list (using LPUSH and LTRIM list Redis functions).

      - Then lists' cache keys are baseon the sensor's integration key.

      - We will keep all the list cache keys in a Redis set so that we can
        easily fetch them all without needing to know all the integration
        keys (using the SADD and SMEMBERS Redis functions).
    """
    SENSOR_RESPONSE_LIST_SIZE = 5
    SENSOR_RESPONSE_LIST_SET_KEY = 'hi.sr.list.keys'

    def __init_singleton__( self ):
        self._redis_client = get_redis_client()
        self._sensor_history_manager = SensorHistoryManager()
        self._sensor_cache = TTLCache( maxsize = 1000, ttl = 300 )
        return

    async def update_with_latest_sensor_responses(
            self,
            sensor_response_map : Dict[ IntegrationKey, SensorResponse ] ):
        """
        Used when states are polled and get current state at a point in time
        which may or may not represent a change in state.  We only want to
        keep the history of changed states, so we fetch previous values to
        detect changes.
        """
        if not sensor_response_map:
            return
        changed_sensor_response_list = list()

        list_cache_keys = [ self.to_sensor_response_list_cache_key(x) for x in sensor_response_map.keys() ]
        integration_keys = list( sensor_response_map.keys() )

        pipeline = self._redis_client.pipeline()
        for list_cache_key in list_cache_keys:
            pipeline.lindex( list_cache_key, 0 )
            continue
        cached_values = pipeline.execute()

        for integration_key, cached_value in zip( integration_keys, cached_values ):
            latest_sensor_response = sensor_response_map.get( integration_key )

            if cached_value:
                previous_sensor_response = SensorResponse.from_string( cached_value )
                if latest_sensor_response.value == previous_sensor_response.value:
                    continue
                
            changed_sensor_response_list.append( latest_sensor_response )
            continue
        
        await self._add_latest_sensor_responses( changed_sensor_response_list )
        logger.debug( f'Sensor changed: {len(changed_sensor_response_list)} of {len(sensor_response_map)}' )
        return

    def get_all_latest_sensor_responses( self ) -> Dict[ Sensor, List[ SensorResponse ] ]:

        list_cache_keys = self._redis_client.smembers( self.SENSOR_RESPONSE_LIST_SET_KEY )

        pipeline = self._redis_client.pipeline()
        for list_cache_key in list_cache_keys:
            pipeline.lrange( list_cache_key, 0, -1 )
            continue
        cached_list_list = pipeline.execute()

        sensor_response_list_map = dict()
        for cached_list in cached_list_list:
            if not cached_list:
                continue
            sensor_response_list = [ SensorResponse.from_string( x ) for x in cached_list ]
            if sensor_response_list:
                sensor = self._get_sensor( integration_key = sensor_response_list[0].integration_key )
                if sensor:
                    
                    sensor_response_list_map[sensor] = sensor_response_list
            continue

        return sensor_response_list_map
    
    def get_latest_sensor_responses( self,
                                     sensor_list : List[ Sensor ] ) -> Dict[ Sensor, List[ SensorResponse ] ]:
        
        list_cache_keys = [ self.to_sensor_response_list_cache_key( x.integration_key )
                            for x in sensor_list ]
        
        pipeline = self._redis_client.pipeline()
        for list_cache_key in list_cache_keys:
            pipeline.lrange( list_cache_key, 0, -1 )
            continue
        cached_list_list = pipeline.execute()

        sensor_response_list_map = dict()
        for sensor, cached_list in zip( sensor_list, cached_list_list ):
            sensor_response_list = [ SensorResponse.from_string( x ) for x in cached_list ]
            for sensor_response in sensor_response_list:
                sensor_response.sensor = sensor
                continue
            sensor_response_list_map[sensor] = sensor_response_list
            continue

        return sensor_response_list_map
    
    async def _add_latest_sensor_responses( self, sensor_response_list : List[ SensorResponse ] ):
        if not sensor_response_list:
            return

        pipeline = self._redis_client.pipeline()
        for sensor_response in sensor_response_list:
            list_cache_key = self.to_sensor_response_list_cache_key( sensor_response.integration_key )
            cache_value = str(sensor_response)
            pipeline.lpush( list_cache_key, cache_value )
            pipeline.ltrim( list_cache_key, 0, self.SENSOR_RESPONSE_LIST_SIZE - 1 )
            pipeline.sadd( self.SENSOR_RESPONSE_LIST_SET_KEY, list_cache_key )
            continue
        pipeline.execute()

        await self._add_sensors( sensor_response_list = sensor_response_list )
        await self._sensor_history_manager.add_to_sensor_response_history(
            sensor_response_list = sensor_response_list,
        )        
        return
    
    def to_sensor_response_list_cache_key( self, integration_key : IntegrationKey ) -> str:
        return f'hi.sr.latest.{integration_key}' 
    
    async def _add_sensors( self, sensor_response_list : List[ SensorResponse ] ):
        for sensor_response in sensor_response_list:
            if sensor_response.sensor is None:
                sensor_response.sensor = await sync_to_async(
                    self._get_sensor )( integration_key = sensor_response.integration_key )
            continue
        return
        
    def _get_sensor( self, integration_key : IntegrationKey ):
        if integration_key not in self._sensor_cache:
            sensor_queryset = Sensor.objects.filter_by_integration_key(
                integration_key = integration_key,
            ).select_related('entity_state')
            if not sensor_queryset.exists():
                return None
            self._sensor_cache[integration_key] = sensor_queryset[0]

        return self._sensor_cache[integration_key]
        
