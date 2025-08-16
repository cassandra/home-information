"""
Unit tests for EntityUserDataDetector utility.
"""

from django.test import TestCase

from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller

from hi.integrations.user_data_detector import EntityUserDataDetector
from django.db import IntegrityError


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
        # Verify initial state - no user attributes
        result_before = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertFalse(result_before)
        
        # Create a user-created attribute (no integration_key_str)
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='This is a user note',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
            # integration_key_str is None (user-created)
        )
        
        # Verify detection of user-created attribute
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertTrue(result)
        
        # Verify database state remains unchanged (read-only operation)
        user_attr.refresh_from_db()
        self.assertEqual(user_attr.name, 'User Note')
        self.assertEqual(user_attr.value, 'This is a user note')
        self.assertIsNone(user_attr.integration_key_str)
        
        # Verify entity state unchanged
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.attributes.count(), 1)

    def test_has_user_created_attributes_with_integration_data_only(self):
        """Test that integration-created attributes don't trigger preservation."""
        # Create an integration-created attribute
        integration_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Data',
            value='Integration-specific data',
            value_type_str='TEXT',
            attribute_type_str='CONFIGURATION',
            integration_key_str='test_integration:test_device_1'
        )
        
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertFalse(result)
        
        # Verify database state remains unchanged
        integration_attr.refresh_from_db()
        self.assertEqual(integration_attr.integration_key_str, 'test_integration:test_device_1')
        self.assertEqual(self.entity.attributes.count(), 1)
        
        # Verify specifically that only integration attributes exist
        user_attrs = self.entity.attributes.filter(integration_key_str__isnull=True)
        self.assertEqual(user_attrs.count(), 0)

    def test_has_user_created_attributes_no_attributes(self):
        """Test entity with no attributes."""
        # Verify entity has no attributes initially
        self.assertEqual(self.entity.attributes.count(), 0)
        
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertFalse(result)
        
        # Verify database state unchanged
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.attributes.count(), 0)

    def test_has_user_created_attributes_mixed_attributes(self):
        """Test entity with both user and integration attributes."""
        # Create both types
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User data',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
            # integration_key_str is None (user-created)
        )
        integration_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Data',
            value='Integration data',
            value_type_str='TEXT',
            attribute_type_str='CONFIGURATION',
            integration_key_str='test_integration:test_device_1'
        )
        
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertTrue(result)  # Should preserve due to user attribute
        
        # Verify both attributes exist with correct types
        self.assertEqual(self.entity.attributes.count(), 2)
        user_attrs = self.entity.attributes.filter(integration_key_str__isnull=True)
        integration_attrs = self.entity.attributes.filter(integration_key_str__isnull=False)
        
        self.assertEqual(user_attrs.count(), 1)
        self.assertEqual(integration_attrs.count(), 1)
        self.assertEqual(user_attrs.first(), user_attr)
        self.assertEqual(integration_attrs.first(), integration_attr)

    def test_get_integration_related_sensors(self):
        """Test identification of integration-related sensors."""
        # Verify initial state - no sensors
        initial_sensor_ids = EntityUserDataDetector.get_integration_related_sensors(self.entity)
        self.assertEqual(len(initial_sensor_ids), 0)
        
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
        
        # Verify exact result set
        self.assertEqual(len(sensor_ids), 1)
        self.assertIn(integration_sensor.id, sensor_ids)
        self.assertNotIn(user_sensor.id, sensor_ids)
        self.assertEqual(sensor_ids, {integration_sensor.id})
        
        # Verify database state unchanged (read-only operation)
        integration_sensor.refresh_from_db()
        user_sensor.refresh_from_db()
        self.assertEqual(integration_sensor.integration_id, 'test_integration')
        self.assertIsNone(user_sensor.integration_id)
        
        # Verify all sensors still exist
        total_sensors = self.entity_state.sensors.count()
        self.assertEqual(total_sensors, 2)

    def test_get_integration_related_controllers(self):
        """Test identification of integration-related controllers."""
        # Verify initial state - no controllers
        initial_controller_ids = EntityUserDataDetector.get_integration_related_controllers(self.entity)
        self.assertEqual(len(initial_controller_ids), 0)
        
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
        
        # Verify exact result set
        self.assertEqual(len(controller_ids), 1)
        self.assertIn(integration_controller.id, controller_ids)
        self.assertNotIn(user_controller.id, controller_ids)
        self.assertEqual(controller_ids, {integration_controller.id})
        
        # Verify database state unchanged (read-only operation)
        integration_controller.refresh_from_db()
        user_controller.refresh_from_db()
        self.assertEqual(integration_controller.integration_id, 'test_integration')
        self.assertIsNone(user_controller.integration_id)
        
        # Verify all controllers still exist
        total_controllers = self.entity_state.controllers.count()
        self.assertEqual(total_controllers, 2)

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
        
        # Verify exact result set
        self.assertEqual(len(orphaned_ids), 1)
        self.assertIn(self.entity_state.id, orphaned_ids)
        self.assertEqual(orphaned_ids, {self.entity_state.id})
        
        # Verify database state unchanged (read-only operation)
        integration_sensor.refresh_from_db()
        integration_controller.refresh_from_db()
        self.entity_state.refresh_from_db()
        
        # Verify the state still has its components
        self.assertEqual(self.entity_state.sensors.count(), 1)
        self.assertEqual(self.entity_state.controllers.count(), 1)

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
        user_sensor = Sensor.objects.create(
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
        
        # Verify exact result - no orphaned states
        self.assertEqual(len(orphaned_ids), 0)
        self.assertEqual(orphaned_ids, set())
        
        # Verify database state unchanged
        integration_sensor.refresh_from_db()
        user_sensor.refresh_from_db()
        self.entity_state.refresh_from_db()
        
        # Verify the state has both sensors
        self.assertEqual(self.entity_state.sensors.count(), 2)
        remaining_sensors_after_removal = self.entity_state.sensors.exclude(
            id__in=sensor_ids
        )
        self.assertEqual(remaining_sensors_after_removal.count(), 1)
        self.assertEqual(remaining_sensors_after_removal.first(), user_sensor)

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
        
        user_sensor2 = Sensor.objects.create(
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
        
        # Verify exact result set
        self.assertEqual(len(orphaned_ids), 1)
        self.assertIn(self.entity_state.id, orphaned_ids)
        self.assertNotIn(entity_state2.id, orphaned_ids)
        self.assertEqual(orphaned_ids, {self.entity_state.id})
        
        # Verify database state unchanged
        self.entity_state.refresh_from_db()
        entity_state2.refresh_from_db()
        
        # Verify entity has both states
        self.assertEqual(self.entity.states.count(), 2)
        
        # Verify state 2 would retain user sensor
        remaining_sensors_state2 = entity_state2.sensors.exclude(id__in=sensor_ids)
        self.assertEqual(remaining_sensors_state2.count(), 1)
        self.assertEqual(remaining_sensors_state2.first(), user_sensor2)

    # Additional comprehensive test cases

    def test_has_user_created_attributes_with_null_entity(self):
        """Test error handling with null entity parameter."""
        with self.assertRaises(AttributeError):
            EntityUserDataDetector.has_user_created_attributes(None)

    def test_has_user_created_attributes_with_multiple_user_attributes(self):
        """Test detection when multiple user attributes exist."""
        # Create multiple user attributes
        attr1 = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note 1',
            value='First note',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
        )
        attr2 = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note 2',
            value='Second note',
            value_type_str='TEXT',
            attribute_type_str='CONFIGURATION'
        )
        
        result = EntityUserDataDetector.has_user_created_attributes(self.entity)
        self.assertTrue(result)
        
        # Verify both attributes exist and are user-created
        user_attrs = self.entity.attributes.filter(integration_key_str__isnull=True)
        self.assertEqual(user_attrs.count(), 2)
        self.assertIn(attr1, user_attrs)
        self.assertIn(attr2, user_attrs)

    def test_get_integration_related_sensors_entity_with_no_states(self):
        """Test sensor detection for entity with no states."""
        # Create entity with no states
        empty_entity = Entity.objects.create(
            name='Empty Entity',
            entity_type_str='GENERIC',
            integration_id='test_integration',
            integration_name='empty_device'
        )
        
        sensor_ids = EntityUserDataDetector.get_integration_related_sensors(empty_entity)
        self.assertEqual(len(sensor_ids), 0)
        self.assertEqual(sensor_ids, set())

    def test_get_integration_related_controllers_entity_with_no_states(self):
        """Test controller detection for entity with no states."""
        # Create entity with no states
        empty_entity = Entity.objects.create(
            name='Empty Entity',
            entity_type_str='GENERIC',
            integration_id='test_integration',
            integration_name='empty_device'
        )
        
        controller_ids = EntityUserDataDetector.get_integration_related_controllers(empty_entity)
        self.assertEqual(len(controller_ids), 0)
        self.assertEqual(controller_ids, set())

    def test_get_integration_related_sensors_multiple_integrations(self):
        """Test sensor detection across multiple integrations."""
        # Create sensors from different integrations
        sensor1 = Sensor.objects.create(
            name='Integration 1 Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='integration_1',
            integration_name='sensor_1'
        )
        sensor2 = Sensor.objects.create(
            name='Integration 2 Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='integration_2',
            integration_name='sensor_2'
        )
        user_sensor = Sensor.objects.create(
            name='User Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE'
        )
        
        sensor_ids = EntityUserDataDetector.get_integration_related_sensors(self.entity)
        
        # Verify all integration sensors are detected, user sensor is not
        self.assertEqual(len(sensor_ids), 2)
        self.assertIn(sensor1.id, sensor_ids)
        self.assertIn(sensor2.id, sensor_ids)
        self.assertNotIn(user_sensor.id, sensor_ids)
        self.assertEqual(sensor_ids, {sensor1.id, sensor2.id})

    def test_get_orphaned_entity_states_empty_removal_sets(self):
        """Test orphan detection with empty removal sets."""
        # Create sensors and controllers
        Sensor.objects.create(
            name='Test Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        Controller.objects.create(
            name='Test Controller',
            entity_state=self.entity_state,
            controller_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='controller_1'
        )
        
        # Test with empty removal sets - no states should be orphaned
        orphaned_ids = EntityUserDataDetector.get_orphaned_entity_states(
            self.entity, set(), set()
        )
        
        self.assertEqual(len(orphaned_ids), 0)
        self.assertEqual(orphaned_ids, set())

    def test_get_orphaned_entity_states_no_components(self):
        """Test orphan detection for state with no sensors or controllers."""
        # EntityState exists but has no sensors or controllers
        orphaned_ids = EntityUserDataDetector.get_orphaned_entity_states(
            self.entity, set(), set()
        )
        
        # State with no components should be orphaned
        self.assertEqual(len(orphaned_ids), 1)
        self.assertIn(self.entity_state.id, orphaned_ids)

    def test_integration_key_str_consistency(self):
        """Test that integration_key_str format is handled consistently."""
        # Test various integration key formats
        test_keys = [
            'simple_key',
            'integration:device',
            'complex.integration:device_name_with_underscores',
            'integration:device:sub_component'
        ]
        
        for key in test_keys:
            with self.subTest(integration_key=key):
                # Create attribute with specific integration key
                attr = EntityAttribute.objects.create(
                    entity=self.entity,
                    name=f'Test Attr {key}',
                    value='test value',
                    value_type_str='TEXT',
                    attribute_type_str='CONFIGURATION',
                    integration_key_str=key
                )
                
                # Should not be detected as user-created
                result = EntityUserDataDetector.has_user_created_attributes(self.entity)
                self.assertFalse(result)
                
                # Clean up for next iteration
                attr.delete()

    def test_database_constraint_behavior(self):
        """Test database constraints for integration keys."""
        from django.db import transaction
        
        # Test unique constraint on Entity integration key
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Entity.objects.create(
                    name='Duplicate Entity',
                    entity_type_str='LIGHT',
                    integration_id='test_integration',  # Same as setUp entity
                    integration_name='test_device_1'    # Same as setUp entity
                )
        
        # Test unique constraint on Sensor integration key
        Sensor.objects.create(
            name='Sensor 1',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_sensor_integration',
            integration_name='sensor_device_1'
        )
        
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Sensor.objects.create(
                    name='Duplicate Sensor',
                    entity_state=self.entity_state,
                    sensor_type_str='DISCRETE',
                    integration_id='test_sensor_integration',  # Same as sensor1
                    integration_name='sensor_device_1'         # Same as sensor1
                )
