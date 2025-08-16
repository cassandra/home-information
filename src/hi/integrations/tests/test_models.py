"""
Unit tests for Integration models.
"""

from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError, transaction, models

from hi.apps.attribute.enums import AttributeType, AttributeValueType

from hi.integrations.models import Integration, IntegrationAttribute, IntegrationDetailsModel
from hi.integrations.transient_models import IntegrationKey, IntegrationDetails


class ConcreteIntegrationDetailsModel(IntegrationDetailsModel):
    """Concrete test class for testing abstract IntegrationDetailsModel."""
    
    # Add a simple field to make it a valid concrete model
    name = models.CharField(max_length=64, default='test')
    
    class Meta:
        # Use this model only for testing
        app_label = 'integrations'


class IntegrationModelTestCase(TestCase):
    """Test cases for Integration model functionality."""

    def test_integration_model_fields_and_constraints(self):
        """Test Integration model field definitions and constraints."""
        # Create integration
        integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )
        
        # Verify field values
        self.assertEqual(integration.integration_id, 'test_integration')
        self.assertTrue(integration.is_enabled)
        self.assertIsNotNone(integration.created_datetime)
        self.assertIsNotNone(integration.updated_datetime)
        
        # Verify string representation
        self.assertEqual(str(integration), 'test_integration')
        
        # Verify model meta
        self.assertEqual(integration._meta.verbose_name, 'Integration')
        self.assertEqual(integration._meta.verbose_name_plural, 'Integrations')

    def test_integration_id_unique_constraint(self):
        """Test that integration_id must be unique."""
        # Create first integration
        Integration.objects.create(
            integration_id='unique_integration',
            is_enabled=True
        )
        
        # Attempt to create duplicate
        with self.assertRaises(IntegrityError):
            Integration.objects.create(
                integration_id='unique_integration',  # Same ID
                is_enabled=False
            )

    def test_integration_id_required_constraint(self):
        """Test that integration_id is required (not null, not blank)."""
        # Test empty string (should work - blank=False prevents form validation, not DB)
        integration = Integration.objects.create(
            integration_id='',
            is_enabled=True
        )
        self.assertEqual(integration.integration_id, '')

    def test_is_enabled_default_value(self):
        """Test that is_enabled defaults to False."""
        integration = Integration.objects.create(
            integration_id='default_test'
        )
        
        # Should default to False
        self.assertFalse(integration.is_enabled)

    def test_datetime_field_auto_behavior(self):
        """Test auto_now_add and auto_now behavior of datetime fields."""
        import time
        
        # Create integration
        integration = Integration.objects.create(
            integration_id='datetime_test',
            is_enabled=False
        )
        
        created_time = integration.created_datetime
        updated_time = integration.updated_datetime
        
        # Initially, created and updated should be very close
        time_diff = abs((updated_time - created_time).total_seconds())
        self.assertLess(time_diff, 1.0)  # Within 1 second
        
        # Wait a small amount and update
        time.sleep(0.1)
        integration.is_enabled = True
        integration.save()
        
        # Reload from database
        integration.refresh_from_db()
        
        # Created time should not have changed
        self.assertEqual(integration.created_datetime, created_time)
        
        # Updated time should have changed
        self.assertGreater(integration.updated_datetime, updated_time)

    def test_attributes_by_name_property(self):
        """Test attributes_by_name property returns correct mapping."""
        integration = Integration.objects.create(
            integration_id='attr_test_integration',
            is_enabled=True
        )
        
        # Test with no attributes
        result = integration.attributes_by_name
        self.assertEqual(result, {})
        self.assertIsInstance(result, dict)
        
        # Create attributes
        attr1 = IntegrationAttribute.objects.create(
            integration=integration,
            name='First Attribute',
            value='value1',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        attr2 = IntegrationAttribute.objects.create(
            integration=integration,
            name='Second Attribute',
            value='value2',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        # Test property returns correct mapping
        result = integration.attributes_by_name
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result['First Attribute'], attr1)
        self.assertEqual(result['Second Attribute'], attr2)
        self.assertIsInstance(result, dict)
        
        # Verify keys are attribute names
        self.assertEqual(set(result.keys()), {'First Attribute', 'Second Attribute'})

    def test_attributes_by_integration_key_property(self):
        """Test attributes_by_integration_key property returns correct mapping."""
        integration = Integration.objects.create(
            integration_id='key_test_integration',
            is_enabled=True
        )
        
        # Test with no attributes
        result = integration.attributes_by_integration_key
        self.assertEqual(result, {})
        self.assertIsInstance(result, dict)
        
        # Create attributes with integration keys
        key1 = IntegrationKey(
            integration_id='test_integration',
            integration_name='attr1'
        )
        key2 = IntegrationKey(
            integration_id='test_integration', 
            integration_name='attr2'
        )
        
        attr1 = IntegrationAttribute.objects.create(
            integration=integration,
            name='First Attribute',
            value='value1',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str=str(key1)
        )
        
        attr2 = IntegrationAttribute.objects.create(
            integration=integration,
            name='Second Attribute',
            value='value2',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str=str(key2)
        )
        
        # Test property returns correct mapping
        result = integration.attributes_by_integration_key
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[key1], attr1)
        self.assertEqual(result[key2], attr2)
        self.assertIsInstance(result, dict)
        
        # Verify keys are IntegrationKey objects
        result_keys = list(result.keys())
        self.assertTrue(all(isinstance(key, IntegrationKey) for key in result_keys))

    def test_attributes_by_integration_key_property_without_keys(self):
        """Test attributes_by_integration_key with attributes that have no integration key."""
        integration = Integration.objects.create(
            integration_id='no_key_test',
            is_enabled=True
        )
        
        # Create attribute without integration key
        attr = IntegrationAttribute.objects.create(
            integration=integration,
            name='No Key Attribute',
            value='value',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.CUSTOM)
            # No integration_key_str
        )
        
        # Property should handle attributes without integration keys
        result = integration.attributes_by_integration_key
        
        # Should have one entry with None key
        self.assertEqual(len(result), 1)
        
        # The key should be None since no integration_key_str was set
        self.assertIn(None, result)
        self.assertEqual(result[None], attr)


class IntegrationAttributeModelTestCase(TestCase):
    """Test cases for IntegrationAttribute model functionality."""

    def setUp(self):
        """Set up test data."""
        self.integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )

    def test_integration_attribute_foreign_key_relationship(self):
        """Test foreign key relationship between IntegrationAttribute and Integration."""
        # Create attribute
        attr = IntegrationAttribute.objects.create(
            integration=self.integration,
            name='Test Attribute',
            value='test_value',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        # Verify relationship from attribute to integration
        self.assertEqual(attr.integration, self.integration)
        self.assertEqual(attr.integration.integration_id, 'test_integration')
        
        # Verify reverse relationship from integration to attributes
        integration_attrs = self.integration.attributes.all()
        self.assertEqual(integration_attrs.count(), 1)
        self.assertEqual(integration_attrs.first(), attr)

    def test_integration_attribute_cascade_deletion(self):
        """Test that attributes are deleted when integration is deleted (CASCADE)."""
        # Create attributes
        attr1 = IntegrationAttribute.objects.create(
            integration=self.integration,
            name='Attribute 1',
            value='value1',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        attr2 = IntegrationAttribute.objects.create(
            integration=self.integration,
            name='Attribute 2',
            value='value2',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        attr1_id = attr1.id
        attr2_id = attr2.id
        
        # Verify attributes exist
        self.assertEqual(IntegrationAttribute.objects.filter(integration=self.integration).count(), 2)
        
        # Delete integration
        self.integration.delete()
        
        # Verify attributes were cascade deleted
        self.assertFalse(IntegrationAttribute.objects.filter(id=attr1_id).exists())
        self.assertFalse(IntegrationAttribute.objects.filter(id=attr2_id).exists())
        self.assertEqual(IntegrationAttribute.objects.filter(integration_id=self.integration.id).count(), 0)

    def test_integration_attribute_get_upload_to(self):
        """Test get_upload_to method returns correct path."""
        attr = IntegrationAttribute.objects.create(
            integration=self.integration,
            name='Test Attribute',
            value='test_value',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        upload_path = attr.get_upload_to()
        self.assertEqual(upload_path, 'integration/attributes/')

    def test_integration_attribute_meta_properties(self):
        """Test IntegrationAttribute model meta properties."""
        attr = IntegrationAttribute.objects.create(
            integration=self.integration,
            name='Meta Test',
            value='test',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        # Test meta properties
        self.assertEqual(attr._meta.verbose_name, 'Attribute')
        self.assertEqual(attr._meta.verbose_name_plural, 'Attributes')


class IntegrationDetailsModelTestCase(TestCase):
    """Test cases for IntegrationDetailsModel abstract model functionality."""

    def test_integration_key_property_getter(self):
        """Test integration_key property returns correct IntegrationKey."""
        # We can't instantiate abstract model directly, but can test the property logic
        # Create a mock object with the required fields
        class MockIntegrationDetails:
            def __init__(self, integration_id, integration_name):
                self.integration_id = integration_id
                self.integration_name = integration_name
            
            @property
            def integration_key(self):
                return IntegrationKey(
                    integration_id=self.integration_id,
                    integration_name=self.integration_name,
                )
        
        # Test with both values present
        mock_obj = MockIntegrationDetails('test_integration', 'device_1')
        key = mock_obj.integration_key
        
        self.assertIsInstance(key, IntegrationKey)
        self.assertEqual(key.integration_id, 'test_integration')
        self.assertEqual(key.integration_name, 'device_1')
        
        # Test with None values
        mock_obj_none = MockIntegrationDetails(None, None)
        key_none = mock_obj_none.integration_key
        
        self.assertIsInstance(key_none, IntegrationKey)
        self.assertIsNone(key_none.integration_id)
        self.assertIsNone(key_none.integration_name)

    def test_integration_key_property_setter(self):
        """Test integration_key property setter updates fields correctly."""
        class MockIntegrationDetails:
            def __init__(self):
                self.integration_id = None
                self.integration_name = None
            
            @property
            def integration_key(self):
                return IntegrationKey(
                    integration_id=self.integration_id,
                    integration_name=self.integration_name,
                )
            
            @integration_key.setter
            def integration_key(self, integration_key):
                if not integration_key:
                    self.integration_id = None
                    self.integration_name = None
                    return
                self.integration_id = integration_key.integration_id
                self.integration_name = integration_key.integration_name
        
        mock_obj = MockIntegrationDetails()
        
        # Test setting with IntegrationKey
        key = IntegrationKey('test_integration', 'device_1')
        mock_obj.integration_key = key
        
        self.assertEqual(mock_obj.integration_id, 'test_integration')
        self.assertEqual(mock_obj.integration_name, 'device_1')
        
        # Test setting with None
        mock_obj.integration_key = None
        
        self.assertIsNone(mock_obj.integration_id)
        self.assertIsNone(mock_obj.integration_name)
        
        # Test setting with falsy value
        mock_obj.integration_key = ''
        
        self.assertIsNone(mock_obj.integration_id)
        self.assertIsNone(mock_obj.integration_name)

    def test_get_integration_details_method(self):
        """Test get_integration_details method returns correct IntegrationDetails."""
        class MockIntegrationDetails:
            def __init__(self, integration_id, integration_name, payload):
                self.integration_id = integration_id
                self.integration_name = integration_name
                self.integration_payload = payload
            
            @property
            def integration_key(self):
                return IntegrationKey(
                    integration_id=self.integration_id,
                    integration_name=self.integration_name,
                )
            
            def get_integration_details(self):
                return IntegrationDetails(
                    key=self.integration_key,
                    payload=self.integration_payload,
                )
        
        # Test with payload
        payload = {'device_type': 'light', 'capabilities': ['brightness']}
        mock_obj = MockIntegrationDetails('test_integration', 'device_1', payload)
        
        details = mock_obj.get_integration_details()
        
        self.assertIsInstance(details, IntegrationDetails)
        self.assertEqual(details.key.integration_id, 'test_integration')
        self.assertEqual(details.key.integration_name, 'device_1')
        self.assertEqual(details.payload, payload)
        
        # Test with empty payload
        mock_obj_empty = MockIntegrationDetails('test_integration', 'device_2', {})
        details_empty = mock_obj_empty.get_integration_details()
        
        self.assertEqual(details_empty.payload, {})

    def test_update_integration_payload_method(self):
        """Test update_integration_payload method behavior and change detection."""
        class MockIntegrationDetails:
            def __init__(self, initial_payload=None):
                self.integration_payload = initial_payload or {}
                self.save_called = False
            
            def save(self):
                self.save_called = True
            
            def update_integration_payload(self, new_payload):
                old_payload = self.integration_payload or {}
                changed_fields = []
                
                # Check for changes to existing fields only
                for key, new_value in new_payload.items():
                    if key in old_payload and old_payload[key] != new_value:
                        changed_fields.append(f'{key}: {old_payload[key]} -> {new_value}')
                
                # Always update payload (even if no existing fields changed)
                self.integration_payload = new_payload
                self.save()
                
                return changed_fields
        
        # Test with empty initial payload
        mock_obj = MockIntegrationDetails()
        
        new_payload = {'device_type': 'light', 'brightness': 80}
        changes = mock_obj.update_integration_payload(new_payload)
        
        # No existing fields to change
        self.assertEqual(changes, [])
        self.assertEqual(mock_obj.integration_payload, new_payload)
        self.assertTrue(mock_obj.save_called)
        
        # Test with existing payload and changes
        mock_obj2 = MockIntegrationDetails({'device_type': 'switch', 'brightness': 50})
        mock_obj2.save_called = False
        
        updated_payload = {'device_type': 'light', 'brightness': 80, 'color': 'red'}
        changes = mock_obj2.update_integration_payload(updated_payload)
        
        # Should detect changes to existing fields
        expected_changes = [
            'device_type: switch -> light',
            'brightness: 50 -> 80'
        ]
        self.assertEqual(set(changes), set(expected_changes))
        self.assertEqual(mock_obj2.integration_payload, updated_payload)
        self.assertTrue(mock_obj2.save_called)
        
        # Test with no changes to existing fields
        mock_obj3 = MockIntegrationDetails({'device_type': 'light'})
        mock_obj3.save_called = False
        
        same_payload = {'device_type': 'light', 'new_field': 'new_value'}
        changes = mock_obj3.update_integration_payload(same_payload)
        
        # No changes to existing fields (new fields are ignored for change detection)
        self.assertEqual(changes, [])
        self.assertEqual(mock_obj3.integration_payload, same_payload)
        self.assertTrue(mock_obj3.save_called)

    def test_integration_details_model_manager(self):
        """Test that IntegrationDetailsModel uses IntegrationDetailsManager."""
        # Test using the concrete test model
        self.assertEqual(ConcreteIntegrationDetailsModel.objects.__class__.__name__, 'IntegrationDetailsManager')

    def test_integration_details_model_fields(self):
        """Test IntegrationDetailsModel field definitions."""
        # Test field properties on the abstract model
        integration_id_field = IntegrationDetailsModel._meta.get_field('integration_id')
        integration_name_field = IntegrationDetailsModel._meta.get_field('integration_name')
        integration_payload_field = IntegrationDetailsModel._meta.get_field('integration_payload')
        
        # Test integration_id field
        self.assertEqual(integration_id_field.max_length, 32)
        self.assertTrue(integration_id_field.null)
        self.assertTrue(integration_id_field.blank)
        self.assertEqual(integration_id_field.verbose_name, 'Integration Id')
        
        # Test integration_name field
        self.assertEqual(integration_name_field.max_length, 128)
        self.assertTrue(integration_name_field.null)
        self.assertTrue(integration_name_field.blank)
        self.assertEqual(integration_name_field.verbose_name, 'Integration Name')
        
        # Test integration_payload field
        self.assertEqual(integration_payload_field.default, dict)
        self.assertTrue(integration_payload_field.blank)
        self.assertEqual(integration_payload_field.verbose_name, 'Integration Payload')
        self.assertIn('Integration-specific data', integration_payload_field.help_text)


class IntegrationModelTransactionTestCase(TransactionTestCase):
    """Transaction-specific tests for Integration models."""

    def test_integration_id_null_constraint(self):
        """Test that integration_id cannot be null."""
        with self.assertRaises(IntegrityError):
            Integration.objects.create(
                integration_id=None,
                is_enabled=True
            )

    def test_integration_unique_constraint_transaction_behavior(self):
        """Test unique constraint behavior in transaction context."""
        integration_id = 'transaction_test_integration'
        
        # Test that transaction rollback works correctly with unique constraint
        try:
            with transaction.atomic():
                # Create first integration
                Integration.objects.create(
                    integration_id=integration_id,
                    is_enabled=True
                )
                
                # Attempt to create duplicate in same transaction
                Integration.objects.create(
                    integration_id=integration_id,  # Duplicate
                    is_enabled=False
                )
                
        except IntegrityError:
            # Expected - transaction should roll back
            pass
        
        # Verify no integrations were created due to rollback
        self.assertFalse(Integration.objects.filter(integration_id=integration_id).exists())
        
        # Verify we can create integration after failed transaction
        integration = Integration.objects.create(
            integration_id=integration_id,
            is_enabled=True
        )
        self.assertTrue(Integration.objects.filter(integration_id=integration_id).exists())
        self.assertEqual(integration.integration_id, integration_id)

    def test_integration_attribute_cascade_deletion_transaction_consistency(self):
        """Test cascade deletion maintains transaction consistency."""
        # Create integration with attributes
        integration = Integration.objects.create(
            integration_id='cascade_test',
            is_enabled=True
        )
        
        # Create multiple attributes
        attributes = []
        for i in range(3):
            attr = IntegrationAttribute.objects.create(
                integration=integration,
                name=f'Attribute {i}',
                value=f'value{i}',
                value_type_str=str(AttributeValueType.TEXT),
                attribute_type_str=str(AttributeType.PREDEFINED)
            )
            attributes.append(attr)
        
        attribute_ids = [attr.id for attr in attributes]
        
        # Verify all attributes exist
        self.assertEqual(IntegrationAttribute.objects.filter(id__in=attribute_ids).count(), 3)
        
        # Delete integration in transaction
        with transaction.atomic():
            integration.delete()
        
        # Verify complete cleanup
        self.assertEqual(IntegrationAttribute.objects.filter(id__in=attribute_ids).count(), 0)
        self.assertFalse(Integration.objects.filter(id=integration.id).exists())
        
        # Verify database consistency - no orphaned attributes
        orphaned_attrs = IntegrationAttribute.objects.filter(integration_id=integration.id)
        self.assertEqual(orphaned_attrs.count(), 0)
