from asgiref.sync import sync_to_async
import asyncio
from cachetools import TTLCache
import logging
from typing import Dict, List, Optional

from django.conf import settings

from hi.apps.common.redis_client import get_redis_client
from hi.apps.common.singleton import Singleton
from hi.apps.event.event_mixins import EventMixin
from hi.apps.event.transient_models import EntityStateTransition

from hi.integrations.transient_models import IntegrationKey
from hi.testing.dev_overrides import DevOverrideManager

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

    def invalidate_local_sensor_cache(self):
        """Drop the in-process IntegrationKey → Sensor lookup cache
        and mark the in-memory latest-responses map stale. Leaves
        the Redis-backed sensor response data untouched (its keys
        are integration_key strings, which are stable across
        re-import).

        Called by the integration framework after any operation that
        creates, refreshes, or removes Sensors with integration_keys
        (sync, disable). Symmetric with
        ``IntegrationMetadataCache.invalidate()``.

        Necessary because ``_sensor_cache`` holds Python ``Sensor``
        model instances keyed by integration_key. After re-import
        the integration_key is reused (it's derived from the
        external ID, which doesn't change) but the underlying DB
        row has a new PK and a new ``entity_state`` link. Without
        invalidation, the polling read path returns the stale
        Sensor object, the status map is keyed by the deleted
        EntityState's PK, and the client's DOM (rendered with new
        PKs) silently fails to update for up to the 300s TTL."""
        self._sensor_cache.clear()
        self._latest_sensor_data_dirty = True
        return
    
    async def update_with_latest_sensor_responses(
            self,
            sensor_response_map : Dict[ IntegrationKey, SensorResponse ] ):
        """Single-response-per-key entry point. The common case — one
        transition per sensor per poll cycle. Callers whose poll
        window may carry multiple transitions for the same sensor
        (e.g., Frigate switching object class within one cycle)
        should call :meth:`update_with_latest_sensor_response_lists`
        directly instead of forcing their multiple responses through
        this dict shape (which would collapse them on overwrite).

        Thin adapter: wraps each value in a single-element list and
        delegates to the list-shape entry point."""
        if not sensor_response_map:
            return
        await self.update_with_latest_sensor_response_lists(
            sensor_response_list_map = {
                key: [ response ]
                for key, response in sensor_response_map.items()
            },
        )
        return

    async def update_with_latest_sensor_response_lists(
            self,
            sensor_response_list_map : Dict[ IntegrationKey, List[ SensorResponse ] ] ):
        """Multi-response-per-key entry point.

        Each list is treated as chronologically ordered (sorted by
        timestamp internally as a safety net). Each response is
        compared against the running previous state — initially the
        cached latest from Redis, then the prior response in the
        same list. Equal-value responses are skipped; changes are
        recorded as both a history row and an entity-state transition.
        """
        if not sensor_response_list_map:
            return
        changed_sensor_response_list = list()
        entity_state_transition_list = list()

        integration_keys = list( sensor_response_list_map.keys() )
        list_cache_keys = [
            self.to_sensor_response_list_cache_key( k ) for k in integration_keys
        ]

        pipeline = self._redis_client.pipeline()
        for list_cache_key in list_cache_keys:
            pipeline.lindex( list_cache_key, 0 )
            continue
        cached_values = pipeline.execute()

        for integration_key, cached_value in zip( integration_keys, cached_values ):
            response_list = sorted(
                sensor_response_list_map.get( integration_key ) or [],
                key = lambda r : r.timestamp,
            )

            if cached_value:
                previous_sensor_response = SensorResponse.from_string( cached_value )
            else:
                previous_sensor_response = None

            for latest_sensor_response in response_list:
                if ( previous_sensor_response is not None
                     and latest_sensor_response.value == previous_sensor_response.value ):
                    if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                        sensor = latest_sensor_response.sensor
                        DevOverrideManager.trace_state(
                            'hi.sensor.skip',
                            integration_name = integration_key.integration_name,
                            hi_entity_state_id = sensor.entity_state.id if sensor else None,
                            hi_value = latest_sensor_response.value,
                        )
                    continue

                if previous_sensor_response is not None:
                    entity_state_transition = await self._create_entity_state_transition(
                        previous_sensor_response = previous_sensor_response,
                        latest_sensor_response = latest_sensor_response,
                    )
                    if entity_state_transition:
                        entity_state_transition_list.append( entity_state_transition )

                    if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                        sensor = latest_sensor_response.sensor
                        DevOverrideManager.trace_state(
                            'hi.sensor.commit',
                            integration_name = integration_key.integration_name,
                            hi_entity_state_id = sensor.entity_state.id if sensor else None,
                            hi_value = f'{previous_sensor_response.value} -> {latest_sensor_response.value}',
                        )
                else:
                    if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                        sensor = latest_sensor_response.sensor
                        DevOverrideManager.trace_state(
                            'hi.sensor.first',
                            integration_name = integration_key.integration_name,
                            hi_entity_state_id = sensor.entity_state.id if sensor else None,
                            hi_value = latest_sensor_response.value,
                        )

                changed_sensor_response_list.append( latest_sensor_response )
                previous_sensor_response = latest_sensor_response
                continue
            continue

        await self._add_latest_sensor_responses( changed_sensor_response_list )

        event_manager = await self.event_manager_async()
        if not event_manager:
            return

        await event_manager.add_entity_state_transitions( entity_state_transition_list )

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
    
    def get_latest_sensor_response_map(
            self, integration_keys : List[ IntegrationKey ],
    ) -> Dict[ IntegrationKey, Optional[ SensorResponse ] ]:
        if not integration_keys:
            return {}
        list_cache_keys = [ self.to_sensor_response_list_cache_key( k ) for k in integration_keys ]
        pipeline = self._redis_client.pipeline()
        for list_cache_key in list_cache_keys:
            pipeline.lindex( list_cache_key, 0 )
            continue
        cached_values = pipeline.execute()
        result : Dict[ IntegrationKey, Optional[ SensorResponse ] ] = {}
        for integration_key, cached_value in zip( integration_keys, cached_values ):
            result[ integration_key ] = (
                SensorResponse.from_string( cached_value ) if cached_value else None
            )
            continue
        return result

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

        await self._add_sensors( sensor_response_list = sensor_response_list )

        sensor_history_manager = await self.sensor_history_manager_async()

        # This also has side effect of populating sensor_history_id
        await sensor_history_manager.add_to_sensor_history(
            sensor_response_list = sensor_response_list,
        )

        pipeline = self._redis_client.pipeline()
        for sensor_response in sensor_response_list:
            list_cache_key = self.to_sensor_response_list_cache_key( sensor_response.integration_key )
            cache_value = str(sensor_response)
            pipeline.lpush( list_cache_key, cache_value )
            pipeline.ltrim( list_cache_key, 0, self.SENSOR_RESPONSE_LIST_SIZE - 1 )
            pipeline.sadd( self.SENSOR_RESPONSE_LIST_SET_KEY, list_cache_key )
            continue
        pipeline.execute()

        # Flag the in-memory map stale only after Redis is
        # updated. Setting it earlier opens a window where a
        # concurrent reader rebuilds the map from pre-update
        # Redis and clears the flag, leaving the in-memory map
        # stuck on the stale value until the next commit. A
        # reader that runs between ``pipeline.execute()`` and
        # this assignment can still see one stale poll, but
        # next-call recovery is automatic.
        self._latest_sensor_data_dirty = True
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
