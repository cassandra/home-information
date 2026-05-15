import logging
from unittest.mock import Mock

from hi.apps.monitor.display_data import EntityDisplayData
from hi.apps.monitor.status_data import EntityStateStatusData, EntityStatusData
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
        """``EntityDisplayData.to_template_context`` provides the keys
        templates rely on for rendering, with the per-state list
        wrapped in display-ready ``EntityStateDisplayData`` items."""
        entity = Entity.objects.create(
            name='Display Entity',
            entity_type_str='CAMERA',
        )
        state_1 = EntityState.objects.create(
            entity=entity, name='State 1',
            entity_state_type_str='ON_OFF',
        )
        state_2 = EntityState.objects.create(
            entity=entity, name='State 2',
            entity_state_type_str='MOVEMENT',
        )
        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=[
                EntityStateStatusData(
                    entity_state=state_1,
                    sensor_response_list=[], controller_data_list=[],
                ),
                EntityStateStatusData(
                    entity_state=state_2,
                    sensor_response_list=[], controller_data_list=[],
                ),
            ],
        )
        display_data = EntityDisplayData(entity_status_data=status_data)
        context = display_data.to_template_context()
        self.assertIn('entity', context)
        self.assertIn('state_status_data_list', context)
        self.assertEqual(context['entity'], entity)
        self.assertEqual(len(context['state_status_data_list']), 2)

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
        
        # Template context should still be valid (via display wrapper)
        context = EntityDisplayData(entity_status_data=status_data).to_template_context()
        self.assertEqual(context['entity'], entity)
        self.assertEqual(len(context['state_status_data_list']), 0)

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


class TestStateStatusDataByRole(BaseTestCase):
    """``EntityDisplayData.state_status_data_by_role`` indexes the
    state-status entries by the lowercase EntityStateRole name so
    panel templates can pull a specific state by semantic role."""

    def test_keys_are_lowercase_role_names(self):
        from hi.apps.entity.enums import EntityStateRole, EntityType
        from hi.apps.entity.models import EntityState

        entity = Entity.objects.create(
            name='Smoke Test',
            entity_type_str=str(EntityType.SMOKE_DETECTOR),
        )
        smoke_state = EntityState.objects.create(
            entity=entity, name='Smoke',
            entity_state_type_str='SMOKE',
            role_str=str(EntityStateRole.SMOKE),
        )
        battery_state = EntityState.objects.create(
            entity=entity, name='Battery',
            entity_state_type_str='BATTERY_LEVEL',
            role_str=str(EntityStateRole.BATTERY_LEVEL),
        )

        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=[
                EntityStateStatusData(
                    entity_state=smoke_state,
                    sensor_response_list=[], controller_data_list=[],
                ),
                EntityStateStatusData(
                    entity_state=battery_state,
                    sensor_response_list=[], controller_data_list=[],
                ),
            ],
        )
        display_data = EntityDisplayData(entity_status_data=status_data)

        by_role = display_data.state_status_data_by_role
        self.assertIn('smoke', by_role)
        self.assertIn('battery_level', by_role)
        self.assertEqual(by_role['smoke'].entity_state, smoke_state)
        self.assertEqual(by_role['battery_level'].entity_state, battery_state)

    def test_empty_when_no_states(self):
        entity = Entity.objects.create(
            name='Empty', entity_type_str='OTHER',
        )
        status_data = EntityStatusData(
            entity=entity, entity_state_status_data_list=[],
        )
        display_data = EntityDisplayData(entity_status_data=status_data)
        self.assertEqual(display_data.state_status_data_by_role, {})

    def test_template_context_includes_by_role_map(self):
        entity = Entity.objects.create(
            name='Ctx Test', entity_type_str='OTHER',
        )
        status_data = EntityStatusData(
            entity=entity, entity_state_status_data_list=[],
        )
        display_data = EntityDisplayData(entity_status_data=status_data)
        context = display_data.to_template_context()
        self.assertIn('state_status_data_by_role', context)
