import logging
from unittest.mock import Mock

from hi.apps.monitor.transient_models import EntityStateStatusData, EntityStatusData
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.control.transient_models import ControllerData
from hi.apps.common.svg_models import SvgIconItem
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityStateStatusData(BaseTestCase):

    def test_latest_sensor_response_returns_most_recent_from_ordered_list(self):
        """Test latest_sensor_response returns first item from time-ordered list."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        # Create responses ordered by time (newest first as expected)
        newest_response = Mock(spec=SensorResponse)
        newest_response.response_datetime = '2023-01-01T12:00:00Z'
        newest_response.value = 'ON'
        
        older_response = Mock(spec=SensorResponse)
        older_response.response_datetime = '2023-01-01T11:00:00Z'
        older_response.value = 'OFF'
        
        sensor_response_list = [newest_response, older_response]
        
        status_data = EntityStateStatusData(
            entity_state=entity_state,
            sensor_response_list=sensor_response_list,
            controller_data_list=[]
        )
        
        # Should return the first (most recent) response
        latest = status_data.latest_sensor_response
        self.assertEqual(latest.value, 'ON')
        self.assertEqual(latest.response_datetime, '2023-01-01T12:00:00Z')

    def test_latest_sensor_response_handles_empty_list_gracefully(self):
        """Test latest_sensor_response returns None for empty sensor list."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        status_data = EntityStateStatusData(
            entity_state=entity_state,
            sensor_response_list=[],
            controller_data_list=[]
        )
        
        self.assertIsNone(status_data.latest_sensor_response)

    def test_entity_state_status_data_provides_access_to_related_controllers(self):
        """Test controller data access for entity state control operations."""
        entity = Entity.objects.create(
            name='Controllable Entity',
            entity_type_str='LIGHT'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        # Mock controller data
        controller_data1 = Mock(spec=ControllerData)
        controller_data1.controller = Mock()
        controller_data1.controller.name = 'Power Switch'
        controller_data2 = Mock(spec=ControllerData)
        controller_data2.controller = Mock()
        controller_data2.controller.name = 'Dimmer'
        
        status_data = EntityStateStatusData(
            entity_state=entity_state,
            sensor_response_list=[],
            controller_data_list=[controller_data1, controller_data2]
        )
        
        # Should provide access to all available controllers
        self.assertEqual(len(status_data.controller_data_list), 2)
        self.assertIn(controller_data1, status_data.controller_data_list)
        self.assertIn(controller_data2, status_data.controller_data_list)

    def test_entity_state_status_data_handles_mixed_sensor_and_controller_data(self):
        """Test status data with both sensor responses and controller data."""
        entity = Entity.objects.create(
            name='Smart Switch',
            entity_type_str='SWITCH'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        sensor_response = Mock(spec=SensorResponse)
        sensor_response.value = 'ON'
        
        controller_data = Mock(spec=ControllerData)
        controller_data.controller = Mock()
        controller_data.controller.name = 'Toggle'
        
        status_data = EntityStateStatusData(
            entity_state=entity_state,
            sensor_response_list=[sensor_response],
            controller_data_list=[controller_data]
        )
        
        # Should maintain both sensor and controller data
        self.assertEqual(status_data.latest_sensor_response.value, 'ON')
        self.assertEqual(len(status_data.controller_data_list), 1)
        self.assertEqual(status_data.controller_data_list[0].controller.name, 'Toggle')


class TestEntityStatusData(BaseTestCase):

    def test_template_context_includes_all_required_display_data(self):
        """Test template context provides complete data for UI rendering."""
        entity = Entity.objects.create(
            name='Display Entity',
            entity_type_str='CAMERA'
        )
        
        # Create mock entity state status data
        state_status_data1 = Mock(spec=EntityStateStatusData)
        state_status_data1.entity_state = Mock()
        state_status_data1.entity_state.entity_state_type_str = 'ON_OFF'
        
        state_status_data2 = Mock(spec=EntityStateStatusData)
        state_status_data2.entity_state = Mock()
        state_status_data2.entity_state.entity_state_type_str = 'MOTION'
        
        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=[state_status_data1, state_status_data2]
        )
        
        context = status_data.to_template_context()
        
        # Should include all data needed for template rendering
        self.assertIn('entity', context)
        self.assertIn('entity_state_status_data_list', context)
        self.assertEqual(context['entity'], entity)
        self.assertEqual(len(context['entity_state_status_data_list']), 2)

    def test_entity_status_data_supports_optional_display_icon(self):
        """Test entity status data with optional SVG icon for display."""
        entity = Entity.objects.create(
            name='Icon Entity',
            entity_type_str='CAMERA'
        )
        
        svg_icon = Mock(spec=SvgIconItem)
        svg_icon.icon_name = 'camera-icon'
        
        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=[],
            display_only_svg_icon_item=svg_icon
        )
        
        # Should store and provide access to display icon
        self.assertEqual(status_data.display_only_svg_icon_item.icon_name, 'camera-icon')

    def test_entity_status_data_handles_entity_without_states(self):
        """Test entity status data for entities with no configured states."""
        entity = Entity.objects.create(
            name='Simple Entity',
            entity_type_str='DISPLAY_ONLY'
        )
        
        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=[]
        )
        
        # Should handle entities with no states gracefully
        self.assertEqual(status_data.entity, entity)
        self.assertEqual(len(status_data.entity_state_status_data_list), 0)
        self.assertIsNone(status_data.display_only_svg_icon_item)
        
        # Template context should still be valid
        context = status_data.to_template_context()
        self.assertEqual(context['entity'], entity)
        self.assertEqual(len(context['entity_state_status_data_list']), 0)

    def test_entity_status_data_aggregates_multiple_state_types(self):
        """Test entity status data aggregation across different state types."""
        entity = Entity.objects.create(
            name='Multi-Function Device',
            entity_type_str='CAMERA'
        )
        
        # Mock different types of entity state status data
        power_status = Mock(spec=EntityStateStatusData)
        power_status.entity_state = Mock()
        power_status.entity_state.entity_state_type_str = 'ON_OFF'
        power_status.latest_sensor_response = Mock()
        power_status.latest_sensor_response.value = 'ON'
        
        motion_status = Mock(spec=EntityStateStatusData)
        motion_status.entity_state = Mock()
        motion_status.entity_state.entity_state_type_str = 'MOTION'
        motion_status.latest_sensor_response = Mock()
        motion_status.latest_sensor_response.value = 'DETECTED'
        
        recording_status = Mock(spec=EntityStateStatusData)
        recording_status.entity_state = Mock()
        recording_status.entity_state.entity_state_type_str = 'RECORDING'
        recording_status.latest_sensor_response = Mock()
        recording_status.latest_sensor_response.value = 'ACTIVE'
        
        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=[power_status, motion_status, recording_status]
        )
        
        # Should aggregate all state types for comprehensive entity status
        self.assertEqual(len(status_data.entity_state_status_data_list), 3)
        
        state_types = [
            state.entity_state.entity_state_type_str 
            for state in status_data.entity_state_status_data_list
        ]
        self.assertIn('ON_OFF', state_types)
        self.assertIn('MOTION', state_types)
        self.assertIn('RECORDING', state_types)
