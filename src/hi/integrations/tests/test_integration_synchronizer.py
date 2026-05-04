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
        
        # Preservation records the original name in removed_list
        # (captured before the rename) and surfaces a diagnostic
        # info note — the operator wants to know an entity was
        # disconnected and renamed, not just see a name in a list.
        self.assertEqual(self.result.removed_list, [original_name])
        self.assertEqual(len(self.result.info_list), 1)
        message = self.result.info_list[0]
        self.assertIn('Preserved TestIntegration item', message)
        self.assertIn('disconnected from integration', message)
        self.assertIn(original_name, message)
        self.assertIn('[Disconnected]', message)
        
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
            attribute_type_str=str(AttributeType.CUSTOM)
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
        self.assertTrue(self.entity.name.startswith('[Disconnected]'))
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
        
        # Preservation diagnostic surfaces in info_list; the
        # original (pre-rename) name is captured in removed_list.
        self.assertEqual(len(self.result.info_list), 1)
        message = self.result.info_list[0]
        self.assertIn('Preserved TestIntegration item', message)
        self.assertIn('disconnected from integration', message)
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
        self.assertTrue(self.entity.name.startswith('[Disconnected]'))
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
        self.assertTrue(mixed_entity.name.startswith('[Disconnected]'))
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
        self.assertTrue(self.entity.name.startswith('[Disconnected]'))
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

    def test_complex_disconnection_name_handling(self):
        """Test various edge cases in disconnection name handling."""
        test_cases = [
            {
                'name': 'Simple Entity Name',
                'expected': '[Disconnected] Simple Entity Name'
            },
            {
                'name': '[Already Disconnected] Entity',
                'expected': '[Disconnected] [Already Disconnected] Entity'  # Should not duplicate if different format
            },
            {
                'name': '[Disconnected] Already Prefixed',
                'expected': '[Disconnected] Already Prefixed'  # Should not duplicate exact match
            },
            {
                'name': '   Whitespace Padded   ',
                'expected': '[Disconnected]    Whitespace Padded   '  # Should preserve exact spacing
            },
            {
                'name': '',
                'expected': '[Disconnected] '  # Should handle empty name
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            with self.subTest(test_case=test_case):
                # Create entity for this test
                entity = Entity.objects.create(
                    name=test_case['name'],
                    entity_type_str='LIGHT',
                    integration_id='test_integration',
                    integration_name=f'device_{i}'
                )
                
                # Add user data to trigger preservation
                EntityAttribute.objects.create(
                    entity=entity,
                    name='User Data',
                    value='User value',
                    value_type_str='TEXT',
                    attribute_type_str=str(AttributeType.CUSTOM)
                )
                
                # Create fresh result for each test
                test_result = IntegrationSyncResult(title='Test Result')
                
                # Execute preservation
                self.synchronizer._remove_entity_intelligently(
                    entity, test_result, 'TestIntegration'
                )
                
                # Verify name transformation
                entity.refresh_from_db()
                self.assertEqual(entity.name, test_case['expected'])
                
                # Verify disconnection
                self.assertIsNone(entity.integration_id)
                self.assertIsNone(entity.integration_name)
                
                # Preservation note surfaces in info_list.
                self.assertEqual(len(test_result.info_list), 1)
                self.assertIn('Preserved TestIntegration item', test_result.info_list[0])



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
        # Area persists with operator-added data.
        self.assertTrue(Entity.objects.filter(id=area_id).exists())
        self.area.refresh_from_db()
        self.assertTrue(self.area.name.startswith('[Disconnected]'))

    def test_orphan_delegate_deleted_when_only_principal_has_user_data(self):
        """Camera carries user data so it is preserved (kept as
        [Disconnected]); Area carries none. Even though the
        principal survives in name, the Area is correctly hard-
        deleted — see the rationale documented on
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

        # Camera kept with [Disconnected] rename (user data).
        self.assertTrue(Entity.objects.filter(id=camera_id).exists())
        self.camera.refresh_from_db()
        self.assertTrue(self.camera.name.startswith('[Disconnected]'))
        # Area is gone — its display purpose is negated once the
        # principal's integration-derived state is removed.
        self.assertFalse(Entity.objects.filter(id=area_id).exists())
