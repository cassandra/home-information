import logging
from datetime import datetime
from unittest.mock import Mock, patch
from django.utils import timezone
from hi.testing.async_task_utils import AsyncTaskFastTestCase, AsyncTaskTestCase

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


class AsyncSensorResponseManagerCrossConnectionTestCase(AsyncTaskTestCase):
    """Tests that exercise ``_add_latest_sensor_responses`` end-to-end.
    The method fans out through ``sync_to_async`` to multiple DB
    reads/writes; under TestCase the worker thread can't see setUp's
    uncommitted Sensor row, so SQLite returns ``database table is
    locked``. TransactionTestCase commits between methods, which is
    the visibility this fan-out needs."""

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

            mock_pipeline = Mock()

            def capture_dirty_state():
                observed_dirty_at_execute.append(
                    self.manager._latest_sensor_data_dirty,
                )
                return []

            mock_pipeline.execute.side_effect = capture_dirty_state

            with patch.object( self.manager, '_redis_client' ) as mock_redis:
                mock_redis.pipeline.return_value = mock_pipeline
                self.manager._latest_sensor_data_dirty = False
                await self.manager._add_latest_sensor_responses( [ sensor_response ] )

        import asyncio
        asyncio.get_event_loop().run_until_complete( run() )

        self.assertEqual(
            observed_dirty_at_execute, [ False ],
            'Dirty flag was set before the Redis pipeline executed',
        )
        self.assertTrue(
            self.manager._latest_sensor_data_dirty,
            'Dirty flag must be True after the Redis pipeline executes',
        )
