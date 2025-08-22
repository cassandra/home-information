import logging

from hi.apps.entity.models import Entity, EntityAttribute, EntityAttributeHistory
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class EntityAttributeHistoryTestCase(BaseTestCase):
    """Tests for EntityAttribute history tracking functionality."""

    def test_attribute_history_creation_on_value_change(self):
        """Test that history records are created when attribute values change - core business logic."""
        # Create entity and attribute
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='GENERAL',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        
        attr = EntityAttribute.objects.create(
            entity=entity,
            name='test_attr',
            value='initial_value',
            value_type_str='TEXT',
            attribute_type_str='CUSTOM'
        )
        
        # Verify initial history record was created
        initial_history_count = EntityAttributeHistory.objects.filter(attribute=attr).count()
        self.assertEqual(initial_history_count, 1)
        
        # Update the attribute value
        attr.value = 'updated_value'
        attr.save()
        
        # Verify new history record was created
        updated_history_count = EntityAttributeHistory.objects.filter(attribute=attr).count()
        self.assertEqual(updated_history_count, 2)
        
        # Verify the latest history record contains the new value
        latest_history = EntityAttributeHistory.objects.filter(attribute=attr).order_by('-changed_datetime').first()
        self.assertEqual(latest_history.value, 'updated_value')
        return

    def test_attribute_history_skipped_for_file_attributes(self):
        """Test that file attributes do not create history records - important exclusion logic."""
        # Create entity
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='GENERAL',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        
        # Create file attribute
        attr = EntityAttribute.objects.create(
            entity=entity,
            name='test_file_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        
        # Verify no history records were created for file attribute
        history_count = EntityAttributeHistory.objects.filter(attribute=attr).count()
        self.assertEqual(history_count, 0)
        return

    def test_attribute_history_disabled_with_track_history_false(self):
        """Test that history tracking can be disabled via save parameter - control mechanism."""
        # Create entity and attribute with history tracking disabled
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='GENERAL',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        
        attr = EntityAttribute(
            entity=entity,
            name='test_attr',
            value='initial_value',
            value_type_str='TEXT',
            attribute_type_str='CUSTOM'
        )
        attr.save(track_history=False)  # Disable history tracking
        
        # Verify no history record was created
        history_count = EntityAttributeHistory.objects.filter(attribute=attr).count()
        self.assertEqual(history_count, 0)
        return

    def test_attribute_get_history_model_class_mapping(self):
        """Test _get_history_model_class returns correct model class - critical mapping logic."""
        # Test EntityAttribute mapping
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='GENERAL',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        entity_attr = EntityAttribute(
            entity=entity,
            name='entity_attr',
            value_type_str='TEXT',
            attribute_type_str='CUSTOM'
        )
        self.assertEqual(entity_attr._get_history_model_class(), EntityAttributeHistory)
        return

    def test_attribute_history_cascade_deletion(self):
        """Test that history records are deleted when attribute is deleted - database constraint behavior."""
        # Create entity and attribute with history
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='GENERAL',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        
        attr = EntityAttribute.objects.create(
            entity=entity,
            name='test_attr',
            value='test_value',
            value_type_str='TEXT',
            attribute_type_str='CUSTOM'
        )
        
        # Update to create multiple history records
        attr.value = 'updated_value'
        attr.save()
        
        # Verify history records exist
        history_count = EntityAttributeHistory.objects.filter(attribute=attr).count()
        self.assertEqual(history_count, 2)
        
        # Delete the attribute
        attr.delete()
        
        # Verify all history records are deleted (cascade)
        history_count = EntityAttributeHistory.objects.filter(attribute=attr).count()
        self.assertEqual(history_count, 0)
        return

    def test_multiple_attribute_updates_create_sequential_history(self):
        """Test that multiple updates create proper history sequence - workflow verification."""
        # Create entity and attribute
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='GENERAL',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        
        attribute = EntityAttribute.objects.create(
            entity=entity,
            name='sequential_test',
            value='value_1',
            value_type_str='TEXT',
            attribute_type_str='CUSTOM'
        )
        
        # Perform multiple updates
        for i in range(2, 6):  # values 2, 3, 4, 5
            attribute.value = f'value_{i}'
            attribute.save()
        
        # Verify all history records exist
        history_records = EntityAttributeHistory.objects.filter(attribute=attribute).order_by('-changed_datetime')
        self.assertEqual(history_records.count(), 5)  # Initial + 4 updates
        
        # Verify values are in correct order (newest first)
        expected_values = ['value_5', 'value_4', 'value_3', 'value_2', 'value_1']
        actual_values = [record.value for record in history_records]
        self.assertEqual(actual_values, expected_values)
        return

    def test_boolean_attribute_history(self):
        """Test boolean attribute value changes create proper history - data type verification."""
        # Create entity and boolean attribute
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='GENERAL',
            integration_id='test.entity',
            integration_name='test_integration'
        )
        
        attribute = EntityAttribute.objects.create(
            entity=entity,
            name='boolean_test',
            value='True',
            value_type_str='BOOLEAN',
            attribute_type_str='CUSTOM'
        )
        
        # Update boolean value
        attribute.value = 'False'
        attribute.save()
        
        # Verify history captures the boolean change
        history_records = EntityAttributeHistory.objects.filter(attribute=attribute).order_by('-changed_datetime')
        self.assertEqual(history_records.count(), 2)
        self.assertEqual(history_records[0].value, 'False')  # Latest
        self.assertEqual(history_records[1].value, 'True')   # Original
        return
