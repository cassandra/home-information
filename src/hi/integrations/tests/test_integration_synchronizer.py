"""
Unit tests for IntegrationSynchronizer's intelligent entity-removal helper.
"""

import logging

from django.test import TestCase, TransactionTestCase

from hi.apps.attribute.enums import AttributeType
from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller
from hi.integrations.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.sync_result import IntegrationSyncResult

logging.disable(logging.CRITICAL)


class TestSynchronizer(IntegrationSynchronizer):
    """Concrete IntegrationSynchronizer used to exercise the
    intelligent-removal helper. Stubs the abstract hooks so the class
    can be instantiated; sync() itself is not exercised here."""

    def get_result_title(self, is_initial_import=False):
        return 'Test Sync Result'

    def _sync_impl(self, is_initial_import=False):
        return IntegrationSyncResult(
            title=self.get_result_title(is_initial_import=is_initial_import),
        )


class IntegrationSynchronizerRemovalTestCase(TestCase):
    """Test cases for IntegrationSynchronizer's _remove_entity_intelligently."""

    def setUp(self):
        """Set up test data."""
        self.synchronizer = TestSynchronizer()
        self.result = IntegrationSyncResult(title='Test Import Result')
        
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
            attribute_type_str=str(AttributeType.PREDEFINED),
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

        # Hard delete records the entity name in removed_list and
        # adds nothing to info_list — the per-category list itself
        # is what enumerates 'what was removed'.
        self.assertEqual(self.result.removed_list, ['Test Entity'])
        self.assertEqual(self.result.info_list, [])
        
        # Verify complete cleanup - no orphaned attributes or states
        self.assertEqual(EntityAttribute.objects.filter(entity_id=entity_id).count(), 0)
        self.assertEqual(EntityState.objects.filter(entity_id=entity_id).count(), 0)
        self.assertEqual(Sensor.objects.filter(entity_state__entity_id=entity_id).count(), 0)

    def test_remove_entity_intelligently_with_user_data(self):
        """Test preservation when entity has user data."""
        # Create user-created attribute
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='This is a user note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
            # integration_key_str is None (user-created)
        )
        
        # Create integration attribute
        integration_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Data',
            value='Integration data',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.PREDEFINED),
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
        
        # Check entity is detached: active integration identity is
        # cleared, previous identity is recorded, and the entity name
        # is preserved verbatim (the detached state is signaled
        # structurally, not by mutating the name).
        self.assertIsNone(self.entity.integration_id)
        self.assertIsNone(self.entity.integration_name)
        self.assertEqual(self.entity.previous_integration_id, 'test_integration')
        self.assertEqual(self.entity.name, original_name)
        
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
        
        # Preservation records the original name in removed_list
        # and surfaces a diagnostic info note — the operator wants
        # to know an entity was detached, not just see a name in a list.
        self.assertEqual(self.result.removed_list, [original_name])
        self.assertEqual(len(self.result.info_list), 1)
        message = self.result.info_list[0]
        self.assertIn('Preserved TestIntegration item', message)
        self.assertIn('detached from integration', message)
        self.assertIn(original_name, message)
        
        # Verify integration payload is cleared
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.integration_payload, {})
        
        # Verify entity maintains referential integrity
        remaining_attributes = EntityAttribute.objects.filter(entity=self.entity)
        self.assertEqual(remaining_attributes.count(), 1)
        self.assertEqual(remaining_attributes.first().name, 'User Note')
        
        # Verify no orphaned integration data remains
        orphaned_attrs = EntityAttribute.objects.filter(
            entity=self.entity, 
            integration_key_str__isnull=False
        )
        self.assertEqual(orphaned_attrs.count(), 0)

    def test_preserve_entity_state_with_remaining_user_components(self):
        """Test that entity states are preserved when user components remain."""
        # Create user-created attribute
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
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

    def test_multiple_entity_states_mixed_preservation(self):
        """Test handling of multiple entity states with different preservation needs."""
        # Create user data to trigger preservation
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
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

    def test_remove_entity_with_no_states(self):
        """Test deletion of entity with no entity states."""
        # Remove the default entity state
        self.entity_state.delete()
        
        # Create only entity attributes
        EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Data',
            value='Some data',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str='test_integration:test_device_1'
        )
        
        entity_id = self.entity.id
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Entity should be completely deleted; name recorded.
        self.assertFalse(Entity.objects.filter(id=entity_id).exists())
        self.assertEqual(self.result.removed_list, ['Test Entity'])

    def test_entity_with_integration_payload_preservation(self):
        """Test that integration_payload is preserved during entity preservation."""
        # Set up entity with integration payload
        original_payload = {
            'device_type': 'light',
            'capabilities': ['brightness', 'color'],
            'last_seen': '2024-01-01T00:00:00Z'
        }
        self.entity.integration_payload = original_payload
        self.entity.save()
        
        # Create user data to trigger preservation
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='Important note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
        )
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Verify entity is preserved and integration fields are cleared
        self.entity.refresh_from_db()
        self.assertIsNone(self.entity.integration_id)
        self.assertIsNone(self.entity.integration_name)
        # Integration payload should be preserved for historical value
        self.assertEqual(self.entity.integration_payload, original_payload)

    def test_entity_with_multiple_integration_attributes(self):
        """Test removal of multiple integration attributes while preserving user data."""
        # Create multiple integration attributes
        integration_attrs = []
        for i in range(3):
            attr = EntityAttribute.objects.create(
                entity=self.entity,
                name=f'Integration Config {i}',
                value=f'Config value {i}',
                value_type_str='TEXT',
                attribute_type_str=str(AttributeType.PREDEFINED),
                integration_key_str=f'test_integration:config_{i}'
            )
            integration_attrs.append(attr)
        
        # Create user attribute
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Documentation',
            value='User-created note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
        )
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # All integration attributes should be deleted
        for attr in integration_attrs:
            self.assertFalse(EntityAttribute.objects.filter(id=attr.id).exists())
        
        # User attribute should be preserved
        self.assertTrue(EntityAttribute.objects.filter(id=user_attr.id).exists())
        
        # Verify only user attributes remain
        remaining_attrs = EntityAttribute.objects.filter(entity=self.entity)
        self.assertEqual(remaining_attrs.count(), 1)
        self.assertEqual(remaining_attrs.first().name, 'User Documentation')

    def test_complex_entity_state_relationships(self):
        """Test handling of entity with complex sensor/controller relationships."""
        # Create multiple entity states
        state2 = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='CONTINUOUS',
            name='Temperature State'
        )
        
        state3 = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='DISCRETE',
            name='Motion State'
        )
        
        # Create mixed sensors and controllers across states
        # State 1: integration sensor + user controller
        integration_sensor1 = Sensor.objects.create(
            name='Integration Sensor 1',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        user_controller1 = Controller.objects.create(
            name='User Controller 1',
            entity_state=self.entity_state,
            controller_type_str='DISCRETE'
        )
        
        # State 2: user sensor + integration controller
        user_sensor2 = Sensor.objects.create(
            name='User Sensor 2',
            entity_state=state2,
            sensor_type_str='CONTINUOUS'
        )
        
        integration_controller2 = Controller.objects.create(
            name='Integration Controller 2',
            entity_state=state2,
            controller_type_str='CONTINUOUS',
            integration_id='test_integration',
            integration_name='controller_2'
        )
        
        # State 3: only integration components (will be orphaned)
        integration_sensor3 = Sensor.objects.create(
            name='Integration Sensor 3',
            entity_state=state3,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_3'
        )
        
        # Create user attribute to trigger preservation
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
        )
        
        # Call the method
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Verify entity is preserved
        self.assertTrue(Entity.objects.filter(id=self.entity.id).exists())
        
        # State 1 should be preserved (has user controller)
        self.assertTrue(EntityState.objects.filter(id=self.entity_state.id).exists())
        
        # State 2 should be preserved (has user sensor)
        self.assertTrue(EntityState.objects.filter(id=state2.id).exists())
        
        # State 3 should be deleted (orphaned)
        self.assertFalse(EntityState.objects.filter(id=state3.id).exists())
        
        # Integration components should be deleted
        self.assertFalse(Sensor.objects.filter(id=integration_sensor1.id).exists())
        self.assertFalse(Controller.objects.filter(id=integration_controller2.id).exists())
        self.assertFalse(Sensor.objects.filter(id=integration_sensor3.id).exists())
        
        # User components should be preserved
        self.assertTrue(Controller.objects.filter(id=user_controller1.id).exists())
        self.assertTrue(Sensor.objects.filter(id=user_sensor2.id).exists())
        
        # User attribute should be preserved
        self.assertTrue(EntityAttribute.objects.filter(id=user_attr.id).exists())

    def test_database_cascade_deletion_integrity(self):
        """Test that complete deletion properly cascades and maintains database integrity."""
        # Create complex entity structure with multiple relationships
        state2 = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='CONTINUOUS',
            name='Second State'
        )
        
        # Create multiple integration components
        sensor1 = Sensor.objects.create(
            name='Integration Sensor 1',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        sensor2 = Sensor.objects.create(
            name='Integration Sensor 2',
            entity_state=state2,
            sensor_type_str='CONTINUOUS',
            integration_id='test_integration',
            integration_name='sensor_2'
        )
        
        controller = Controller.objects.create(
            name='Integration Controller',
            entity_state=self.entity_state,
            controller_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='controller_1'
        )
        
        # Create multiple integration attributes
        attr1 = EntityAttribute.objects.create(
            entity=self.entity,
            name='Config 1',
            value='Value 1',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str='test_integration:config_1'
        )
        
        attr2 = EntityAttribute.objects.create(
            entity=self.entity,
            name='Config 2',
            value='Value 2',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str='test_integration:config_2'
        )
        
        # Store IDs for verification
        entity_id = self.entity.id
        state1_id = self.entity_state.id
        state2_id = state2.id
        component_ids = [sensor1.id, sensor2.id, controller.id]
        attribute_ids = [attr1.id, attr2.id]
        
        # Call deletion (no user data, should delete completely)
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Verify complete cascade deletion
        self.assertFalse(Entity.objects.filter(id=entity_id).exists())
        self.assertFalse(EntityState.objects.filter(id__in=[state1_id, state2_id]).exists())
        self.assertFalse(Sensor.objects.filter(id__in=component_ids).exists())
        self.assertFalse(Controller.objects.filter(id__in=component_ids).exists())
        self.assertFalse(EntityAttribute.objects.filter(id__in=attribute_ids).exists())
        
        # Hard delete records the name in removed_list; no
        # narrative info entry.
        self.assertEqual(self.result.removed_list, ['Test Entity'])
        self.assertEqual(self.result.info_list, [])

    def test_result_info_list_accumulation(self):
        """Pre-existing info_list entries are preserved when the
        preservation path appends its diagnostic note."""
        self.result.info_list.append('Initial message')
        self.result.info_list.append('Another message')

        # Create user data to trigger preservation.
        EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
        )

        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )

        # 3 entries: 2 pre-existing + 1 preservation note.
        self.assertEqual(len(self.result.info_list), 3)
        self.assertIn('Preserved TestIntegration item', self.result.info_list[2])
        self.assertEqual(self.result.info_list[0], 'Initial message')
        self.assertEqual(self.result.info_list[1], 'Another message')
        # And removed_list captured the name exactly once.
        self.assertEqual(self.result.removed_list, ['Test Entity'])


class IntegrationSynchronizerRemovalTransactionTestCase(TransactionTestCase):
    """Transaction-specific tests for _remove_entity_intelligently."""
    
    def setUp(self):
        """Set up test data."""
        # Ensure subsystem data is populated after database flush
        from hi.apps.config.signals import SettingsInitializer
        initializer = SettingsInitializer()
        initializer.run(sender=None)
        
        self.synchronizer = TestSynchronizer()
        self.result = IntegrationSyncResult(title='Test Import Result')
        
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
    
    def test_data_consistency_during_preservation_operation(self):
        """Test that preservation maintains referential integrity throughout the operation."""
        # Create user attribute to trigger preservation path
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='Critical user note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
        )
        
        # Create complex state structure
        state2 = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='CONTINUOUS',
            name='Temperature State'
        )
        
        # Create mixed integration and user components
        integration_sensor = Sensor.objects.create(
            name='Integration Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        user_sensor = Sensor.objects.create(
            name='User Sensor',
            entity_state=state2,
            sensor_type_str='CONTINUOUS'
            # No integration_id - user created
        )
        
        integration_controller = Controller.objects.create(
            name='Integration Controller',
            entity_state=self.entity_state,
            controller_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='controller_1'
        )
        
        integration_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='Integration Config',
            value='Config data',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str='test_integration:config_1'
        )
        
        # Store initial counts for verification
        initial_entity_count = Entity.objects.count()
        
        # Execute preservation operation
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Verify entity preservation and disconnection
        self.entity.refresh_from_db()
        self.assertIsNotNone(self.entity.previous_integration_id)
        self.assertIsNone(self.entity.integration_id)
        self.assertIsNone(self.entity.integration_name)
        
        # Verify database consistency - no orphaned or invalid foreign keys
        self.assertEqual(Entity.objects.count(), initial_entity_count)
        
        # Verify selective component removal
        self.assertFalse(Sensor.objects.filter(id=integration_sensor.id).exists())
        self.assertTrue(Sensor.objects.filter(id=user_sensor.id).exists())
        self.assertFalse(Controller.objects.filter(id=integration_controller.id).exists())
        
        # Verify attribute handling
        self.assertTrue(EntityAttribute.objects.filter(id=user_attr.id).exists())
        self.assertFalse(EntityAttribute.objects.filter(id=integration_attr.id).exists())
        
        # Verify state preservation logic
        # State 1 should be deleted (orphaned - only had integration components)
        self.assertFalse(EntityState.objects.filter(id=self.entity_state.id).exists())
        # State 2 should be preserved (has user sensor)
        self.assertTrue(EntityState.objects.filter(id=state2.id).exists())
        
        # Verify remaining components have valid foreign key relationships
        remaining_sensors = Sensor.objects.filter(entity_state__entity=self.entity)
        self.assertEqual(remaining_sensors.count(), 1)
        self.assertEqual(remaining_sensors.first().name, 'User Sensor')
        
        remaining_attributes = EntityAttribute.objects.filter(entity=self.entity)
        self.assertEqual(remaining_attributes.count(), 1)
        self.assertEqual(remaining_attributes.first().name, 'User Note')
        
        # Preservation diagnostic surfaces in info_list; the entity
        # name is captured in removed_list.
        self.assertEqual(len(self.result.info_list), 1)
        message = self.result.info_list[0]
        self.assertIn('Preserved TestIntegration item', message)
        self.assertIn('detached from integration', message)
        self.assertEqual(self.result.removed_list, ['Test Entity'])

    def test_preservation_with_database_constraint_validation(self):
        """Test that preservation operations respect database constraints and maintain referential integrity."""
        # Create user attribute to trigger preservation
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='User note',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
        )
        
        # Create integration sensor that will be orphaned (state will be deleted)
        integration_sensor = Sensor.objects.create(
            name='Integration Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        # Create a second entity state with mixed components
        second_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='CONTINUOUS',
            name='Mixed State'
        )
        
        # Integration controller on second state
        integration_controller = Controller.objects.create(
            name='Integration Controller',
            entity_state=second_state,
            controller_type_str='CONTINUOUS',
            integration_id='test_integration',
            integration_name='controller_1'
        )
        
        # User sensor on second state (should preserve the state)
        user_sensor = Sensor.objects.create(
            name='User Sensor',
            entity_state=second_state,
            sensor_type_str='CONTINUOUS'
            # No integration_id - user created
        )
        
        # Store IDs for verification
        first_state_id = self.entity_state.id
        second_state_id = second_state.id
        
        # Execute preservation
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Verify our entity was preserved and disconnected
        self.entity.refresh_from_db()
        self.assertIsNotNone(self.entity.previous_integration_id)
        self.assertIsNone(self.entity.integration_id)
        self.assertIsNone(self.entity.integration_name)
        
        # Integration components should be deleted
        self.assertFalse(Sensor.objects.filter(id=integration_sensor.id).exists())
        self.assertFalse(Controller.objects.filter(id=integration_controller.id).exists())
        
        # First state should be deleted (orphaned - only had integration sensor)
        self.assertFalse(EntityState.objects.filter(id=first_state_id).exists())
        
        # Second state should be preserved (has user sensor)
        self.assertTrue(EntityState.objects.filter(id=second_state_id).exists())
        
        # User components should still exist
        self.assertTrue(Sensor.objects.filter(id=user_sensor.id).exists())
        self.assertTrue(EntityAttribute.objects.filter(id=user_attr.id).exists())
        
        # Preservation note surfaces in info_list.
        self.assertEqual(len(self.result.info_list), 1)
        self.assertIn('Preserved TestIntegration item', self.result.info_list[0])

        # Verify database integrity: remaining state has valid relationships
        remaining_state = EntityState.objects.get(id=second_state_id)
        remaining_sensors = remaining_state.sensors.all()
        self.assertEqual(remaining_sensors.count(), 1)
        self.assertEqual(remaining_sensors.first().name, 'User Sensor')
        
        # Verify entity still has correct relationships
        self.assertEqual(self.entity.states.count(), 1)
        self.assertEqual(self.entity.states.first().id, second_state_id)

    def test_user_data_detection_boundary_conditions(self):
        """Test edge cases in user data detection that determine preservation vs deletion."""
        # Test 1: Entity with only integration attributes (should be deleted)
        integration_only_entity = Entity.objects.create(
            name='Integration Only Entity',
            entity_type_str='LIGHT',
            integration_id='test_integration',
            integration_name='device_2'
        )
        
        EntityAttribute.objects.create(
            entity=integration_only_entity,
            name='Integration Config',
            value='Config value',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str='test_integration:device_2'
        )
        
        entity_id = integration_only_entity.id
        
        self.synchronizer._remove_entity_intelligently(
            integration_only_entity, self.result, 'TestIntegration'
        )
        
        # Should be completely deleted
        self.assertFalse(Entity.objects.filter(id=entity_id).exists())
        
        # Test 2: Entity with mixed attributes (should be preserved)
        mixed_entity = Entity.objects.create(
            name='Mixed Entity',
            entity_type_str='LIGHT',
            integration_id='test_integration',
            integration_name='device_3'
        )
        
        # Add integration attribute
        EntityAttribute.objects.create(
            entity=mixed_entity,
            name='Integration Config',
            value='Config value',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str='test_integration:device_3'
        )
        
        # Add user attribute (should trigger preservation)
        EntityAttribute.objects.create(
            entity=mixed_entity,
            name='User Comment',
            value='User added this',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
            # No integration_key_str - user created
        )
        
        self.synchronizer._remove_entity_intelligently(
            mixed_entity, self.result, 'TestIntegration'
        )
        
        # Should be preserved and disconnected
        mixed_entity.refresh_from_db()
        self.assertIsNotNone(mixed_entity.previous_integration_id)
        self.assertIsNone(mixed_entity.integration_id)
        self.assertIsNone(mixed_entity.integration_name)
        
        # Integration attribute should be deleted, user attribute preserved
        integration_attrs = EntityAttribute.objects.filter(
            entity=mixed_entity,
            integration_key_str__isnull=False
        )
        self.assertEqual(integration_attrs.count(), 0)
        
        user_attrs = EntityAttribute.objects.filter(
            entity=mixed_entity,
            integration_key_str__isnull=True
        )
        self.assertEqual(user_attrs.count(), 1)
        self.assertEqual(user_attrs.first().name, 'User Comment')

    def test_entity_state_orphan_detection_with_mixed_components(self):
        """Test that entity state cleanup correctly identifies orphaned vs preserved states."""
        # Create second entity state for this entity
        second_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='CONTINUOUS',
            name='Temperature State'
        )
        
        # First state: only integration sensor (will be orphaned)
        integration_sensor1 = Sensor.objects.create(
            name='Integration Sensor 1',
            entity_state=self.entity_state,
            sensor_type_str='DISCRETE',
            integration_id='test_integration',
            integration_name='sensor_1'
        )
        
        # Second state: integration controller + user sensor (will be preserved)
        integration_controller = Controller.objects.create(
            name='Integration Controller',
            entity_state=second_state,
            controller_type_str='CONTINUOUS',
            integration_id='test_integration',
            integration_name='controller_1'
        )
        
        user_sensor = Sensor.objects.create(
            name='User Sensor',
            entity_state=second_state,
            sensor_type_str='CONTINUOUS'
            # No integration_id - user created
        )
        
        # Add user data to trigger preservation
        user_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name='User Note',
            value='Important user data',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM)
        )
        
        # Store IDs for verification
        first_state_id = self.entity_state.id
        second_state_id = second_state.id
        
        # Execute preservation
        self.synchronizer._remove_entity_intelligently(
            self.entity, self.result, 'TestIntegration'
        )
        
        # Our entity should be preserved and disconnected
        self.entity.refresh_from_db()
        self.assertIsNotNone(self.entity.previous_integration_id)
        self.assertIsNone(self.entity.integration_id)
        
        # Integration components should be deleted
        self.assertFalse(Sensor.objects.filter(id=integration_sensor1.id).exists())
        self.assertFalse(Controller.objects.filter(id=integration_controller.id).exists())
        
        # First state should be deleted (orphaned)
        self.assertFalse(EntityState.objects.filter(id=first_state_id).exists())
        
        # Second state should be preserved (has user sensor)
        self.assertTrue(EntityState.objects.filter(id=second_state_id).exists())
        
        # User components should remain
        self.assertTrue(Sensor.objects.filter(id=user_sensor.id).exists())
        self.assertTrue(EntityAttribute.objects.filter(id=user_attr.id).exists())
        
        # Verify entity now has only one state
        self.assertEqual(self.entity.states.count(), 1)
        remaining_state = self.entity.states.first()
        self.assertEqual(remaining_state.id, second_state_id)
        
        # Verify remaining state has only user components
        self.assertEqual(remaining_state.sensors.count(), 1)
        self.assertEqual(remaining_state.controllers.count(), 0)
        self.assertEqual(remaining_state.sensors.first().name, 'User Sensor')



class IntegrationSynchronizerOrphanDelegateTestCase(TestCase):
    """Refresh-time entity removal must clean up delegate entities
    (e.g., the Area auto-created when a camera/motion-detector was
    placed in a view) that become orphaned by the removal — the same
    closure the integration-disable path uses."""

    def setUp(self):
        from hi.apps.entity.models import EntityStateDelegation

        self.synchronizer = TestSynchronizer()
        self.result = IntegrationSyncResult(title='Test')
        self.EntityStateDelegation = EntityStateDelegation

        # Camera entity (integration-owned).
        self.camera = Entity.objects.create(
            name='Cam 1',
            entity_type_str='CAMERA',
            integration_id='test_integration',
            integration_name='cam_1',
        )
        self.camera_state = EntityState.objects.create(
            entity=self.camera,
            entity_state_type_str='MOVEMENT',
            name='Motion',
        )

        # Area entity (delegate, Hi-side, no integration_id).
        self.area = Entity.objects.create(
            name='Cam 1 Area',
            entity_type_str='AREA',
        )
        self.EntityStateDelegation.objects.create(
            entity_state=self.camera_state,
            delegate_entity=self.area,
        )

    def test_orphan_delegate_area_is_deleted_when_only_principal_removed(self):
        """Camera removed → Area has no remaining principal → Area
        is part of the closure and gets deleted."""
        camera_id = self.camera.id
        area_id = self.area.id

        self.synchronizer._remove_entity_intelligently(
            self.camera, self.result, 'TestIntegration',
        )

        self.assertFalse(Entity.objects.filter(id=camera_id).exists())
        self.assertFalse(Entity.objects.filter(id=area_id).exists())
        # Both names surface in the result's removed_list.
        self.assertIn('Cam 1', self.result.removed_list)
        self.assertIn('Cam 1 Area', self.result.removed_list)

    def test_shared_delegate_area_survives_when_other_principals_remain(self):
        """Camera A removed; Area still serves Camera B → Area stays."""
        camera_b = Entity.objects.create(
            name='Cam 2',
            entity_type_str='CAMERA',
            integration_id='test_integration',
            integration_name='cam_2',
        )
        camera_b_state = EntityState.objects.create(
            entity=camera_b,
            entity_state_type_str='MOVEMENT',
            name='Motion',
        )
        # Area also delegates from Camera B's state — shared delegate.
        self.EntityStateDelegation.objects.create(
            entity_state=camera_b_state,
            delegate_entity=self.area,
        )

        camera_id = self.camera.id
        area_id = self.area.id

        self.synchronizer._remove_entity_intelligently(
            self.camera, self.result, 'TestIntegration',
        )

        self.assertFalse(Entity.objects.filter(id=camera_id).exists())
        # Area must remain — Camera B still uses it.
        self.assertTrue(Entity.objects.filter(id=area_id).exists())
        # Result reports only Cam 1's removal.
        self.assertEqual(self.result.removed_list, ['Cam 1'])

    def test_orphan_delegate_with_user_data_is_preserved_not_deleted(self):
        """Operator added a custom attribute to the auto-created
        Area → Area is preserved (disconnected/renamed) rather than
        hard-deleted, even though it became an orphan."""
        EntityAttribute.objects.create(
            entity=self.area,
            name='Floor Plan Note',
            value='Has skylight on east side',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM),
        )

        camera_id = self.camera.id
        area_id = self.area.id

        self.synchronizer._remove_entity_intelligently(
            self.camera, self.result, 'TestIntegration',
        )

        self.assertFalse(Entity.objects.filter(id=camera_id).exists())
        # Area persists with operator-added data and is now in
        # the user-managed state (preserve_with_user_data flips
        # is_disabled=True and can_user_delete=True). The Area
        # never had an active integration identity of its own — it
        # was an auto-created delegate of the camera — so the
        # previous_integration_* columns remain NULL on it; the
        # is_disabled gate is the durable detached signal here.
        self.assertTrue(Entity.objects.filter(id=area_id).exists())
        self.area.refresh_from_db()
        self.assertTrue(self.area.is_disabled)
        self.assertTrue(self.area.can_user_delete)

    def test_orphan_delegate_deleted_when_only_principal_has_user_data(self):
        """Camera carries user data so it is detached and preserved;
        Area carries none. Even though the principal survives, the
        Area is correctly hard-deleted — see the rationale
        documented on
        ``EntityIntegrationOperations.remove_entities_with_closure``.
        Pinning this case prevents a well-intentioned future
        refactor from flipping it back to preservation."""
        EntityAttribute.objects.create(
            entity=self.camera,
            name='Lens Notes',
            value='Wide-angle, dome housing',
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM),
        )

        camera_id = self.camera.id
        area_id = self.area.id

        self.synchronizer._remove_entity_intelligently(
            self.camera, self.result, 'TestIntegration',
        )

        # Camera detached and preserved (user data).
        self.assertTrue(Entity.objects.filter(id=camera_id).exists())
        self.camera.refresh_from_db()
        self.assertIsNotNone(self.camera.previous_integration_id)
        # Area is gone — its display purpose is negated once the
        # principal's integration-derived state is removed.
        self.assertFalse(Entity.objects.filter(id=area_id).exists())


class ReconnectDisconnectedItemsFrameworkTests(TestCase):
    """
    Issue #281: framework-level reconnect lives on the
    IntegrationSynchronizer base class, symmetric to disconnect
    (preserve_with_user_data) which lives on EntityIntegrationOperations.
    Each integration only contributes a thin
    ``_rebuild_integration_components`` override; all the boilerplate
    (find candidates, strip prefix, clear previous identity, append
    info_list note, update entity-map) lives here in the base.

    These tests exercise the base method directly with a recording
    subclass, so the per-integration sync tests don't need to
    re-verify the boilerplate.
    """

    INTEGRATION_ID = 'hass'
    INTEGRATION_LABEL = 'Home Assistant'

    def _make_synchronizer(self):
        """Concrete synchronizer that records each
        _rebuild_integration_components dispatch + simulates the
        per-integration converter's effect (sets integration_key)."""
        from hi.integrations.transient_models import IntegrationKey

        captured = []
        integration_id = self.INTEGRATION_ID

        class RecordingSynchronizer(IntegrationSynchronizer):
            def _rebuild_integration_components(self, entity, upstream, result):
                captured.append((entity.id, upstream))
                entity.integration_key = IntegrationKey(
                    integration_id=integration_id,
                    integration_name=upstream['name'],
                )
                entity.save()

        return RecordingSynchronizer(), captured

    def _disconnected_entity(self, name, previous_integration_name):
        return Entity.objects.create(
            name=name,
            entity_type_str='LIGHT',
            previous_integration_id=self.INTEGRATION_ID,
            previous_integration_name=previous_integration_name,
        )

    def _make_upstream_key(self, integration_name):
        from hi.integrations.transient_models import IntegrationKey
        return IntegrationKey(
            integration_id=self.INTEGRATION_ID,
            integration_name=integration_name,
        )

    def test_reconnect_clears_previous_identity_and_inserts_to_entity_map(self):
        """Single secondary match → entity is reconnected end-to-end:
        previous identity cleared (which removes the "Detached from"
        UI badge), converter dispatched, info_list note added, entity
        inserted into the entity-map so the caller's main loop sees
        it as matched. The entity name is preserved verbatim — the
        user's name is not the place we encode connection state."""
        user_edited_name = 'Kitchen Light (user-edited)'
        entity = self._disconnected_entity(
            name=user_edited_name,
            previous_integration_name='light.kitchen',
        )
        upstream_key = self._make_upstream_key('light.kitchen')
        upstream_payload = {'name': 'light.kitchen', 'flavor': 'demo'}

        synchronizer, captured = self._make_synchronizer()
        result = IntegrationSyncResult(title='Test')
        integration_key_to_entity = {}

        synchronizer.reconnect_disconnected_items(
            integration_id=self.INTEGRATION_ID,
            integration_label=self.INTEGRATION_LABEL,
            integration_key_to_upstream={upstream_key: upstream_payload},
            integration_key_to_entity=integration_key_to_entity,
            result=result,
        )

        self.assertEqual(captured, [(entity.id, upstream_payload)])
        entity.refresh_from_db()
        # Name is preserved verbatim — reconnect does not touch it.
        self.assertEqual(entity.name, user_edited_name)
        self.assertIsNone(entity.previous_integration_id)
        self.assertEqual(entity.integration_id, self.INTEGRATION_ID)
        self.assertEqual(integration_key_to_entity, {upstream_key: entity})
        self.assertTrue(any(
            f'Auto-reconnected {self.INTEGRATION_LABEL} item' in note
            for note in result.info_list
        ))

    def test_no_unmatched_short_circuits_without_dispatch(self):
        """All upstream keys already primary-matched →
        _rebuild_integration_components is never invoked."""
        existing_key = self._make_upstream_key('light.existing')
        existing_entity = Entity.objects.create(
            name='Already Connected',
            entity_type_str='LIGHT',
            integration_id=self.INTEGRATION_ID,
            integration_name='light.existing',
        )

        synchronizer, captured = self._make_synchronizer()
        result = IntegrationSyncResult(title='Test')
        integration_key_to_entity = {existing_key: existing_entity}

        synchronizer.reconnect_disconnected_items(
            integration_id=self.INTEGRATION_ID,
            integration_label=self.INTEGRATION_LABEL,
            integration_key_to_upstream={existing_key: {'name': 'light.existing'}},
            integration_key_to_entity=integration_key_to_entity,
            result=result,
        )

        self.assertEqual(captured, [])

    def test_subclass_without_override_raises_clear_error_when_match_found(self):
        """A subclass that doesn't override
        _rebuild_integration_components but whose sync flow has a
        reconnect candidate hits NotImplementedError with a
        diagnostic message — fail loud, not silent."""
        self._disconnected_entity(
            name='[Disconnected] foo',
            previous_integration_name='foo',
        )
        upstream_key = self._make_upstream_key('foo')

        class IncompleteSynchronizer(IntegrationSynchronizer):
            pass

        synchronizer = IncompleteSynchronizer()
        result = IntegrationSyncResult(title='Test')

        with self.assertRaises(NotImplementedError) as cm:
            synchronizer.reconnect_disconnected_items(
                integration_id=self.INTEGRATION_ID,
                integration_label=self.INTEGRATION_LABEL,
                integration_key_to_upstream={upstream_key: {'name': 'foo'}},
                integration_key_to_entity={},
                result=result,
            )
        self.assertIn('_rebuild_integration_components', str(cm.exception))


class IntegrationSynchronizerReconnectCycleTests(TestCase):
    """
    Issue #281 end-to-end cycle tests. Exercise the full
    sync → disconnect → re-add upstream → sync → reconnect cycle
    against a self-contained test synchronizer that mimics the real
    per-integration sync pattern (primary-match lookup, framework
    reconnect pre-pass, create-new for the remainder, disconnect
    for upstream-orphans). The shared synchronizer fixture means
    these tests are integration-agnostic — they exercise the
    framework path that all integrations now share.

    Phase 6 of #281's plan; the per-converter unit-level coverage
    lives in services/<integration>/tests/test_*.
    """

    INTEGRATION_ID = 'test_e2e'
    INTEGRATION_LABEL = 'Test E2E'

    def _make_upstream_key(self, integration_name):
        from hi.integrations.transient_models import IntegrationKey
        return IntegrationKey(
            integration_id=self.INTEGRATION_ID,
            integration_name=integration_name,
        )

    def _build_synchronizer(self):
        """Test-only synchronizer that drives a complete sync cycle
        against an in-memory upstream-key list. The
        ``_rebuild_integration_components`` override mirrors what a
        real integration converter does: set integration_key on the
        existing entity and save."""
        from hi.integrations.entity_operations import EntityIntegrationOperations
        from hi.integrations.transient_models import IntegrationKey

        integration_id = self.INTEGRATION_ID
        integration_label = self.INTEGRATION_LABEL

        class TestE2ESynchronizer(IntegrationSynchronizer):
            def _rebuild_integration_components(self, entity, upstream, result):
                entity.integration_key = IntegrationKey(
                    integration_id=integration_id,
                    integration_name=upstream['name'],
                )
                entity.save()

            def run_sync_cycle(self, upstream_keys, result):
                """Run one full sync pass: primary-match → framework
                reconnect pre-pass → create-new for the remainder →
                disconnect upstream-orphans. Mirrors the real
                per-integration sync structure."""
                upstream_map = {
                    IntegrationKey(integration_id=integration_id,
                                   integration_name=name): {'name': name}
                    for name in upstream_keys
                }
                existing_qs = Entity.objects.filter(integration_id=integration_id)
                integration_key_to_entity = {
                    e.integration_key: e for e in existing_qs
                    if e.integration_key is not None
                }

                self.reconnect_disconnected_items(
                    integration_id=integration_id,
                    integration_label=integration_label,
                    integration_key_to_upstream=upstream_map,
                    integration_key_to_entity=integration_key_to_entity,
                    result=result,
                )

                for upstream_key, payload in upstream_map.items():
                    if upstream_key in integration_key_to_entity:
                        continue
                    Entity.objects.create(
                        name=payload['name'],
                        entity_type_str='LIGHT',
                        integration_id=integration_id,
                        integration_name=upstream_key.integration_name,
                    )

                for upstream_key, entity in list(integration_key_to_entity.items()):
                    if upstream_key not in upstream_map:
                        EntityIntegrationOperations.preserve_with_user_data(
                            entity=entity,
                            integration_name=integration_id,
                            result=result,
                        )

        return TestE2ESynchronizer()

    def _user_attribute(self, entity, name='Custom Note', value='retain me'):
        """Anchor an entity for sync-time preservation by attaching
        user-created custom data."""
        EntityAttribute.objects.create(
            entity=entity,
            name=name,
            value=value,
            value_type_str='TEXT',
            attribute_type_str=str(AttributeType.CUSTOM),
        )

    def test_sync_disconnect_then_reconnect_does_not_create_duplicate(self):
        """The headline cycle: an entity is imported, drops from
        upstream (disconnect via sync-time preservation), reappears
        (reconnect via the secondary-match path). Total entity
        count returns to 1 — no duplicate is created."""
        synchronizer = self._build_synchronizer()
        result = IntegrationSyncResult(title='Cycle')

        # Pass 1: upstream introduces the entity.
        synchronizer.run_sync_cycle(['light.kitchen'], result)
        self.assertEqual(Entity.objects.count(), 1)
        original = Entity.objects.get(integration_name='light.kitchen')
        self._user_attribute(original)
        original_id = original.id

        # Pass 2: upstream drops the entity → preserved (disconnected).
        synchronizer.run_sync_cycle([], result)
        original.refresh_from_db()
        self.assertIsNone(original.integration_id)
        self.assertEqual(original.previous_integration_id, self.INTEGRATION_ID)
        self.assertEqual(original.previous_integration_name, 'light.kitchen')

        # Pass 3: upstream re-adds → reconnected (NOT duplicated).
        result_pass3 = IntegrationSyncResult(title='Cycle 3')
        synchronizer.run_sync_cycle(['light.kitchen'], result_pass3)
        self.assertEqual(Entity.objects.count(), 1)
        reconnected = Entity.objects.get(id=original_id)
        self.assertEqual(reconnected.integration_id, self.INTEGRATION_ID)
        self.assertIsNone(reconnected.previous_integration_id)
        self.assertTrue(any('Auto-reconnected' in note
                            for note in result_pass3.info_list))

    def test_disable_safe_then_resync_reconnects_preserved_entity(self):
        """Operator-initiated disable (SAFE mode) preserves entities
        with user data via the same code path as sync-time
        preservation, so reconnect must work for those too. Pinned
        in the corrected #281 issue's edge-cases section."""
        from hi.integrations.entity_operations import EntityIntegrationOperations

        synchronizer = self._build_synchronizer()
        result = IntegrationSyncResult(title='Disable Cycle')

        synchronizer.run_sync_cycle(['light.lounge'], result)
        entity = Entity.objects.get(integration_name='light.lounge')
        self._user_attribute(entity)
        entity_id = entity.id

        # Disable-SAFE: this is the exact call the integration_manager
        # makes for SAFE-mode disable on entities with user data.
        EntityIntegrationOperations.preserve_with_user_data(
            entity=entity,
            integration_name=self.INTEGRATION_ID,
            result=result,
        )
        entity.refresh_from_db()
        self.assertIsNone(entity.integration_id)
        self.assertEqual(entity.previous_integration_id, self.INTEGRATION_ID)

        # Re-Configure + sync re-imports the upstream item → reconnect.
        result_resync = IntegrationSyncResult(title='Resync')
        synchronizer.run_sync_cycle(['light.lounge'], result_resync)
        self.assertEqual(Entity.objects.count(), 1)
        reconnected = Entity.objects.get(id=entity_id)
        self.assertEqual(reconnected.integration_id, self.INTEGRATION_ID)
        self.assertIsNone(reconnected.previous_integration_id)

    def test_primary_match_shadows_secondary_so_no_false_reconnect(self):
        """A live entity matches the primary scan; an unrelated
        disconnected entity happens to share the previous_integration_name
        of an unrelated upstream key. The primary-match wins and the
        secondary scan only operates on the unmatched residual —
        the disconnected entity is NOT silently re-attached to the
        wrong upstream item."""
        synchronizer = self._build_synchronizer()
        result = IntegrationSyncResult(title='Shadow')

        # A primary-matched entity for 'light.bath'.
        Entity.objects.create(
            name='light.bath',
            entity_type_str='LIGHT',
            integration_id=self.INTEGRATION_ID,
            integration_name='light.bath',
        )
        # An unrelated disconnected entity whose previous identity
        # is for 'light.attic' — different upstream key entirely.
        Entity.objects.create(
            name='[Disconnected] light.attic',
            entity_type_str='LIGHT',
            previous_integration_id=self.INTEGRATION_ID,
            previous_integration_name='light.attic',
        )

        # Sync sees only 'light.bath' upstream — light.attic is NOT
        # in upstream, so no reconnect attempt for it.
        synchronizer.run_sync_cycle(['light.bath'], result)

        # The disconnected entity is unchanged: still disconnected,
        # not reconnected to light.bath.
        attic = Entity.objects.get(name__contains='attic')
        self.assertIsNone(attic.integration_id)
        self.assertEqual(attic.previous_integration_name, 'light.attic')

    def test_ambiguous_secondary_creates_fresh_entity_with_info_list_note(self):
        """Two disconnected entities share the same
        previous_integration_id + previous_integration_name. When
        upstream re-adds that key, the system has no basis to pick
        one — so it skips reconnect, creates a fresh entity, and
        leaves the duplicates for the user to resolve via merge."""
        synchronizer = self._build_synchronizer()

        Entity.objects.create(
            name='[Detached A] light.foo',
            entity_type_str='LIGHT',
            previous_integration_id=self.INTEGRATION_ID,
            previous_integration_name='light.foo',
        )
        Entity.objects.create(
            name='[Detached B] light.foo',
            entity_type_str='LIGHT',
            previous_integration_id=self.INTEGRATION_ID,
            previous_integration_name='light.foo',
        )

        result = IntegrationSyncResult(title='Ambiguous')
        synchronizer.run_sync_cycle(['light.foo'], result)

        # Three rows now: the two disconnected stragglers + a fresh entity.
        self.assertEqual(Entity.objects.count(), 3)
        # Fresh entity has the active integration_id; previous-identity NULL.
        fresh = Entity.objects.get(integration_id=self.INTEGRATION_ID)
        self.assertEqual(fresh.integration_name, 'light.foo')
        self.assertIsNone(fresh.previous_integration_id)
        # The two disconnected entities are unchanged.
        disconnected = Entity.objects.filter(
            previous_integration_id=self.INTEGRATION_ID,
        )
        self.assertEqual(disconnected.count(), 2)
        # Operator-visible breadcrumb in result.info_list.
        self.assertTrue(any('share that previous identity' in note
                            for note in result.info_list))

    def test_legacy_disconnected_entity_does_not_reconnect(self):
        """An entity disconnected before this feature landed has NO
        previous_integration_id (the column was NULL by default). It
        cannot be auto-reconnected — the system has no signal to use.
        Fresh entity is created instead; user resolves via merge.
        Pinned in the issue's 'Legacy disconnected entities' edge case."""
        synchronizer = self._build_synchronizer()
        result = IntegrationSyncResult(title='Legacy')

        Entity.objects.create(
            name='[Disconnected] light.cellar',
            entity_type_str='LIGHT',
            integration_id=None,
            integration_name=None,
            previous_integration_id=None,
            previous_integration_name=None,
        )

        synchronizer.run_sync_cycle(['light.cellar'], result)

        # Two rows: the legacy one (untouched) + a fresh import.
        self.assertEqual(Entity.objects.count(), 2)
        fresh = Entity.objects.get(integration_id=self.INTEGRATION_ID)
        self.assertEqual(fresh.integration_name, 'light.cellar')
        # Legacy entity is unchanged.
        legacy = Entity.objects.exclude(id=fresh.id).get()
        self.assertEqual(legacy.name, '[Disconnected] light.cellar')
        self.assertIsNone(legacy.integration_id)
        self.assertIsNone(legacy.previous_integration_id)
