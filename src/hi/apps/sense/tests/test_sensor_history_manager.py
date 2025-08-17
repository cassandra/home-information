import asyncio
from datetime import datetime
from unittest.mock import patch

from asgiref.sync import sync_to_async
from django.utils import timezone
from hi.tests.async_task_utils import AsyncTaskTestCase

from hi.apps.entity.models import Entity, EntityState, EntityStateDelegation
from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.sensor_history_manager import SensorHistoryManager
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey


class AsyncSensorHistoryManagerTestCase(AsyncTaskTestCase):
    """Test SensorHistoryManager with proper async infrastructure."""
    
    def setUp(self):
        super().setUp()
        # Reset singleton state for each test
        SensorHistoryManager._instances = {}
        self.manager = SensorHistoryManager()
        
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
            integration_name='test_integration',
            persist_history=True
        )
        self.integration_key = IntegrationKey(
            integration_id='test_sensor_123',
            integration_name='test_integration'
        )

    def test_manager_singleton_behavior(self):
        """Test singleton pattern behavior - critical for state consistency."""
        manager1 = SensorHistoryManager()
        manager2 = SensorHistoryManager()
        self.assertIs(manager1, manager2)
        
        # Ensure shared state
        manager1._was_initialized = True
        self.assertTrue(manager2._was_initialized)

    def test_initialization_sets_state_properly(self):
        """Test manager initialization sets internal state correctly."""
        # Reset to test initialization
        SensorHistoryManager._instances = {}
        manager = SensorHistoryManager()
        
        # Reset initialization to test fresh state
        manager._was_initialized = False
        
        self.assertFalse(manager._was_initialized)
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        
        # Second call should not change initialized state (it stays True)
        original_state = manager._was_initialized
        manager.ensure_initialized()
        self.assertEqual(manager._was_initialized, original_state)

    def test_add_sensor_history_only_persists_enabled_sensors(self):
        """Test history persistence respects sensor persist_history flag."""
        # Create sensor with history disabled
        sensor_no_persist = Sensor.objects.create(
            name='No Persist Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DEFAULT',
            integration_id='no_persist_123',
            integration_name='test_integration',
            persist_history=False
        )
        
        responses = [
            SensorResponse(
                integration_key=self.integration_key,
                value='on',
                timestamp=timezone.now(),
                sensor=self.sensor  # persist_history=True
            ),
            SensorResponse(
                integration_key=IntegrationKey('no_persist_123', 'test_integration'),
                value='off',
                timestamp=timezone.now(),
                sensor=sensor_no_persist  # persist_history=False
            )
        ]
        
        async def async_test_logic():
            with patch.object(self.manager, '_bulk_create_sensor_history_async') as mock_bulk:
                await self.manager.add_to_sensor_history(responses)
                
                # Should only create history for sensor with persist_history=True
                mock_bulk.assert_called_once()
                # Get the first positional argument (sensor_history_list)
                history_list = mock_bulk.call_args[0][0]
                self.assertEqual(len(history_list), 1)
                self.assertEqual(history_list[0].sensor, self.sensor)
        
        self.run_async(async_test_logic())

    def test_add_sensor_history_handles_empty_list(self):
        """Test add_to_sensor_history handles empty input gracefully."""
        async def async_test_logic():
            with patch.object(self.manager, '_bulk_create_sensor_history_async') as mock_bulk:
                await self.manager.add_to_sensor_history([])
                mock_bulk.assert_not_called()
        
        self.run_async(async_test_logic())

    def test_bulk_create_uses_correct_async_pattern(self):
        """Test bulk create uses proper sync_to_async pattern for database operations."""
        history_items = [
            SensorHistory(
                sensor=self.sensor,
                value='test_value',
                response_datetime=timezone.now()
            )
        ]
        
        async def async_test_logic():
            with patch('hi.apps.sense.models.SensorHistory.objects.bulk_create') as mock_bulk:
                await self.manager._bulk_create_sensor_history_async(history_items)
                mock_bulk.assert_called_once_with(history_items)
        
        self.run_async(async_test_logic())

    def test_sensor_response_to_history_conversion(self):
        """Test sensor responses convert to history objects correctly."""
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value_that_is_very_long' * 20,  # Test truncation
            timestamp=timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0)),
            sensor=self.sensor,
            detail_attrs={'key': 'value'},
            image_url='http://example.com/image.jpg'
        )
        
        history = response.to_sensor_history()
        
        self.assertEqual(history.sensor, self.sensor)
        self.assertEqual(len(history.value), 255)  # Should be truncated
        self.assertEqual(history.response_datetime, response.timestamp)
        self.assertEqual(history.image_url, response.image_url)
        self.assertIn('key', history.detail_attrs)

    def test_get_latest_entity_sensor_history_direct_states(self):
        """Test retrieval of sensor history for entity's direct states."""
        # Create history records
        SensorHistory.objects.create(
            sensor=self.sensor,
            value='value1',
            response_datetime=timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        )
        SensorHistory.objects.create(
            sensor=self.sensor,
            value='value2', 
            response_datetime=timezone.make_aware(datetime(2023, 1, 1, 13, 0, 0))
        )
        
        result = self.manager.get_latest_entity_sensor_history(self.entity, max_items=5)
        
        self.assertIn(self.sensor, result)
        history_list = result[self.sensor]
        self.assertEqual(len(history_list), 2)
        # Should be ordered by most recent first
        self.assertEqual(history_list[0].value, 'value2')
        self.assertEqual(history_list[1].value, 'value1')

    def test_get_latest_entity_sensor_history_with_delegations(self):
        """Test retrieval includes sensors from delegated entity states."""
        # Create delegated entity and state
        delegated_entity = Entity.objects.create(
            name='Delegated Entity',
            entity_type_str='SENSOR'
        )
        delegated_state = EntityState.objects.create(
            entity=delegated_entity,
            entity_state_type_str='NUMERIC'
        )
        delegated_sensor = Sensor.objects.create(
            name='Delegated Sensor',
            entity_state=delegated_state,
            sensor_type_str='DEFAULT',
            integration_id='delegated_123',
            integration_name='test_integration'
        )
        
        # Create delegation relationship
        EntityStateDelegation.objects.create(
            entity_state=delegated_state,
            delegate_entity=self.entity
        )
        
        # Create history for delegated sensor
        SensorHistory.objects.create(
            sensor=delegated_sensor,
            value='delegated_value',
            response_datetime=timezone.now()
        )
        
        result = self.manager.get_latest_entity_sensor_history(self.entity, max_items=5)
        
        # Should include both direct and delegated sensors
        sensor_keys = list(result.keys())
        self.assertIn(self.sensor, sensor_keys)
        self.assertIn(delegated_sensor, sensor_keys)

    def test_get_latest_entity_sensor_history_respects_max_items(self):
        """Test max_items parameter limits history records per sensor."""
        # Create multiple history records
        for i in range(10):
            SensorHistory.objects.create(
                sensor=self.sensor,
                value=f'value_{i}',
                response_datetime=timezone.make_aware(datetime(2023, 1, 1, 12, i, 0))
            )
        
        result = self.manager.get_latest_entity_sensor_history(self.entity, max_items=3)
        
        self.assertIn(self.sensor, result)
        history_list = result[self.sensor]
        self.assertEqual(len(history_list), 3)
        # Should return most recent records
        self.assertEqual(history_list[0].value, 'value_9')

    def test_get_latest_entity_sensor_history_handles_no_sensors(self):
        """Test handles entities with no sensors gracefully."""
        entity_no_sensors = Entity.objects.create(
            name='No Sensors Entity',
            entity_type_str='LIGHT'
        )
        
        result = self.manager.get_latest_entity_sensor_history(entity_no_sensors)
        
        self.assertEqual(result, {})

    def test_get_latest_entity_sensor_history_query_optimization(self):
        """Test query uses select_related for performance optimization."""
        # Create delegation to test select_related usage
        delegated_entity = Entity.objects.create(
            name='Delegated Entity',
            entity_type_str='SENSOR'
        )
        delegated_state = EntityState.objects.create(
            entity=delegated_entity,
            entity_state_type_str='NUMERIC'
        )
        EntityStateDelegation.objects.create(
            entity_state=delegated_state,
            delegate_entity=self.entity
        )
        
        with patch('hi.apps.entity.models.Entity.entity_state_delegations') as mock_delegations:
            mock_delegations.select_related.return_value.all.return_value = []
            
            self.manager.get_latest_entity_sensor_history(self.entity)
            
            # Verify select_related is used for optimization
            mock_delegations.select_related.assert_called_once_with('entity_state')

    def test_concurrent_history_addition_thread_safety(self):
        """Test manager handles concurrent access safely."""
        import threading
        
        from django.utils import timezone
        responses = [
            SensorResponse(
                integration_key=self.integration_key,
                value=f'concurrent_value_{i}',
                timestamp=timezone.now(),
                sensor=self.sensor
            ) for i in range(5)
        ]
        
        results = []
        
        def worker(response_list):
            async def async_worker():
                await self.manager.add_to_sensor_history(response_list)
                # Check that records were created
                count = await sync_to_async(SensorHistory.objects.filter(
                    sensor=self.sensor
                ).count)()
                results.append(count)
            
            # Run in separate event loop for each thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(async_worker())
            finally:
                loop.close()
        
        threads = [threading.Thread(target=worker, args=([resp],)) for resp in responses]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        self.assertEqual(len(results), 5)
        # Total records should equal number of operations
        final_count = SensorHistory.objects.filter(sensor=self.sensor).count()
        self.assertEqual(final_count, 5)
