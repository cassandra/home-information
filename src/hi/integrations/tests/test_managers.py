"""
Unit tests for IntegrationDetailsManager.
"""

from django.test import TransactionTestCase
from django.db import models, connection

from hi.integrations.managers import IntegrationDetailsManager
from hi.integrations.models import IntegrationDetailsModel
from hi.integrations.transient_models import IntegrationKey


class ManagerTestModel(IntegrationDetailsModel):
    """Concrete test model for testing IntegrationDetailsManager."""
    
    name = models.CharField(max_length=64, default='test')
    
    class Meta:
        app_label = 'integrations'


class IntegrationDetailsManagerTestCase(TransactionTestCase):
    """Test cases for IntegrationDetailsManager functionality."""

    def setUp(self):
        """Set up test data by creating table and test instances."""
        # Create table manually for test model
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(ManagerTestModel)
            
        # Create test instances with different integration keys
        self.model1 = ManagerTestModel.objects.create(
            name='Test Model 1',
            integration_id='home_assistant',
            integration_name='light_bedroom'
        )
        
        self.model2 = ManagerTestModel.objects.create(
            name='Test Model 2',
            integration_id='home_assistant',
            integration_name='switch_kitchen'
        )
        
        self.model3 = ManagerTestModel.objects.create(
            name='Test Model 3',
            integration_id='zoneminder',
            integration_name='camera_front_door'
        )
        
        self.model4 = ManagerTestModel.objects.create(
            name='Test Model 4',
            integration_id='zoneminder',
            integration_name='camera_back_yard'
        )
        
        # Create model without integration (user-created)
        self.model_no_integration = ManagerTestModel.objects.create(
            name='User Created Model',
            integration_id=None,
            integration_name=None
        )
    
    def tearDown(self):
        """Clean up test table."""
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(ManagerTestModel)

    def test_filter_by_integration_key_exact_match(self):
        """Test filter_by_integration_key with exact key matches."""
        # Test home_assistant light
        ha_light_key = IntegrationKey('home_assistant', 'light_bedroom')
        result = ManagerTestModel.objects.filter_by_integration_key(ha_light_key)
        
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.model1)
        self.assertEqual(result.first().name, 'Test Model 1')
        
        # Test zoneminder camera
        zm_camera_key = IntegrationKey('zoneminder', 'camera_front_door')
        result = ManagerTestModel.objects.filter_by_integration_key(zm_camera_key)
        
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.model3)
        self.assertEqual(result.first().name, 'Test Model 3')

    def test_filter_by_integration_key_no_matches(self):
        """Test filter_by_integration_key with no matching results."""
        # Test non-existent integration
        nonexistent_key = IntegrationKey('nonexistent_integration', 'device_name')
        result = ManagerTestModel.objects.filter_by_integration_key(nonexistent_key)
        
        self.assertEqual(result.count(), 0)
        
        # Test existing integration with non-existent device
        partial_key = IntegrationKey('home_assistant', 'nonexistent_device')
        result = ManagerTestModel.objects.filter_by_integration_key(partial_key)
        
        self.assertEqual(result.count(), 0)

    def test_filter_by_integration_key_case_sensitivity(self):
        """Test filter_by_integration_key case sensitivity behavior."""
        # Create key with different case
        # Note: IntegrationKey lowercases values in __post_init__, so this tests the database query
        different_case_key = IntegrationKey('HOME_ASSISTANT', 'LIGHT_BEDROOM')
        
        # Should match because IntegrationKey normalizes to lowercase
        result = ManagerTestModel.objects.filter_by_integration_key(different_case_key)
        
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.model1)

    def test_filter_by_integration_key_with_none_values(self):
        """Test filter_by_integration_key with None integration values."""
        # Create key with None values
        none_key = IntegrationKey(None, None)
        result = ManagerTestModel.objects.filter_by_integration_key(none_key)
        
        # Should match the model without integration
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.model_no_integration)

    def test_filter_by_integration_keys_multiple_keys(self):
        """Test filter_by_integration_keys with multiple keys."""
        # Create multiple keys
        key1 = IntegrationKey('home_assistant', 'light_bedroom')
        key2 = IntegrationKey('zoneminder', 'camera_front_door')
        key3 = IntegrationKey('nonexistent', 'device')  # This won't match anything
        
        keys = [key1, key2, key3]
        result = ManagerTestModel.objects.filter_by_integration_keys(keys)
        
        # Should match model1 and model3
        self.assertEqual(result.count(), 2)
        result_names = {model.name for model in result}
        self.assertEqual(result_names, {'Test Model 1', 'Test Model 3'})

    def test_filter_by_integration_keys_empty_list(self):
        """Test filter_by_integration_keys with empty key list."""
        result = ManagerTestModel.objects.filter_by_integration_keys([])
        
        # Empty list should return no results
        self.assertEqual(result.count(), 0)

    def test_filter_by_integration_keys_single_key(self):
        """Test filter_by_integration_keys with single key (equivalent to filter_by_integration_key)."""
        key = IntegrationKey('home_assistant', 'switch_kitchen')
        result = ManagerTestModel.objects.filter_by_integration_keys([key])
        
        # Should match model2
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.model2)
        self.assertEqual(result.first().name, 'Test Model 2')

    def test_filter_by_integration_keys_duplicate_keys(self):
        """Test filter_by_integration_keys with duplicate keys."""
        key = IntegrationKey('home_assistant', 'light_bedroom')
        duplicate_keys = [key, key, key]  # Same key multiple times
        
        result = ManagerTestModel.objects.filter_by_integration_keys(duplicate_keys)
        
        # Should still return only one result (no duplicates)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.model1)

    def test_filter_by_integration_keys_all_same_integration(self):
        """Test filter_by_integration_keys with multiple devices from same integration."""
        key1 = IntegrationKey('home_assistant', 'light_bedroom')
        key2 = IntegrationKey('home_assistant', 'switch_kitchen')
        
        result = ManagerTestModel.objects.filter_by_integration_keys([key1, key2])
        
        # Should match both home_assistant models
        self.assertEqual(result.count(), 2)
        result_names = {model.name for model in result}
        self.assertEqual(result_names, {'Test Model 1', 'Test Model 2'})

    def test_filter_by_integration_keys_mixed_integrations(self):
        """Test filter_by_integration_keys with keys from different integrations."""
        ha_key = IntegrationKey('home_assistant', 'light_bedroom')
        zm_key1 = IntegrationKey('zoneminder', 'camera_front_door')
        zm_key2 = IntegrationKey('zoneminder', 'camera_back_yard')
        
        result = ManagerTestModel.objects.filter_by_integration_keys([ha_key, zm_key1, zm_key2])
        
        # Should match model1, model3, and model4
        self.assertEqual(result.count(), 3)
        result_names = {model.name for model in result}
        self.assertEqual(result_names, {'Test Model 1', 'Test Model 3', 'Test Model 4'})

    def test_manager_query_chaining(self):
        """Test that manager methods can be chained with other queryset operations."""
        # Test chaining with additional filters
        key = IntegrationKey('home_assistant', 'light_bedroom')
        result = ManagerTestModel.objects.filter_by_integration_key(key).filter(name__contains='Model 1')
        
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.model1)
        
        # Test chaining with exclude
        keys = [
            IntegrationKey('home_assistant', 'light_bedroom'),
            IntegrationKey('home_assistant', 'switch_kitchen')
        ]
        result = ManagerTestModel.objects.filter_by_integration_keys(keys).exclude(name__contains='Test Model 1')
        
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), self.model2)

    def test_manager_query_ordering(self):
        """Test that manager methods work with ordering."""
        keys = [
            IntegrationKey('zoneminder', 'camera_front_door'),
            IntegrationKey('zoneminder', 'camera_back_yard')
        ]
        
        # Test ordering by name
        result_asc = ManagerTestModel.objects.filter_by_integration_keys(keys).order_by('name')
        result_desc = ManagerTestModel.objects.filter_by_integration_keys(keys).order_by('-name')
        
        self.assertEqual(result_asc.count(), 2)
        self.assertEqual(result_desc.count(), 2)
        
        # Verify ordering
        asc_names = [model.name for model in result_asc]
        desc_names = [model.name for model in result_desc]
        
        self.assertEqual(asc_names, ['Test Model 3', 'Test Model 4'])
        self.assertEqual(desc_names, ['Test Model 4', 'Test Model 3'])

    def test_manager_integration_key_query_performance(self):
        """Test that manager methods generate efficient queries."""
        # This test verifies that the manager methods use proper query structure
        
        key = IntegrationKey('home_assistant', 'light_bedroom')
        queryset = ManagerTestModel.objects.filter_by_integration_key(key)
        
        # Verify the queryset generates correct SQL (basic check)
        sql = str(queryset.query)
        
        # Should use AND to combine integration_id and integration_name filters
        self.assertIn('integration_id', sql)
        self.assertIn('integration_name', sql)
        self.assertIn('AND', sql.upper())

    def test_manager_multiple_keys_query_structure(self):
        """Test that filter_by_integration_keys generates correct OR query structure."""
        keys = [
            IntegrationKey('home_assistant', 'light_bedroom'),
            IntegrationKey('zoneminder', 'camera_front_door')
        ]
        
        queryset = ManagerTestModel.objects.filter_by_integration_keys(keys)
        sql = str(queryset.query)
        
        # Should use OR to combine different integration key filters
        self.assertIn('OR', sql.upper())
        self.assertIn('integration_id', sql)
        self.assertIn('integration_name', sql)

    def test_manager_with_values_and_annotations(self):
        """Test that manager methods work with values() and annotations."""
        keys = [
            IntegrationKey('home_assistant', 'light_bedroom'),
            IntegrationKey('home_assistant', 'switch_kitchen')
        ]
        
        # Test with values()
        result = ManagerTestModel.objects.filter_by_integration_keys(keys).values('name', 'integration_id')
        
        self.assertEqual(len(result), 2)
        names = {item['name'] for item in result}
        self.assertEqual(names, {'Test Model 1', 'Test Model 2'})
        
        # Verify all have same integration_id
        integration_ids = {item['integration_id'] for item in result}
        self.assertEqual(integration_ids, {'home_assistant'})

    def test_manager_with_complex_filter_combinations(self):
        """Test manager methods with complex filter combinations."""
        # Create additional test data
        ManagerTestModel.objects.create(
            name='Extra Model',
            integration_id='home_assistant',
            integration_name='light_bedroom'  # Same key as model1
        )
        
        key = IntegrationKey('home_assistant', 'light_bedroom')
        
        # Test that multiple objects with same integration key are returned
        result = ManagerTestModel.objects.filter_by_integration_key(key)
        
        self.assertEqual(result.count(), 2)  # model1 and extra_model
        result_names = {model.name for model in result}
        self.assertEqual(result_names, {'Test Model 1', 'Extra Model'})
        
        # Test filtering further
        filtered_result = ManagerTestModel.objects.filter_by_integration_key(key).filter(name__contains='Extra')
        
        self.assertEqual(filtered_result.count(), 1)
        self.assertEqual(filtered_result.first().name, 'Extra Model')

    def test_manager_inheritance_and_usage(self):
        """Test that IntegrationDetailsManager is properly inherited and used."""
        # Verify that ManagerTestModel uses IntegrationDetailsManager
        self.assertIsInstance(ManagerTestModel.objects, IntegrationDetailsManager)
        
        # Verify that manager methods exist and are callable
        self.assertTrue(hasattr(ManagerTestModel.objects, 'filter_by_integration_key'))
        self.assertTrue(hasattr(ManagerTestModel.objects, 'filter_by_integration_keys'))
        
        # Verify methods are callable
        self.assertTrue(callable(ManagerTestModel.objects.filter_by_integration_key))
        self.assertTrue(callable(ManagerTestModel.objects.filter_by_integration_keys))

    def test_manager_with_special_characters_in_keys(self):
        """Test manager methods with special characters in integration keys."""
        # Create model with special characters
        special_model = ManagerTestModel.objects.create(
            name='Special Model',
            integration_id='integration-with-dashes',
            integration_name='device_with_underscores-and-dashes'
        )
        
        # Test filtering with special character key
        special_key = IntegrationKey('integration-with-dashes', 'device_with_underscores-and-dashes')
        result = ManagerTestModel.objects.filter_by_integration_key(special_key)
        
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), special_model)
        self.assertEqual(result.first().name, 'Special Model')

    def test_manager_queryset_methods_return_types(self):
        """Test that manager methods return correct QuerySet types."""
        key = IntegrationKey('home_assistant', 'light_bedroom')
        keys = [key]
        
        # Test return types
        single_result = ManagerTestModel.objects.filter_by_integration_key(key)
        multiple_result = ManagerTestModel.objects.filter_by_integration_keys(keys)
        
        # Both should return QuerySet instances
        self.assertEqual(type(single_result).__name__, 'QuerySet')
        self.assertEqual(type(multiple_result).__name__, 'QuerySet')
        
        # Should be able to evaluate to lists
        single_list = list(single_result)
        multiple_list = list(multiple_result)
        
        self.assertIsInstance(single_list, list)
        self.assertIsInstance(multiple_list, list)
        self.assertEqual(len(single_list), 1)
        self.assertEqual(len(multiple_list), 1)
