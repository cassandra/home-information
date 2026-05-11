import logging
from datetime import datetime
from unittest.mock import Mock, patch

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.monitor.transient_models import EntityStateStatusData
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestStatusDisplayManager(BaseTestCase):

    def test_status_display_manager_singleton_behavior(self):
        """Test StatusDisplayManager maintains single instance across calls."""
        manager1 = StatusDisplayManager()
        manager2 = StatusDisplayManager()
        
        self.assertIs(manager1, manager2)

    def test_entity_state_value_override_storage_and_retrieval(self):
        """Test value override storage and TTL cache behavior."""
        entity = Entity.objects.create(name='Test Entity', entity_type_str='CAMERA')
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        # Create a new manager instance to ensure clean state
        manager = StatusDisplayManager()
        manager._status_value_overrides.clear()  # Clear any existing state
        
        # Verify no override initially
        self.assertNotIn(entity_state.id, manager._status_value_overrides)
        
        # Add override value
        manager.add_entity_state_value_override(entity_state, 'ON')
        
        # Verify override is stored
        self.assertIn(entity_state.id, manager._status_value_overrides)
        self.assertEqual(manager._status_value_overrides[entity_state.id], 'ON')
        
        # Test updating override
        manager.add_entity_state_value_override(entity_state, 'OFF')
        self.assertEqual(manager._status_value_overrides[entity_state.id], 'OFF')

    def test_get_entity_status_data_handles_entity_with_no_states(self):
        """Test entity status data generation for entity without states."""
        entity = Entity.objects.create(name='Empty Entity', entity_type_str='CAMERA')
        
        manager = StatusDisplayManager()
        
        with patch.object(manager, '_get_latest_sensor_responses_helper') as mock_helper:
            mock_helper.return_value = {}
            
            entity_status_data = manager.get_entity_status_data(entity)
            
            self.assertEqual(entity_status_data.entity, entity)
            self.assertEqual(len(entity_status_data.entity_state_status_data_list), 0)

    def test_get_entity_status_data_aggregates_multiple_states(self):
        """Test entity status data properly aggregates multiple entity states."""
        entity = Entity.objects.create(name='Multi-State Entity', entity_type_str='CAMERA')
        state1 = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        state2 = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='MOTION'
        )
        
        manager = StatusDisplayManager()
        
        with patch.object(manager, '_get_entity_state_to_entity_state_status_data') as mock_method:
            status_data1 = Mock(spec=EntityStateStatusData)
            status_data2 = Mock(spec=EntityStateStatusData)
            mock_method.return_value = {
                state1: status_data1,
                state2: status_data2
            }
            
            entity_status_data = manager.get_entity_status_data(entity)
            
            self.assertEqual(entity_status_data.entity, entity)
            self.assertIn(status_data1, entity_status_data.entity_state_status_data_list)
            self.assertIn(status_data2, entity_status_data.entity_state_status_data_list)
            self.assertEqual(len(entity_status_data.entity_state_status_data_list), 2)

    def test_get_latest_sensor_response_returns_most_recent(self):
        """Test latest sensor response selection from multiple responses."""
        entity = Entity.objects.create(name='Test Entity', entity_type_str='CAMERA')
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        sensor = Sensor.objects.create(
            name='Test Sensor',
            entity_state=entity_state,
            sensor_type_str='BINARY'
        )
        
        manager = StatusDisplayManager()
        
        # Create mock responses with different timestamps
        older_response = Mock(spec=SensorResponse)
        older_response.timestamp = '2023-01-01T10:00:00Z'
        older_response.value = 'OFF'
        
        newer_response = Mock(spec=SensorResponse)
        newer_response.timestamp = '2023-01-01T11:00:00Z'
        newer_response.value = 'ON'
        
        with patch.object(manager, '_get_latest_sensor_responses_helper') as mock_helper:
            # Mock returns list in timestamp-sorted order (newest first)
            mock_helper.return_value = {sensor: [newer_response, older_response]}
            
            latest_response = manager.get_latest_sensor_response(entity_state)
            
            # Should return newer response (first in sorted list)
            self.assertEqual(latest_response.value, 'ON')

    def test_get_latest_sensor_response_handles_no_responses(self):
        """Test latest sensor response when no responses exist."""
        entity = Entity.objects.create(name='Test Entity', entity_type_str='CAMERA')
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        manager = StatusDisplayManager()
        
        with patch.object(manager, '_get_latest_sensor_responses_helper') as mock_helper:
            mock_helper.return_value = {}
            
            latest_response = manager.get_latest_sensor_response(entity_state)
            
            self.assertIsNone(latest_response)

    def test_override_does_not_mutate_cached_sensor_response(self):
        """Regression for the cache-poisoning bug: applying a value
        override must not modify the SensorResponse owned by
        SensorResponseManager's cache, otherwise the override
        persists past its TTL."""
        from hi.integrations.transient_models import IntegrationKey
        from datetime import datetime

        entity = Entity.objects.create( name='Test Entity', entity_type_str='CAMERA' )
        entity_state = EntityState.objects.create(
            entity=entity, entity_state_type_str='OPEN_CLOSE_POSITION',
        )
        sensor = Sensor.objects.create(
            name='Test Sensor', entity_state=entity_state, sensor_type_str='DEFAULT',
        )
        cached_response = SensorResponse(
            integration_key=IntegrationKey(
                integration_id='hass', integration_name='cover.test',
            ),
            value='30',
            timestamp=datetime( 2026, 1, 1 ),
            sensor=sensor,
        )

        manager = StatusDisplayManager()
        manager._status_value_overrides.clear()
        manager.add_entity_state_value_override( entity_state, '99' )

        with patch.object(
                manager.sensor_response_manager(),
                'get_all_latest_sensor_responses',
        ) as mock_helper:
            mock_helper.return_value = { sensor: [ cached_response ] }
            manager._get_latest_sensor_responses_helper()

        self.assertEqual(
            cached_response.value, '30',
            'Override application must not mutate the cached SensorResponse',
        )

    def test_override_returns_overridden_value_via_copy(self):
        """The override must surface in the returned response list
        even though the cached object is left intact."""
        from hi.integrations.transient_models import IntegrationKey
        from datetime import datetime

        entity = Entity.objects.create( name='Test Entity', entity_type_str='CAMERA' )
        entity_state = EntityState.objects.create(
            entity=entity, entity_state_type_str='OPEN_CLOSE_POSITION',
        )
        sensor = Sensor.objects.create(
            name='Test Sensor', entity_state=entity_state, sensor_type_str='DEFAULT',
        )
        cached_response = SensorResponse(
            integration_key=IntegrationKey(
                integration_id='hass', integration_name='cover.test',
            ),
            value='30',
            timestamp=datetime( 2026, 1, 1 ),
            sensor=sensor,
        )

        manager = StatusDisplayManager()
        manager._status_value_overrides.clear()
        manager.add_entity_state_value_override( entity_state, '99' )

        with patch.object(
                manager.sensor_response_manager(),
                'get_all_latest_sensor_responses',
        ) as mock_helper:
            mock_helper.return_value = { sensor: [ cached_response ] }
            result = manager._get_latest_sensor_responses_helper()

        self.assertEqual( result[ sensor ][ 0 ].value, '99' )

    def test_get_entity_status_data_list_preserves_order(self):
        """Test entity status data list maintains input entity order."""
        entity1 = Entity.objects.create(name='Entity 1', entity_type_str='CAMERA')
        entity2 = Entity.objects.create(name='Entity 2', entity_type_str='LIGHT')
        entity3 = Entity.objects.create(name='Entity 3', entity_type_str='SENSOR')

        entities = [entity1, entity2, entity3]

        manager = StatusDisplayManager()

        with patch.object(manager, '_get_entity_to_entity_status_data') as mock_method:
            mock_method.return_value = {}  # Empty results

            result_list = manager.get_entity_status_data_list(entities)

            # Should maintain same order as input
            self.assertEqual(len(result_list), 3)
            self.assertEqual(result_list[0].entity, entity1)
            self.assertEqual(result_list[1].entity, entity2)
            self.assertEqual(result_list[2].entity, entity3)

    def test_get_entity_state_status_map_includes_states_without_svg_style(self):
        # The unified map emits a row for every EntityState with a
        # response, even those whose value produces no
        # ``svg_status_style`` (e.g., ON_OFF with an unrecognized
        # value). The pre-refactor ``cssClassUpdateMap`` skipped
        # these; the unified shape carries display_value and
        # (when applicable) controller updates which remain useful
        # independent of icon styling, so they're always
        # emitted with an empty ``attributes`` dict.
        entity = Entity.objects.create(
            name='Unrecognized State', entity_type_str='SENSOR',
        )
        entity_state = EntityState.objects.create(
            entity=entity, entity_state_type_str='ON_OFF',
        )
        response = Mock(spec=SensorResponse)
        response.value = 'INVALID'    # not 'on' / 'off' → no svg_status_style
        response.timestamp = datetime.now()
        status_data = EntityStateStatusData(
            entity_state=entity_state,
            sensor_response_list=[response],
            controller_data_list=[],
        )

        manager = StatusDisplayManager()
        with patch.object(
                manager, 'get_all_entity_state_status_data_list',
                return_value=[status_data]):
            result = manager.get_entity_state_status_map()

        self.assertIn(entity_state.css_class, result)
        self.assertEqual(result[entity_state.css_class]['attributes'], {})
