import logging
from typing import Dict, List

from hi.apps.common.redis_client import get_redis_client
from hi.apps.common.singleton import Singleton

from hi.integrations.core.integration_key import IntegrationKey

from .sensor_history_manager import SensorHistoryManager
from .transient_models import SensorResponse

logger = logging.getLogger(__name__)


class SensorResponseManager( Singleton ):
    """
    Integrations are responsible for monitoring sensor values and
    normalizing them into SensorResponse objects.  This module take it from
    there to store these for tracking the latest state and sensor history.
    i.e., Integrations should be using this module to submit sensor
    values changes.

    N.B., Since the cached sensor responses are updated and fetched very
    frequently, a design principle of this module is to avoid any database
    queries.
    """

    LATEST_SENSOR_RESPONSE_HASH_NAME = 'hi.sr.all'  # Name of redis cache grouping
    
    def __init_singleton__( self ):
        self._redis_client = get_redis_client()
        self._sensor_history_manager = SensorHistoryManager()
        return
    
    def add_latest_sensor_responses( self, sensor_response_list : List[ SensorResponse ] ):
        if not sensor_response_list:
            return
        
        cached_set = { self.to_sensor_value_cache_key(x.integration_key): str(x)
                       for x in sensor_response_list }
        self._redis_client.hset( self.LATEST_SENSOR_RESPONSE_HASH_NAME, mapping = cached_set )
        return

    def update_with_latest_sensor_responses( self,
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

        cache_keys = [ self.to_sensor_value_cache_key(x) for x in sensor_response_map.keys() ]
        integration_keys = list( sensor_response_map.keys() )
        cached_values = self._redis_client.hmget( self.LATEST_SENSOR_RESPONSE_HASH_NAME, cache_keys )
        for integration_key, cached_value in zip( integration_keys, cached_values ):
            latest_sensor_response = sensor_response_map.get( integration_key )
            if cached_value:
                previous_sensor_response = SensorResponse.from_string( cached_value )
                if latest_sensor_response.value == previous_sensor_response.value:
                    continue
                
            changed_sensor_response_list.append( latest_sensor_response )
            continue
        
        self._sensor_history_manager.add_to_sensor_response_history( changed_sensor_response_list )
        self.add_latest_sensor_responses( changed_sensor_response_list )
        logger.debug( f'Sensor changed: {len(changed_sensor_response_list)} of {len(sensor_response_map)}' )
        return

    def get_latest_sensor_responses( self ) -> Dict[ IntegrationKey, SensorResponse ]:
        key_to_sensor_response_dict = self._redis_client.hgetall( self.LATEST_SENSOR_RESPONSE_HASH_NAME )
        key_to_sensor_response = { k: SensorResponse.from_string( v )
                                   for k, v in key_to_sensor_response_dict.items() }
        return { v.integration_key: v for k, v in key_to_sensor_response.items() }

    def to_sensor_value_cache_key( self, integration_key : IntegrationKey ):
        return f'hi.sr.{integration_key}' 
    
