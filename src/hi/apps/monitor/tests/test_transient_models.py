import logging
from unittest.mock import Mock

from hi.apps.monitor.transient_models import EntityStateStatusData, EntityStatusData
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.control.transient_models import ControllerData
from hi.apps.common.svg_models import SvgIconItem
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityStateStatusData(BaseTestCase):

    def test_entity_state_status_data_latest_sensor_response_with_data(self):
        """Test latest_sensor_response with data - critical for status display."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        # Mock sensor responses in time order (newest first)
        response1 = Mock(spec=SensorResponse)
        response1.response_datetime = '2023-01-01T12:00:00Z'
        response2 = Mock(spec=SensorResponse)
        response2.response_datetime = '2023-01-01T11:00:00Z'
        
        sensor_response_list = [response1, response2]  # Ordered by response time
        controller_data_list = []
        
        status_data = EntityStateStatusData(
            entity_state=entity_state,
            sensor_response_list=sensor_response_list,
            controller_data_list=controller_data_list
        )
        
        # Should return first (latest) sensor response
        self.assertEqual(status_data.latest_sensor_response, response1)
        return

    def test_entity_state_status_data_latest_sensor_response_empty_list(self):
        """Test latest_sensor_response with empty list - error handling."""
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
            sensor_response_list=[],  # Empty list
            controller_data_list=[]
        )
        
        # Should return None when no sensor responses
        self.assertIsNone(status_data.latest_sensor_response)
        return

    def test_entity_state_status_data_initialization(self):
        """Test EntityStateStatusData initialization - critical for data structure."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        sensor_response = Mock(spec=SensorResponse)
        controller_data = Mock(spec=ControllerData)
        
        status_data = EntityStateStatusData(
            entity_state=entity_state,
            sensor_response_list=[sensor_response],
            controller_data_list=[controller_data]
        )
        
        # Should properly initialize all fields
        self.assertEqual(status_data.entity_state, entity_state)
        self.assertEqual(status_data.sensor_response_list, [sensor_response])
        self.assertEqual(status_data.controller_data_list, [controller_data])
        return


class TestEntityStatusData(BaseTestCase):

    def test_entity_status_data_initialization_with_optional_fields(self):
        """Test EntityStatusData initialization with optional fields - important for flexibility."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        entity_state_status_data = Mock(spec=EntityStateStatusData)
        svg_icon_item = Mock(spec=SvgIconItem)
        
        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=[entity_state_status_data],
            display_only_svg_icon_item=svg_icon_item
        )
        
        # Should properly initialize all fields including optional ones
        self.assertEqual(status_data.entity, entity)
        self.assertEqual(status_data.entity_state_status_data_list, [entity_state_status_data])
        self.assertEqual(status_data.display_only_svg_icon_item, svg_icon_item)
        return

    def test_entity_status_data_initialization_without_optional_fields(self):
        """Test EntityStatusData initialization without optional fields - default behavior."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        entity_state_status_data = Mock(spec=EntityStateStatusData)
        
        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=[entity_state_status_data]
        )
        
        # Should properly initialize required fields and default optional ones
        self.assertEqual(status_data.entity, entity)
        self.assertEqual(status_data.entity_state_status_data_list, [entity_state_status_data])
        self.assertIsNone(status_data.display_only_svg_icon_item)
        return

    def test_entity_status_data_template_context_generation(self):
        """Test template context generation - critical for UI rendering."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        entity_state_status_data_list = [
            Mock(spec=EntityStateStatusData),
            Mock(spec=EntityStateStatusData)
        ]
        
        status_data = EntityStatusData(
            entity=entity,
            entity_state_status_data_list=entity_state_status_data_list
        )
        
        context = status_data.to_template_context()
        
        # Should contain required template variables
        expected_keys = {'entity', 'entity_state_status_data_list'}
        self.assertEqual(set(context.keys()), expected_keys)
        self.assertEqual(context['entity'], entity)
        self.assertEqual(context['entity_state_status_data_list'], entity_state_status_data_list)
        return