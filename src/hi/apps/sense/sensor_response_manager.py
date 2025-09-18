from asgiref.sync import sync_to_async
import asyncio
from cachetools import TTLCache
import logging
from typing import Dict, List

from hi.apps.common.redis_client import get_redis_client
from hi.apps.common.singleton import Singleton
from hi.apps.event.event_mixins import EventMixin
from hi.apps.event.transient_models import EntityStateTransition

from hi.integrations.transient_models import IntegrationKey

from .models import Sensor
from .sensor_history_manager import SensorHistoryMixin
from .transient_models import SensorResponse

logger = logging.getLogger(__name__)


class SensorResponseMixin:
    
    def sensor_response_manager(self):
        if not hasattr( self, '_sensor_response_manager' ):
            self._sensor_response_manager = SensorResponseManager()
            self._sensor_response_manager.ensure_initialized()
        return self._sensor_response_manager
        
    async def sensor_response_manager_async(self):
        if not hasattr( self, '_sensor_response_manager' ):
            self._sensor_response_manager = SensorResponseManager()
            try:
                await asyncio.shield( sync_to_async( self._sensor_response_manager.ensure_initialized, thread_sensitive=True )())
 
            except asyncio.CancelledError:
                logger.warning( 'SensorResponse init sync_to_async() was cancelled! Handling gracefully.')
                return None

            except Exception as e:
                logger.warning( f'SensorResponse init sync_to_async() exception! Handling gracefully. ({e})' )
                return None
               
        return self._sensor_response_manager


class SensorResponseManager( Singleton, SensorHistoryMixin, EventMixin ):
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
        self._sensor_cache = TTLCache( maxsize = 1000, ttl = 300 )  # Is thread-safe
        self._latest_sensor_data_dirty = True
        self._sensor_response_list_map = dict()
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        # Any future heavyweight initializations go here (e.g., any DB operations).
        self._was_initialized = True
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
        entity_state_transition_list = list()

        logger.info( f'========= START update_with_latest_sensor_responses() ' )
        
        list_cache_keys = [ self.to_sensor_response_list_cache_key(x) for x in sensor_response_map.keys() ]
        integration_keys = list( sensor_response_map.keys() )

        logger.info( f'Start cached values redis pipeline: {len(list_cache_keys)} keys' )
        pipeline = self._redis_client.pipeline()
        for list_cache_key in list_cache_keys:
            pipeline.lindex( list_cache_key, 0 )
            continue
        cached_values = pipeline.execute()
        logger.info( f'End cached values redis pipeline: {len(cached_values)} values' )

        logger.info( f'Start create changed states: {len(integration_keys)} sensors' )
        for integration_key, cached_value in zip( integration_keys, cached_values ):
            latest_sensor_response = sensor_response_map.get( integration_key )

            if cached_value:
                previous_sensor_response = SensorResponse.from_string( cached_value )
                if latest_sensor_response.value == previous_sensor_response.value:
                    continue

                entity_state_transition = await self._create_entity_state_transition(
                    previous_sensor_response = previous_sensor_response,
                    latest_sensor_response = latest_sensor_response,
                )
                logger.info( f'End create transiiton: {integration_key}' )
                if entity_state_transition:
                    entity_state_transition_list.append( entity_state_transition )
                
            changed_sensor_response_list.append( latest_sensor_response )
            continue
        logger.info( f'End create changed states: {len(changed_sensor_response_list)} changes' )

        await self._add_latest_sensor_responses( changed_sensor_response_list )

        event_manager = await self.event_manager_async()
        if not event_manager:
            return

        logger.info( f'Start add events: {len(entity_state_transition_list)} transitions' )
        await event_manager.add_entity_state_transitions( entity_state_transition_list )

        logger.info( f'End add events: {len(entity_state_transition_list)} transitions' )
        return

    def get_all_latest_sensor_responses( self ) -> Dict[ Sensor, List[ SensorResponse ] ]:
        """
        Since we want to support having many consoles/clients, with responsive
        short polling intervals, we use an optimization for this frequently
        requests status data by keeping a "dirty" flag and returning the
        same data until new data comes in.
        """
        if self._latest_sensor_data_dirty:
            self._sensor_response_list_map = self._create_all_latest_sensor_responses()
        self._latest_sensor_data_dirty = False
        return self._sensor_response_list_map
        
    def _create_all_latest_sensor_responses( self ) -> Dict[ Sensor, List[ SensorResponse ] ]:

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

        self._latest_sensor_data_dirty = True

        logger.info( f'Start add values redis pipeline: {len(sensor_response_list)} responses' )
        pipeline = self._redis_client.pipeline()
        for sensor_response in sensor_response_list:
            list_cache_key = self.to_sensor_response_list_cache_key( sensor_response.integration_key )
            cache_value = str(sensor_response)
            pipeline.lpush( list_cache_key, cache_value )
            pipeline.ltrim( list_cache_key, 0, self.SENSOR_RESPONSE_LIST_SIZE - 1 )
            pipeline.sadd( self.SENSOR_RESPONSE_LIST_SET_KEY, list_cache_key )
            continue
        pipeline.execute()
        logger.info( f'End add values redis pipeline: {len(sensor_response_list)} responses' )

        logger.info( f'Start add responses: {len(sensor_response_list)} total' )
        await self._add_sensors( sensor_response_list = sensor_response_list )
        logger.info( f'End add responses: {len(sensor_response_list)} total' )

        sensor_history_manager = await self.sensor_history_manager_async()

        logger.info( f'Start add history: {len(sensor_response_list)} total' )
        await sensor_history_manager.add_to_sensor_history(
            sensor_response_list = sensor_response_list,
        )        
        logger.info( f'End add history: {len(sensor_response_list)} total' )
        return
    
    def to_sensor_response_list_cache_key( self, integration_key : IntegrationKey ) -> str:
        return f'hi.sr.latest.{integration_key}' 
    
    async def _add_sensors( self, sensor_response_list : List[ SensorResponse ] ):
        for sensor_response in sensor_response_list:
            if sensor_response.sensor is None:
                sensor_response.sensor = await sync_to_async( self._get_sensor,
                                                              thread_sensitive = True )(
                    integration_key = sensor_response.integration_key,
                )
            continue
        return
    
    async def _create_entity_state_transition( self,
                                               previous_sensor_response  : SensorResponse,
                                               latest_sensor_response    : SensorResponse ):
        sensor = await self._get_sensor_async(
            integration_key = latest_sensor_response.integration_key,
        )
        if not sensor:
            return None
        return EntityStateTransition(
            entity_state = sensor.entity_state,
            latest_sensor_response = latest_sensor_response,
            previous_value = previous_sensor_response.value,
        )

    async def _get_sensor_async( self, integration_key : IntegrationKey ):
        return await sync_to_async( self._get_sensor,
                                    thread_sensitive = True )(
            integration_key = integration_key,
        )
    
    def _get_sensor( self, integration_key : IntegrationKey ):
        if integration_key not in self._sensor_cache:
            sensor_queryset = Sensor.objects.filter_by_integration_key(
                integration_key = integration_key,
            ).select_related('entity_state')
            if not sensor_queryset.exists():
                return None
            self._sensor_cache[integration_key] = sensor_queryset[0]

        return self._sensor_cache[integration_key]
