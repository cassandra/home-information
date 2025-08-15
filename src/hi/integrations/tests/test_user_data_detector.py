"""
Unit tests for EntityUserDataDetector utility.
"""

from django.test import TestCase

from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller

from hi.integrations.user_data_detector import EntityUserDataDetector


class EntityUserDataDetectorTestCase(TestCase):
    """Test cases for EntityUserDataDetector functionality."""

    def setUp(self):
        """Set up test data."""
        # Create a test entity
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT',
            integration_id='test_integration',
            integration_name='test_device_1'
        )
        
        # Create entity state for testing sensors/controllers
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='DISCRETE',
            name='Test State'
        )

    def test_has_user_created_attributes_with_user_data(self):
        """Test detection of user-created attributes."""
        # Create a user-created attribute (no integration_key_str)
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='This is a user note',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
            # integration_key_str is None (user-created)
        )
        
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertTrue(result)

    def test_has_user_created_attributes_with_integration_data_only(self):
        """Test that integration-created attributes don't trigger preservation."""
        # Create an integration-created attribute
        EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Data',
            value='Integration-specific data',
            value_type_str='TEXT',
            attribute_type_str='CONFIGURATION',
            integration_key_str='test_integration:test_device_1'
        )
        
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertFalse(result)

    def test_has_user_created_attributes_no_attributes(self):
        """Test entity with no attributes."""
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertFalse(result)

    def test_has_user_created_attributes_mixed_attributes(self):
        """Test entity with both user and integration attributes."""
        # Create both types
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User data',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
            # integration_key_str is None (user-created)
        )
        EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Data',
            value='Integration data',
            value_type_str='TEXT',
            attribute_type_str='CONFIGURATION',
            integration_key_str='test_integration:test_device_1'
        )
        
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertTrue(result)  # Should preserve due to user attribute

    def test_get_integration_related_sensors(self):
        """Test identification of integration-related sensors."""
        # Create integration sensor
        integration_sensor = Sensor.objects.create(
            name='Integration Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        # Create user sensor (no integration)
        user_sensor = Sensor.objects.create(
            name='User Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE'
            # integration_id is None
        )
        
        sensor_ids = EntityUserDataDetector.get_integration_related_sensors(self.entity)
        
        self.assertEqual(len(sensor_ids), 1)
        self.assertIn(integration_sensor.id, sensor_ids)
        self.assertNotIn(user_sensor.id, sensor_ids)

    def test_get_integration_related_controllers(self):
        """Test identification of integration-related controllers."""
        # Create integration controller
        integration_controller = Controller.objects.create(
            name='Integration Controller',
            entity_state=self.entity_state,
            controller_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='controller_1'
        )
        
        # Create user controller (no integration)
        user_controller = Controller.objects.create(
            name='User Controller',
            entity_state=self.entity_state,
            controller_type_str='DISCRETE'
            # integration_id is None
        )
        
        controller_ids = EntityUserDataDetector.get_integration_related_controllers(self.entity)
        
        self.assertEqual(len(controller_ids), 1)
        self.assertIn(integration_controller.id, controller_ids)
        self.assertNotIn(user_controller.id, controller_ids)

    def test_get_orphaned_entity_states_all_integration(self):
        """Test detection of entity states that become orphaned when all sensors/controllers are integration-related."""
        # Create integration sensor and controller
        integration_sensor = Sensor.objects.create(
            name='Integration Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        integration_controller = Controller.objects.create(
            name='Integration Controller',
            entity_state=self.entity_state,
            controller_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='controller_1'
        )
        
        # Get IDs to remove
        sensor_ids = {integration_sensor.id}
        controller_ids = {integration_controller.id}
        
        orphaned_ids = EntityUserDataDetector.get_orphaned_entity_states(
            self.entity, sensor_ids, controller_ids
        )
        
        self.assertEqual(len(orphaned_ids), 1)
        self.assertIn(self.entity_state.id, orphaned_ids)

    def test_get_orphaned_entity_states_with_remaining_user_components(self):
        """Test that entity states with remaining user sensors/controllers are not orphaned."""
        # Create integration sensor
        integration_sensor = Sensor.objects.create(
            name='Integration Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        # Create user sensor (should keep the state)
        Sensor.objects.create(
            name='User Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE'
            # integration_id is None
        )
        
        # Only remove integration sensor
        sensor_ids = {integration_sensor.id}
        controller_ids = set()
        
        orphaned_ids = EntityUserDataDetector.get_orphaned_entity_states(
            self.entity, sensor_ids, controller_ids
        )
        
        self.assertEqual(len(orphaned_ids), 0)  # State should not be orphaned

    def test_multiple_entity_states(self):
        """Test handling multiple entity states with different orphan status."""
        # Create second entity state
        entity_state2 = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='CONTINUOUS',
            name='Test State 2'
        )
        
        # First state: only integration components (will be orphaned)
        integration_sensor1 = Sensor.objects.create(
            name='Integration Sensor 1',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        # Second state: mixed components (will not be orphaned)
        integration_sensor2 = Sensor.objects.create(
            name='Integration Sensor 2',
            entity_state=entity_state2,
            sensor_type_str='CONTINUOUS',
            integration_id='test_integration',
            integration_name='sensor_2'
        )
        
        Sensor.objects.create(
            name='User Sensor 2',
            entity_state=entity_state2,
            sensor_type_str='CONTINUOUS'
        )
        
        # Remove all integration sensors
        sensor_ids = {integration_sensor1.id, integration_sensor2.id}
        controller_ids = set()
        
        orphaned_ids = EntityUserDataDetector.get_orphaned_entity_states(
            self.entity, sensor_ids, controller_ids
        )
        
        self.assertEqual(len(orphaned_ids), 1)
        self.assertIn(self.entity_state.id, orphaned_ids)
        self.assertNotIn(entity_state2.id, orphaned_ids)
