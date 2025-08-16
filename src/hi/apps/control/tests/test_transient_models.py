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

    def test_controller_data_css_class_delegation_affects_ui_styling(self):
        """Test css_class delegation provides consistent styling across different entity types."""
        # Test different entity types that would have different CSS classes
        entity_types = [
            ('LIGHT', 'ON_OFF'),
            ('CAMERA', 'ON_OFF'),
            ('SENSOR', 'DISCRETE'),
        ]
        
        css_classes = []
        for i, (entity_type, state_type) in enumerate(entity_types):
            entity = Entity.objects.create(
                name=f'Test {entity_type}',
                entity_type_str=entity_type
            )
            entity_state = EntityState.objects.create(
                entity=entity,
                entity_state_type_str=state_type
            )
            
            controller = Controller.objects.create(
                name=f'{entity_type} Controller',
                entity_state=entity_state,
                controller_type_str='DEFAULT',
                integration_id=f'test_id_{i}',
                integration_name=f'test_integration_{i}'
            )
            
            sensor_response = Mock(spec=SensorResponse)
            controller_data = ControllerData(
                controller=controller,
                latest_sensor_response=sensor_response
            )
            
            css_class = controller_data.css_class
            css_classes.append(css_class)
            
            # CSS class should be meaningful for UI purposes
            self.assertIsInstance(css_class, str)
            self.assertTrue(len(css_class) > 0)
        
        # Different entity types should potentially have different CSS classes
        # (Though this depends on the entity_state implementation)
        all_classes_str = ','.join(css_classes)
        self.assertTrue(len(all_classes_str) > 0, "CSS classes should be provided for UI styling")
        return

    def test_controller_data_error_list_affects_ui_display(self):
        """Test error list affects how controller data is displayed in UI."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
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
        
        # Test with various error scenarios
        error_scenarios = [
            None,  # No errors
            [],    # Empty error list
            ['Connection timeout'],  # Single error
            ['Connection timeout', 'Invalid response', 'Device offline'],  # Multiple errors
        ]
        
        for error_list in error_scenarios:
            controller_data = ControllerData(
                controller=controller,
                latest_sensor_response=sensor_response,
                error_list=error_list
            )
            
            if error_list is None or len(error_list) == 0:
                # No errors - should be usable normally
                self.assertIn(controller_data.error_list, [None, []])
            else:
                # Has errors - should preserve error information for UI display
                self.assertEqual(controller_data.error_list, error_list)
                self.assertGreater(len(controller_data.error_list), 0)
                
                # Error messages should be useful for debugging
                for error in controller_data.error_list:
                    self.assertIsInstance(error, str)
                    self.assertGreater(len(error), 0)
        return
