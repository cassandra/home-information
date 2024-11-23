import logging
from typing import Dict, List

from hi.apps.common.redis_client import get_redis_client
from hi.apps.monitor.transient_models import SensorResponse

from hi.integrations.core.integration_key import IntegrationKey

logger = logging.getLogger(__name__)


class SensorMonitorMixin:

    def add_to_sensor_response_history( self, sensor_response_list : List[ SensorResponse ] ):
        if not sensor_response_list:
            return

        # TODO: Implement me!
        return

    def add_latest_sensor_responses( self, sensor_response_list : List[ SensorResponse ] ):
        if not sensor_response_list:
            return
        
        redis_client = get_redis_client()
        cached_set = { self.to_sensor_value_cache_key(x.integration_key): str(x)
                       for x in sensor_response_list }
        redis_client.mset( cached_set )
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

        redis_client = get_redis_client()
        cache_keys = [ self.to_sensor_value_cache_key(x) for x in sensor_response_map.keys() ]
        integration_keys = list( sensor_response_map.keys() )
        cached_values = redis_client.mget( cache_keys )
        for integration_key, cached_value in zip( integration_keys, cached_values ):
            latest_sensor_response = sensor_response_map.get( integration_key )
            if cached_value:
                previous_sensor_response = SensorResponse.from_string( cached_value )
                if latest_sensor_response.value == previous_sensor_response.value:
                    continue
                
            changed_sensor_response_list.append( latest_sensor_response )
            continue
        
        self.add_to_sensor_response_history( changed_sensor_response_list )
        self.add_latest_sensor_responses( changed_sensor_response_list )
        if self.TRACE:
            logger.debug( f'HAss Changed: {len(changed_sensor_response_list)} of {len(sensor_response_map)}' )
        return

    def to_sensor_value_cache_key( self, integration_key : IntegrationKey ):
        return f'hi.sr.{integration_key}' 
    
