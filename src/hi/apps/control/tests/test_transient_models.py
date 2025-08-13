import logging
from unittest.mock import Mock

from hi.apps.control.transient_models import ControllerData
from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestControllerData(BaseTestCase):

    def test_controller_data_initialization(self):
        """Test ControllerData initialization - critical for UI data structure."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        sensor_response = Mock(spec=SensorResponse)
        error_list = ['Error 1', 'Error 2']
        
        controller_data = ControllerData(
            controller=controller,
            latest_sensor_response=sensor_response,
            error_list=error_list
        )
        
        # Should properly initialize all fields
        self.assertEqual(controller_data.controller, controller)
        self.assertEqual(controller_data.latest_sensor_response, sensor_response)
        self.assertEqual(controller_data.error_list, error_list)
        return

    def test_controller_data_optional_error_list(self):
        """Test ControllerData with optional error list - important for error handling."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        sensor_response = Mock(spec=SensorResponse)
        
        controller_data = ControllerData(
            controller=controller,
            latest_sensor_response=sensor_response
        )
        
        # Should handle optional error_list
        self.assertEqual(controller_data.controller, controller)
        self.assertEqual(controller_data.latest_sensor_response, sensor_response)
        self.assertIsNone(controller_data.error_list)
        return

    def test_controller_data_css_class_delegation(self):
        """Test css_class property delegation - critical for UI styling."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        # Mock entity_state.css_class using patch
        with self.assertRaises(AttributeError):
            # css_class is a property, not settable directly
            entity_state.css_class = 'test-css-class'
        
        controller = Controller.objects.create(
            name='Test Controller',
            entity_state=entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        sensor_response = Mock(spec=SensorResponse)
        
        controller_data = ControllerData(
            controller=controller,
            latest_sensor_response=sensor_response
        )
        
        # Should delegate to entity_state.css_class
        # (The actual css_class value depends on entity_state implementation)
        css_class = controller_data.css_class
        self.assertIsNotNone(css_class)  # Should return some CSS class
        return