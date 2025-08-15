"""
Unit tests for IntegrationSyncMixin.
"""

from django.test import TestCase

from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller
from hi.apps.common.processing_result import ProcessingResult

from hi.integrations.sync_mixins import IntegrationSyncMixin


class TestSynchronizer(IntegrationSyncMixin):
    """Test class that uses the IntegrationSyncMixin."""
    pass


class IntegrationSyncMixinTestCase(TestCase):
    """Test cases for IntegrationSyncMixin functionality."""

    def setUp(self):
        """Set up test data."""
        self.synchronizer = TestSynchronizer()
        self.result = ProcessingResult(title='Test Sync Result')
        
        # Create a test entity
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT',
            integration_id='test_integration',
            integration_name='test_device_1'
        )
        
        # Create entity state
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='DISCRETE',
            name='Test State'
        )

    def test_remove_entity_intelligently_no_user_data(self):
        """Test complete deletion when entity has no user data."""
        # Create only integration data
        EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Data',
            value='Integration-specific data',
            value_type_str='TEXT',
            attribute_type_str='CONFIGURATION',
            integration_key_str='test_integration:test_device_1'
        )
        
        Sensor.objects.create(
            name='Integration Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        entity_id = self.entity.id
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Entity should be completely deleted
        self.assertFalse(Entity.objects.filter(id=entity_id).exists())
        
        # Check result message
        self.assertEqual(len(self.result.message_list), 1)
        self.assertIn('Removed stale TestIntegration entity', self.result.message_list[0])

    def test_remove_entity_intelligently_with_user_data(self):
        """Test preservation when entity has user data."""
        # Create user-created attribute
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='This is a user note',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
            # integration_key_str is None (user-created)
        )
        
        # Create integration attribute
        integration_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Data',
            value='Integration data',
            value_type_str='TEXT',
            attribute_type_str='CONFIGURATION',
            integration_key_str='test_integration:test_device_1'
        )
        
        # Create integration sensor
        integration_sensor = Sensor.objects.create(
            name='Integration Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        # Create integration controller
        integration_controller = Controller.objects.create(
            name='Integration Controller',
            entity_state=self.entity_state,
            controller_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='controller_1'
        )
        
        original_name = self.entity.name
        entity_id = self.entity.id
        state_id = self.entity_state.id
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Entity should still exist but be disconnected
        self.assertTrue(Entity.objects.filter(id=entity_id).exists())
        
        # Reload entity
        self.entity.refresh_from_db()
        
        # Check entity is disconnected
        self.assertIsNone(self.entity.integration_id)
        self.assertIsNone(self.entity.integration_name)
        self.assertEqual(self.entity.name, f'[Disconnected] {original_name}')
        
        # User attribute should still exist
        self.assertTrue(EntityAttribute.objects.filter(id=user_attr.id).exists())
        
        # Integration attribute should be deleted
        self.assertFalse(EntityAttribute.objects.filter(id=integration_attr.id).exists())
        
        # Integration sensor should be deleted
        self.assertFalse(Sensor.objects.filter(id=integration_sensor.id).exists())
        
        # Integration controller should be deleted
        self.assertFalse(Controller.objects.filter(id=integration_controller.id).exists())
        
        # Entity state should be deleted (orphaned)
        self.assertFalse(EntityState.objects.filter(id=state_id).exists())
        
        # Check result message
        self.assertEqual(len(self.result.message_list), 1)
        self.assertIn('Preserved TestIntegration entity', self.result.message_list[0])
        self.assertIn('disconnected from integration', self.result.message_list[0])

    def test_preserve_entity_state_with_remaining_user_components(self):
        """Test that entity states are preserved when user components remain."""
        # Create user-created attribute
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User note',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
        )
        
        # Create integration sensor
        integration_sensor = Sensor.objects.create(
            name='Integration Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        # Create user sensor (should preserve the state)
        user_sensor = Sensor.objects.create(
            name='User Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE'
        )
        
        state_id = self.entity_state.id
        user_sensor_id = user_sensor.id
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Entity state should still exist (has user sensor)
        self.assertTrue(EntityState.objects.filter(id=state_id).exists())
        
        # User sensor should still exist
        self.assertTrue(Sensor.objects.filter(id=user_sensor_id).exists())
        
        # Integration sensor should be deleted
        self.assertFalse(Sensor.objects.filter(id=integration_sensor.id).exists())

    def test_disconnected_name_not_duplicated(self):
        """Test that [Disconnected] prefix is not added if already present."""
        # Set entity name to already have disconnected prefix
        self.entity.name = '[Disconnected] Already Disconnected'
        self.entity.save()
        
        # Create user data
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User note',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
        )
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Reload entity
        self.entity.refresh_from_db()
        
        # Name should not have duplicate prefix
        self.assertEqual(self.entity.name, '[Disconnected] Already Disconnected')
        self.assertNotIn('[Disconnected] [Disconnected]', self.entity.name)

    def test_multiple_entity_states_mixed_preservation(self):
        """Test handling of multiple entity states with different preservation needs."""
        # Create user data to trigger preservation
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User note',
            value_type_str='TEXT',
            attribute_type_str='DOCUMENTATION'
        )
        
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
        
        # Second state: mixed components (will be preserved)
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
        
        state1_id = self.entity_state.id
        state2_id = entity_state2.id
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # First state should be deleted (orphaned)
        self.assertFalse(EntityState.objects.filter(id=state1_id).exists())
        
        # Second state should be preserved (has user sensor)
        self.assertTrue(EntityState.objects.filter(id=state2_id).exists())
        
        # Integration sensors should be deleted
        self.assertFalse(Sensor.objects.filter(id=integration_sensor1.id).exists())
        self.assertFalse(Sensor.objects.filter(id=integration_sensor2.id).exists())
        
        # User sensor should be preserved
        self.assertTrue(Sensor.objects.filter(id=user_sensor2.id).exists())