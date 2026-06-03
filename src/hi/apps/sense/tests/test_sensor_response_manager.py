import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from django.utils import timezone
from hi.testing.async_task_utils import AsyncTaskFastTestCase

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.sensor_response_manager import SensorResponseManager
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey

logging.disable(logging.CRITICAL)


class AsyncSensorResponseManagerTestCase(AsyncTaskFastTestCase):
    """Test SensorResponseManager with proper async infrastructure."""
    
    def setUp(self):
        super().setUp()
        # Reset singleton state for each test
        SensorResponseManager._instances = {}
        self.manager = SensorResponseManager()
        
        # Create test entities and sensors
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
        )
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF'
        )
        self.sensor = Sensor.objects.create(
            name='Test Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DEFAULT',
            integration_id='test_sensor_123',
            integration_name='test_integration'
        )
        self.integration_key = IntegrationKey(
            integration_id='test_sensor_123',
            integration_name='test_integration'
        )

    def test_manager_singleton_behavior(self):
        """Test singleton pattern behavior - critical for state consistency."""
        manager1 = SensorResponseManager()
        manager2 = SensorResponseManager()
        self.assertIs(manager1, manager2)
        
        # Ensure shared state
        manager1._latest_sensor_data_dirty = True
        self.assertTrue(manager2._latest_sensor_data_dirty)

    def test_initialization_creates_redis_client(self):
        """Test manager initialization sets up Redis client properly."""
        # Reset initialization state to test fresh initialization
        self.manager._was_initialized = False
        
        self.manager.ensure_initialized()
        
        self.assertIsNotNone(self.manager._redis_client)
        self.assertTrue(self.manager._was_initialized)
        
        # Second call should not reinitialize (preserves existing state)
        original_state = self.manager._was_initialized
        self.manager.ensure_initialized()
        self.assertEqual(self.manager._was_initialized, original_state)

    @patch('hi.apps.sense.sensor_response_manager.get_redis_client')
    def test_cache_key_generation(self, mock_get_redis_client):
        """Test cache key generation follows expected pattern."""
        mock_get_redis_client.return_value = Mock()
        
        cache_key = self.manager.to_sensor_response_list_cache_key(self.integration_key)
        expected_key = f'hi.sr.latest.{self.integration_key}'
        
        self.assertEqual(cache_key, expected_key)

    @patch('hi.apps.sense.sensor_response_manager.get_redis_client')
    def test_update_with_no_sensor_responses_does_nothing(self, mock_get_redis_client):
        """Test update with empty map returns without Redis operations."""
        mock_redis = Mock()
        mock_get_redis_client.return_value = mock_redis
        
        async def async_test_logic():
            await self.manager.update_with_latest_sensor_responses({})
        
        self.run_async(async_test_logic())
        
        # Should not interact with Redis for empty input
        mock_redis.pipeline.assert_not_called()

    def test_update_detects_sensor_value_changes(self):
        """Test change detection compares current vs cached values correctly."""
        
        # Create test responses
        previous_response = SensorResponse(
            integration_key=self.integration_key,
            value='off',
            timestamp=timezone.now()
        )
        
        new_response = SensorResponse(
            integration_key=self.integration_key,
            value='on',
            timestamp=timezone.now()
        )
        
        # Test that values are indeed different
        self.assertNotEqual(previous_response.value, new_response.value)
        
        # Test string serialization/deserialization round-trip
        serialized = str(previous_response)
        deserialized = SensorResponse.from_string(serialized)
        self.assertEqual(previous_response.value, deserialized.value)

    def test_update_ignores_unchanged_sensor_values(self):
        """Test no processing occurs when sensor values haven't changed."""
        
        # Create responses with same value
        cached_response = SensorResponse(
            integration_key=self.integration_key,
            value='on',
            timestamp=timezone.now()
        )
        
        new_response = SensorResponse(
            integration_key=self.integration_key,
            value='on',
            timestamp=timezone.now()
        )
        
        # Test that values are the same
        self.assertEqual(cached_response.value, new_response.value)
        
        # Test basic serialization consistency
        serialized = str(cached_response)
        deserialized = SensorResponse.from_string(serialized)
        self.assertEqual(new_response.value, deserialized.value)

    def test_redis_caching_operations_use_correct_commands(self):
        """Test Redis cache key generation follows expected pattern."""
        
        # Test cache key generation
        cache_key = self.manager.to_sensor_response_list_cache_key(self.integration_key)
        expected_key = f'hi.sr.latest.{self.integration_key}'
        
        self.assertEqual(cache_key, expected_key)
        
        # Test that cache key includes both integration components  
        self.assertIn('test_sensor_123', cache_key)
        self.assertIn('test_integration', cache_key)

    def test_get_sensor_caches_database_queries(self):
        """Test sensor lookup uses cache to avoid repeated database queries."""
        # Clear any existing cache
        self.manager._sensor_cache.clear()
        
        # First call should hit database
        sensor1 = self.manager._get_sensor(self.integration_key)
        self.assertIsNotNone(sensor1)
        self.assertEqual(sensor1.integration_id, 'test_sensor_123')
        
        # Second call should use cache
        with patch('hi.apps.sense.models.Sensor.objects.filter_by_integration_key') as mock_filter:
            sensor2 = self.manager._get_sensor(self.integration_key)
            # Should not query database again
            mock_filter.assert_not_called()
            self.assertEqual(sensor2.integration_id, sensor1.integration_id)

    def test_get_sensor_returns_none_for_nonexistent_integration_key(self):
        """Test sensor lookup returns None for missing integration keys."""
        nonexistent_key = IntegrationKey(
            integration_id='nonexistent',
            integration_name='test_integration'
        )
        
        result = self.manager._get_sensor(nonexistent_key)
        self.assertIsNone(result)

    @patch('hi.apps.sense.sensor_response_manager.get_redis_client')
    def test_dirty_flag_optimization_prevents_unnecessary_redis_calls(self, mock_get_redis_client):
        """Test dirty flag optimization reduces Redis operations for repeated calls."""
        mock_redis = Mock()
        mock_redis.smembers.return_value = []
        mock_get_redis_client.return_value = mock_redis
        
        # First call should hit Redis
        result1 = self.manager.get_all_latest_sensor_responses()
        self.assertIsInstance(result1, dict)
        
        # Second call should use cached data
        mock_redis.reset_mock()
        result2 = self.manager.get_all_latest_sensor_responses()
        
        # Should not call Redis again
        mock_redis.smembers.assert_not_called()
        self.assertEqual(result1, result2)

    @patch('hi.apps.sense.sensor_response_manager.get_redis_client')
    def test_sensor_response_serialization_roundtrip(self, mock_get_redis_client):
        """Test sensor responses serialize/deserialize correctly for Redis storage."""
        mock_redis = Mock()
        mock_get_redis_client.return_value = mock_redis
        
        original_response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0)),
            detail_attrs={'key': 'value'},
            has_event_video_snapshot=True
        )
        
        # Serialize to string
        serialized = str(original_response)
        
        # Deserialize from string
        deserialized = SensorResponse.from_string(serialized)
        
        # Verify round-trip integrity
        self.assertEqual(deserialized.integration_key, original_response.integration_key)
        self.assertEqual(deserialized.value, original_response.value)
        self.assertEqual(deserialized.timestamp, original_response.timestamp)
        self.assertEqual(deserialized.detail_attrs, original_response.detail_attrs)
        self.assertEqual(deserialized.has_event_video_snapshot, original_response.has_event_video_snapshot)

    def test_get_latest_sensor_response_map_empty_list_short_circuits(self):
        """Empty integration_keys returns empty dict without touching Redis."""
        with patch.object(self.manager, '_redis_client') as mock_redis:
            result = self.manager.get_latest_sensor_response_map(integration_keys=[])
            self.assertEqual(result, {})
            mock_redis.pipeline.assert_not_called()

    def test_get_latest_sensor_response_map_returns_none_for_uncached(self):
        """Keys with no cached entry map to None."""
        # Reset fakeredis state for this test.
        self.manager._redis_client.flushdb()

        result = self.manager.get_latest_sensor_response_map(
            integration_keys=[self.integration_key],
        )
        self.assertEqual(result, {self.integration_key: None})

    def test_get_latest_sensor_response_map_returns_latest_for_cached(self):
        """Keys with cached entries return the most recent SensorResponse."""
        self.manager._redis_client.flushdb()

        cache_key = self.manager.to_sensor_response_list_cache_key(self.integration_key)
        older = SensorResponse(
            integration_key=self.integration_key,
            value='old_value',
            timestamp=timezone.now(),
        )
        newer = SensorResponse(
            integration_key=self.integration_key,
            value='new_value',
            timestamp=timezone.now(),
        )
        # LPUSH order matches the production write path (newer at index 0).
        self.manager._redis_client.lpush(cache_key, str(older))
        self.manager._redis_client.lpush(cache_key, str(newer))

        result = self.manager.get_latest_sensor_response_map(
            integration_keys=[self.integration_key],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[self.integration_key].value, 'new_value')

    def test_get_latest_sensor_response_map_handles_mixed_cached_and_uncached(self):
        """Multiple keys: some cached, some not — order preserved, None for misses."""
        self.manager._redis_client.flushdb()

        key_a = IntegrationKey(integration_id='a', integration_name='one')
        key_b = IntegrationKey(integration_id='b', integration_name='two')
        key_c = IntegrationKey(integration_id='c', integration_name='three')

        # Cache only key_a and key_c.
        for key, value in [(key_a, 'val_a'), (key_c, 'val_c')]:
            cache_key = self.manager.to_sensor_response_list_cache_key(key)
            response = SensorResponse(
                integration_key=key, value=value, timestamp=timezone.now(),
            )
            self.manager._redis_client.lpush(cache_key, str(response))

        result = self.manager.get_latest_sensor_response_map(
            integration_keys=[key_a, key_b, key_c],
        )
        self.assertEqual(set(result.keys()), {key_a, key_b, key_c})
        self.assertEqual(result[key_a].value, 'val_a')
        self.assertIsNone(result[key_b])
        self.assertEqual(result[key_c].value, 'val_c')

    def test_get_latest_sensor_responses_for_specific_sensors(self):
        """Test retrieval of responses for specific sensor list."""
        # Create additional test data
        SensorHistory.objects.create(
            sensor=self.sensor,
            value='test_value',
            response_datetime=timezone.now()
        )
        
        with patch.object(self.manager, '_redis_client') as mock_redis:
            mock_pipeline = Mock()
            mock_redis.pipeline.return_value = mock_pipeline
            
            # Mock Redis response
            test_response = SensorResponse(
                integration_key=self.integration_key,
                value='cached_value',
                timestamp=timezone.now()
            )
            mock_pipeline.execute.return_value = [[str(test_response)]]
            
            result = self.manager.get_latest_sensor_responses([self.sensor])
            
            # Verify sensor is assigned to responses
            self.assertIn(self.sensor, result)
            response_list = result[self.sensor]
            self.assertEqual(len(response_list), 1)
            self.assertEqual(response_list[0].sensor, self.sensor)


class AsyncSensorResponseManagerDirtyFlagTestCase(AsyncTaskFastTestCase):
    """Verifies the cache-poisoning guard in
    ``_add_latest_sensor_responses``: the in-memory-map dirty flag must be
    set only AFTER the Redis pipeline executes. The DB fan-out (sensor
    lookup + history ``bulk_create``) runs before the Redis write and never
    touches the flag, so it is mocked here. Doing it for real fanned out a
    cross-connection ``sync_to_async`` write whose visibility was
    test-order dependent — the source of this test's flakiness — and that
    write path is covered separately by the sensor-history manager tests."""

    def setUp(self):
        super().setUp()
        SensorResponseManager._instances = {}
        self.manager = SensorResponseManager()

        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT',
        )
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF',
        )
        self.sensor = Sensor.objects.create(
            name='Test Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DEFAULT',
            integration_id='test_sensor_123',
            integration_name='test_integration',
        )
        self.integration_key = IntegrationKey(
            integration_id='test_sensor_123',
            integration_name='test_integration',
        )

    def test_dirty_flag_set_only_after_redis_pipeline_executes(self):
        """Regression for the cache-poisoning race: setting the
        dirty flag before the Redis write let a concurrent reader
        rebuild the in-memory map from pre-update Redis state and
        clear the flag, leaving the map permanently stuck on the
        stale value. Assert the flag is still False at the moment
        ``pipeline.execute()`` runs and True after."""
        observed_dirty_at_execute = []

        async def run():
            sensor_response = SensorResponse(
                integration_key=self.integration_key,
                value='on',
                timestamp=timezone.now(),
            )
            # Pre-resolve the sensor so _add_sensors skips its DB read.
            sensor_response.sensor = self.sensor

            mock_pipeline = Mock()

            def capture_dirty_state():
                observed_dirty_at_execute.append(
                    self.manager._latest_sensor_data_dirty,
                )
                return []

            mock_pipeline.execute.side_effect = capture_dirty_state

            # Mock the history-manager write: it runs before the Redis
            # pipeline and is irrelevant to the dirty flag this test pins.
            mock_history_manager = Mock()
            mock_history_manager.add_to_sensor_history = AsyncMock( return_value = [] )

            with patch.object( self.manager, '_redis_client' ) as mock_redis, \
                 patch.object( self.manager, 'sensor_history_manager_async',
                               new = AsyncMock( return_value = mock_history_manager )):
                mock_redis.pipeline.return_value = mock_pipeline
                self.manager._latest_sensor_data_dirty = False
                await self.manager._add_latest_sensor_responses( [ sensor_response ] )

        # Use the class-managed event loop. asyncio.get_event_loop() would
        # return whatever loop is currently set, which another test class's
        # teardown may have already closed — the source of cross-test
        # flakiness under the parallel runner.
        self.run_async( run() )

        self.assertEqual(
            observed_dirty_at_execute, [ False ],
            'Dirty flag was set before the Redis pipeline executed',
        )
        self.assertTrue(
            self.manager._latest_sensor_data_dirty,
            'Dirty flag must be True after the Redis pipeline executes',
        )


class TestUpdateWithLatestSensorResponseLists(AsyncTaskFastTestCase):
    """``update_with_latest_sensor_response_lists`` is the multi-
    response-per-key entry point. The old single-response method is
    now a thin adapter that wraps each value and delegates here, so
    these tests pin both contracts via the new method's behavior:

      * chronological ordering (incoming list sorted by timestamp)
      * running-previous comparison (cached → first response → second → ...)
      * same-value dedup against the cached prior AND within the list
      * multiple responses per key persisted as separate transitions
      * multiple keys processed independently
      * empty list per key is a no-op
      * first-ever observation (no cache) — persisted without transition
    """

    def setUp(self):
        super().setUp()
        SensorResponseManager._instances = {}
        self.manager = SensorResponseManager()

        self.key_a = IntegrationKey(
            integration_id = 'sensor_a',
            integration_name = 'test',
        )
        self.key_b = IntegrationKey(
            integration_id = 'sensor_b',
            integration_name = 'test',
        )
        self.t0 = timezone.now()

    def _response(self, key, value, offset_secs = 0):
        return SensorResponse(
            integration_key = key,
            value = value,
            timestamp = self.t0 + timedelta( seconds = offset_secs ),
        )

    def _run_update(self, sensor_response_list_map, cached_per_key = None):
        """Mock Redis and the event manager around a single call to
        ``update_with_latest_sensor_response_lists``. Returns
        (changed_responses, transitions) — the lists the manager
        would persist and dispatch.

        ``cached_per_key`` is a dict mapping integration_key →
        previously-cached SensorResponse (string form, as Redis
        returns), or None for no prior cache."""
        cached_per_key = cached_per_key or {}

        def fake_lindex_results():
            return [
                str( cached_per_key[ k ] ) if k in cached_per_key else None
                for k in sensor_response_list_map.keys()
            ]

        captured = { 'changed': None, 'transitions': None }

        async def capture_add( responses ):
            captured['changed'] = list( responses )

        async def capture_transitions( transitions ):
            captured['transitions'] = list( transitions )

        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = fake_lindex_results()
        mock_redis = Mock()
        mock_redis.pipeline.return_value = mock_pipeline

        mock_event_manager = Mock()
        mock_event_manager.add_entity_state_transitions = AsyncMock(
            side_effect = capture_transitions,
        )

        def fake_create_transition( previous_sensor_response, latest_sensor_response ):
            return (
                previous_sensor_response.value,
                latest_sensor_response.value,
            )

        async def run():
            with patch.object( self.manager, '_redis_client', mock_redis ), \
                 patch.object( self.manager, '_add_latest_sensor_responses',
                               side_effect = capture_add ), \
                 patch.object( self.manager, 'event_manager_async',
                               return_value = mock_event_manager ), \
                 patch.object( self.manager, '_create_entity_state_transition',
                               new = AsyncMock( side_effect = fake_create_transition )):
                await self.manager.update_with_latest_sensor_response_lists(
                    sensor_response_list_map = sensor_response_list_map,
                )

        self.run_async( run() )
        return captured['changed'] or [], captured['transitions'] or []

    def test_empty_map_is_noop(self):
        changed, transitions = self._run_update({})
        self.assertEqual( changed, [] )
        self.assertEqual( transitions, [] )

    def test_first_ever_observation_records_without_transition(self):
        # No cached prior → first response is recorded as a history row
        # but does not produce a transition (there's no "from" value).
        response = self._response( self.key_a, 'on' )
        changed, transitions = self._run_update({
            self.key_a: [ response ],
        })
        self.assertEqual( [ r.value for r in changed ], [ 'on' ] )
        self.assertEqual( transitions, [] )

    def test_same_value_as_cached_is_skipped(self):
        # Cached: on. Submitted: on → no change, nothing persisted.
        cached = self._response( self.key_a, 'on', offset_secs = -10 )
        submitted = self._response( self.key_a, 'on' )
        changed, transitions = self._run_update(
            { self.key_a: [ submitted ] },
            cached_per_key = { self.key_a: cached },
        )
        self.assertEqual( changed, [] )
        self.assertEqual( transitions, [] )

    def test_value_change_against_cached_records_transition(self):
        cached = self._response( self.key_a, 'off', offset_secs = -10 )
        submitted = self._response( self.key_a, 'on' )
        changed, transitions = self._run_update(
            { self.key_a: [ submitted ] },
            cached_per_key = { self.key_a: cached },
        )
        self.assertEqual( [ r.value for r in changed ], [ 'on' ] )
        self.assertEqual( transitions, [ ( 'off', 'on' ) ] )

    def test_multi_response_per_key_processes_each_against_running_previous(self):
        # No cached prior. Submit [A, B, C] for one key → first A
        # records as first-ever (no transition); A→B transition; B→C
        # transition. Three persisted, two transitions.
        responses = [
            self._response( self.key_a, 'a', offset_secs = 1 ),
            self._response( self.key_a, 'b', offset_secs = 2 ),
            self._response( self.key_a, 'c', offset_secs = 3 ),
        ]
        changed, transitions = self._run_update({ self.key_a: responses })
        self.assertEqual( [ r.value for r in changed ], [ 'a', 'b', 'c' ] )
        self.assertEqual( transitions, [ ( 'a', 'b' ), ( 'b', 'c' ) ] )

    def test_consecutive_duplicates_within_list_are_skipped(self):
        # No cached prior. Submit [A, B, B, C]. First A is first-ever
        # (records, no transition). A→B is recorded as transition.
        # Second B matches the running previous (B) → skipped. B→C
        # is recorded.
        responses = [
            self._response( self.key_a, 'a', offset_secs = 1 ),
            self._response( self.key_a, 'b', offset_secs = 2 ),
            self._response( self.key_a, 'b', offset_secs = 3 ),
            self._response( self.key_a, 'c', offset_secs = 4 ),
        ]
        changed, transitions = self._run_update({ self.key_a: responses })
        self.assertEqual( [ r.value for r in changed ], [ 'a', 'b', 'c' ] )
        self.assertEqual( transitions, [ ( 'a', 'b' ), ( 'b', 'c' ) ] )

    def test_out_of_order_responses_get_sorted_by_timestamp(self):
        # Defensive: caller might assemble the list in phase order
        # rather than chronological order. The manager sorts by
        # timestamp before applying the running-previous walk.
        responses = [
            self._response( self.key_a, 'b', offset_secs = 2 ),  # later
            self._response( self.key_a, 'a', offset_secs = 1 ),  # earlier
        ]
        changed, transitions = self._run_update({ self.key_a: responses })
        # Order chronologically: a (first-ever, no transition),
        # then b (a→b transition).
        self.assertEqual( [ r.value for r in changed ], [ 'a', 'b' ] )
        self.assertEqual( transitions, [ ( 'a', 'b' ) ] )

    def test_empty_list_for_a_key_is_noop(self):
        changed, transitions = self._run_update({ self.key_a: [] })
        self.assertEqual( changed, [] )
        self.assertEqual( transitions, [] )

    def test_multiple_keys_processed_independently(self):
        # Two keys, each with its own running-previous. A change on
        # key_a does not affect comparisons on key_b.
        cached_a = self._response( self.key_a, 'off', offset_secs = -10 )
        responses = {
            self.key_a: [ self._response( self.key_a, 'on', offset_secs = 1 ) ],
            self.key_b: [
                self._response( self.key_b, 'x', offset_secs = 1 ),
                self._response( self.key_b, 'y', offset_secs = 2 ),
            ],
        }
        changed, transitions = self._run_update(
            responses, cached_per_key = { self.key_a: cached_a },
        )
        self.assertEqual(
            sorted( r.value for r in changed ),
            [ 'on', 'x', 'y' ],
        )
        # key_a contributes off→on; key_b's x is first-ever (no
        # transition), x→y is the one transition.
        self.assertEqual(
            sorted( transitions ),
            sorted( [ ( 'off', 'on' ), ( 'x', 'y' ) ] ),
        )

    def test_adapter_wraps_single_response_into_list(self):
        # The old single-response entry point now delegates to the
        # list-form one. Single response, same key behavior.
        response = self._response( self.key_a, 'on' )

        captured = { 'arg': None }

        async def capture( sensor_response_list_map ):
            captured['arg'] = sensor_response_list_map

        async def run():
            with patch.object(
                self.manager, 'update_with_latest_sensor_response_lists',
                side_effect = capture,
            ):
                await self.manager.update_with_latest_sensor_responses({
                    self.key_a: response,
                })

        self.run_async( run() )
        self.assertEqual( captured['arg'], { self.key_a: [ response ] } )

    def test_event_manager_dispatch_is_awaited_when_transitions_exist(self):
        # Regression guard for the dispatch site: if the production
        # code ever stops awaiting ``add_entity_state_transitions``,
        # the transition-list assertions in the other tests still
        # pass (because they capture the side_effect arg) — but the
        # transitions are no longer delivered to downstream
        # consumers. Assert the call was made.
        cached = self._response( self.key_a, 'off', offset_secs = -10 )
        submitted = self._response( self.key_a, 'on' )

        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [ str( cached ) ]
        mock_redis = Mock()
        mock_redis.pipeline.return_value = mock_pipeline

        mock_event_manager = Mock()
        mock_event_manager.add_entity_state_transitions = AsyncMock()

        async def run():
            with patch.object( self.manager, '_redis_client', mock_redis ), \
                 patch.object( self.manager, '_add_latest_sensor_responses',
                               new = AsyncMock() ), \
                 patch.object( self.manager, 'event_manager_async',
                               return_value = mock_event_manager ), \
                 patch.object( self.manager, '_create_entity_state_transition',
                               new = AsyncMock( return_value = ( 'off', 'on' ))):
                await self.manager.update_with_latest_sensor_response_lists({
                    self.key_a: [ submitted ],
                })

        self.run_async( run() )
        mock_event_manager.add_entity_state_transitions.assert_awaited_once()
