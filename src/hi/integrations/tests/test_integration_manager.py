"""
Unit tests for IntegrationManager.
"""

import asyncio
import threading
from unittest.mock import Mock, AsyncMock, patch
from django.test import TestCase

from hi.apps.attribute.enums import AttributeType, AttributeValueType

from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationMetaData, IntegrationKey
from hi.integrations.enums import IntegrationAttributeType


class MockIntegrationAttributeType(IntegrationAttributeType):
    """Mock integration attribute type for testing."""
    
    TEST_ATTR = ('Test Attribute', 'Test description', AttributeValueType.TEXT, {}, True, True, 'default')


class MockIntegrationGateway(IntegrationGateway):
    """Mock integration gateway for testing."""
    
    def __init__(self, integration_id='test_integration', label='Test Integration'):
        self.integration_id = integration_id
        self.label = label
    
    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label=self.label,
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
    
    def get_manage_view_pane(self):
        return Mock()
    
    def get_monitor(self):
        return Mock()
    
    def get_controller(self):
        return Mock()


class IntegrationManagerTestCase(TestCase):
    """Test cases for IntegrationManager singleton behavior and core functionality."""

    def setUp(self):
        """Set up test data."""
        # Clear any existing singleton instance for clean tests
        IntegrationManager._instances = {}
        IntegrationManager._initialized_instance = None
        
    def test_singleton_pattern_behavior(self):
        """Test that IntegrationManager implements singleton pattern correctly."""
        manager1 = IntegrationManager()
        manager2 = IntegrationManager()
        
        # Verify same instance returned
        self.assertIs(manager1, manager2)
        
        # Verify singleton state is shared
        manager1._test_attribute = 'test_value'
        self.assertEqual(manager2._test_attribute, 'test_value')
        
        # Verify initialization state (should be False for new instances in test)
        # Note: _initialized may be True if singleton was used elsewhere
        # The key test is that both managers are the same instance
        self.assertEqual(manager1._initialized, manager2._initialized)

    def test_singleton_thread_safety(self):
        """Test that singleton creation is thread-safe."""
        managers = []
        results = []
        
        def create_manager():
            try:
                manager = IntegrationManager()
                managers.append(manager)
                results.append('success')
            except Exception as e:
                results.append(f'error: {e}')
        
        # Create multiple threads that create manager instances
        threads = [threading.Thread(target=create_manager) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all threads succeeded
        self.assertEqual(len(results), 10)
        self.assertTrue(all(result == 'success' for result in results))
        
        # Verify all managers are the same instance
        self.assertEqual(len(set(id(manager) for manager in managers)), 1)
        self.assertTrue(all(manager is managers[0] for manager in managers))

    def test_integration_data_list_sorting_and_filtering(self):
        """Test get_integration_data_list with sorting and enabled filtering."""
        manager = IntegrationManager()
        
        # Create mock integration data with different labels and enabled states
        integration1 = Integration.objects.create(
            integration_id='zebra_integration',
            is_enabled=True
        )
        integration2 = Integration.objects.create(
            integration_id='alpha_integration', 
            is_enabled=False
        )
        integration3 = Integration.objects.create(
            integration_id='beta_integration',
            is_enabled=True
        )
        
        data1 = IntegrationData(
            integration_gateway=MockIntegrationGateway('zebra_integration', 'Zebra Service'),
            integration=integration1
        )
        data2 = IntegrationData(
            integration_gateway=MockIntegrationGateway('alpha_integration', 'Alpha Service'),
            integration=integration2
        )
        data3 = IntegrationData(
            integration_gateway=MockIntegrationGateway('beta_integration', 'Beta Service'),
            integration=integration3
        )
        
        manager._integration_data_map = {
            'zebra_integration': data1,
            'alpha_integration': data2,
            'beta_integration': data3
        }
        
        # Test all integrations - should be sorted by label
        all_integrations = manager.get_integration_data_list(enabled_only=False)
        self.assertEqual(len(all_integrations), 3)
        self.assertEqual([data.integration_id for data in all_integrations],
                         ['alpha_integration', 'beta_integration', 'zebra_integration'])
        
        # Test enabled only - should only include enabled, sorted by label
        enabled_integrations = manager.get_integration_data_list(enabled_only=True)
        self.assertEqual(len(enabled_integrations), 2)
        self.assertEqual([data.integration_id for data in enabled_integrations],
                         ['beta_integration', 'zebra_integration'])

    def test_get_default_integration_data(self):
        """Test default integration selection logic."""
        manager = IntegrationManager()
        
        # Test with no integrations
        result = manager.get_default_integration_data()
        self.assertIsNone(result)
        
        # Test with disabled integrations only
        disabled_integration = Integration.objects.create(
            integration_id='disabled_integration',
            is_enabled=False
        )
        disabled_data = IntegrationData(
            integration_gateway=MockIntegrationGateway('disabled_integration', 'Disabled'),
            integration=disabled_integration
        )
        manager._integration_data_map = {'disabled_integration': disabled_data}
        
        result = manager.get_default_integration_data()
        self.assertIsNone(result)
        
        # Test with enabled integrations - should return first alphabetically
        enabled_integration1 = Integration.objects.create(
            integration_id='zebra_integration',
            is_enabled=True
        )
        enabled_integration2 = Integration.objects.create(
            integration_id='alpha_integration',
            is_enabled=True
        )
        
        enabled_data1 = IntegrationData(
            integration_gateway=MockIntegrationGateway('zebra_integration', 'Zebra'),
            integration=enabled_integration1
        )
        enabled_data2 = IntegrationData(
            integration_gateway=MockIntegrationGateway('alpha_integration', 'Alpha'),
            integration=enabled_integration2
        )
        
        manager._integration_data_map.update({
            'zebra_integration': enabled_data1,
            'alpha_integration': enabled_data2
        })
        
        result = manager.get_default_integration_data()
        self.assertEqual(result.integration_id, 'alpha_integration')

    def test_get_integration_data_success_and_error(self):
        """Test integration data retrieval by ID."""
        manager = IntegrationManager()
        
        integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )
        data = IntegrationData(
            integration_gateway=MockIntegrationGateway('test_integration'),
            integration=integration
        )
        manager._integration_data_map = {'test_integration': data}
        
        # Test successful retrieval
        result = manager.get_integration_data('test_integration')
        self.assertEqual(result, data)
        self.assertEqual(result.integration_id, 'test_integration')
        
        # Test error for unknown integration
        with self.assertRaises(KeyError) as context:
            manager.get_integration_data('unknown_integration')
        
        error_message = str(context.exception)
        self.assertIn('Unknown integration id "unknown_integration"', error_message)

    def test_get_integration_gateway_success_and_error(self):
        """Test integration gateway retrieval by ID."""
        manager = IntegrationManager()
        
        gateway = MockIntegrationGateway('test_integration')
        integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )
        data = IntegrationData(
            integration_gateway=gateway,
            integration=integration
        )
        manager._integration_data_map = {'test_integration': data}
        
        # Test successful retrieval
        result = manager.get_integration_gateway('test_integration')
        self.assertEqual(result, gateway)
        
        # Test error for unknown integration
        with self.assertRaises(KeyError) as context:
            manager.get_integration_gateway('unknown_integration')
        
        error_message = str(context.exception)
        self.assertIn('Unknown integration id "unknown_integration"', error_message)

    def test_refresh_integrations_from_db(self):
        """Test database refresh for all integration models."""
        manager = IntegrationManager()
        
        # Create integrations and modify them outside the data objects
        integration1 = Integration.objects.create(
            integration_id='test_integration_1',
            is_enabled=False
        )
        integration2 = Integration.objects.create(
            integration_id='test_integration_2', 
            is_enabled=False
        )
        
        data1 = IntegrationData(
            integration_gateway=MockIntegrationGateway('test_integration_1'),
            integration=integration1
        )
        data2 = IntegrationData(
            integration_gateway=MockIntegrationGateway('test_integration_2'),
            integration=integration2
        )
        
        manager._integration_data_map = {
            'test_integration_1': data1,
            'test_integration_2': data2
        }
        
        # Modify database directly (simulating external change)
        Integration.objects.filter(integration_id='test_integration_1').update(is_enabled=True)
        Integration.objects.filter(integration_id='test_integration_2').update(is_enabled=True)
        
        # Verify objects in memory still show old values
        self.assertFalse(data1.integration.is_enabled)
        self.assertFalse(data2.integration.is_enabled)
        
        # Call refresh and verify updates
        manager.refresh_integrations_from_db()
        
        self.assertTrue(data1.integration.is_enabled)
        self.assertTrue(data2.integration.is_enabled)

    @patch('hi.integrations.integration_manager.apps.get_app_configs')
    @patch('hi.integrations.integration_manager.import_module_safe')
    def test_discover_defined_integrations(self, mock_import, mock_get_apps):
        """Test auto-discovery of integration gateways in services modules."""
        manager = IntegrationManager()
        
        # Mock app configs
        mock_app1 = Mock()
        mock_app1.name = 'hi.services.test_service'
        mock_app2 = Mock()
        mock_app2.name = 'hi.other.module'  # Should be skipped
        mock_app3 = Mock()
        mock_app3.name = 'hi.services.another_service'
        
        mock_get_apps.return_value = [mock_app1, mock_app2, mock_app3]
        
        # Mock integration modules
        mock_gateway_class1 = type('TestGateway1', (IntegrationGateway,), {
            'get_metadata': lambda self: IntegrationMetaData(
                integration_id='test_service',
                label='Test Service',
                attribute_type=MockIntegrationAttributeType,
                allow_entity_deletion=True
            )
        })
        
        mock_gateway_class2 = type('TestGateway2', (IntegrationGateway,), {
            'get_metadata': lambda self: IntegrationMetaData(
                integration_id='another_service',
                label='Another Service',
                attribute_type=MockIntegrationAttributeType,
                allow_entity_deletion=True
            )
        })
        
        mock_module1 = Mock()
        mock_module1.__dir__ = lambda self: ['TestGateway1', 'other_class', 'IntegrationGateway']
        mock_module1.TestGateway1 = mock_gateway_class1
        mock_module1.other_class = str  # Should be ignored
        mock_module1.IntegrationGateway = IntegrationGateway  # Should be ignored (base class)
        
        mock_module2 = Mock()
        mock_module2.__dir__ = lambda self: ['TestGateway2']
        mock_module2.TestGateway2 = mock_gateway_class2
        
        def mock_import_side_effect(module_name):
            if module_name == 'hi.services.test_service.integration':
                return mock_module1
            elif module_name == 'hi.services.another_service.integration':
                return mock_module2
            return None
        
        mock_import.side_effect = mock_import_side_effect
        
        # Execute discovery
        result = manager._discover_defined_integrations()
        
        # Verify correct modules were imported
        expected_module_names = [
            'hi.services.test_service.integration',
            'hi.services.another_service.integration'
        ]
        # Extract module names from call_args_list
        # The function is called with keyword argument 'module_name'
        actual_calls = [call.kwargs['module_name'] for call in mock_import.call_args_list]
        
        self.assertEqual(set(actual_calls), set(expected_module_names))
        
        # Verify correct gateways were discovered
        self.assertEqual(len(result), 2)
        self.assertIn('test_service', result)
        self.assertIn('another_service', result)
        
        # Verify gateway instances were created correctly
        self.assertIsInstance(result['test_service'], mock_gateway_class1)
        self.assertIsInstance(result['another_service'], mock_gateway_class2)

    def test_load_existing_integrations(self):
        """Test loading existing integrations from database."""
        manager = IntegrationManager()
        
        # Create test integrations
        integration1 = Integration.objects.create(
            integration_id='existing_integration_1',
            is_enabled=True
        )
        integration2 = Integration.objects.create(
            integration_id='existing_integration_2',
            is_enabled=False
        )
        
        result = manager._load_existing_integrations()
        
        # Verify correct mapping
        self.assertEqual(len(result), 2)
        self.assertEqual(result['existing_integration_1'], integration1)
        self.assertEqual(result['existing_integration_2'], integration2)
        
        # Verify return type is dict with integration_id as key
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {'existing_integration_1', 'existing_integration_2'})

    def test_thread_safety_with_data_lock(self):
        """Test that data operations are thread-safe using _data_lock."""
        manager = IntegrationManager()
        
        # Clear any existing data to start clean
        manager._integration_data_map.clear()
        
        results = []
        errors = []
        
        def concurrent_operation():
            try:
                # Simulate operations that would use _data_lock
                with manager._data_lock:
                    # Simulate some data modification
                    current_count = len(manager._integration_data_map)
                    # Add artificial delay to increase chance of race condition
                    import time
                    time.sleep(0.001)
                    manager._integration_data_map[f'test_{current_count}'] = f'data_{current_count}'
                    results.append(len(manager._integration_data_map))
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple concurrent operations
        threads = [threading.Thread(target=concurrent_operation) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify all operations completed
        self.assertEqual(len(results), 10)
        
        # Verify final state is consistent (10 items added)
        self.assertEqual(len(manager._integration_data_map), 10)

    def test_initialization_flag_prevents_double_initialization(self):
        """Test that _initialized flag prevents multiple initialization."""
        manager = IntegrationManager()
        
        # Verify initial state
        self.assertFalse(manager._initialized)
        self.assertIsNone(manager._monitor_event_loop)
        
        # Mock event loop
        mock_event_loop = Mock()
        
        # Set up patches for async methods called during initialization
        with patch.object(manager, '_load_integration_data', new=AsyncMock()) as mock_load, \
             patch.object(manager, '_start_all_integration_monitors', new=AsyncMock()) as mock_start_monitors:
            
            async def test_initialization():
                # First initialization
                await manager.initialize(mock_event_loop)
                
                # Verify initialization happened
                self.assertTrue(manager._initialized)
                self.assertEqual(manager._monitor_event_loop, mock_event_loop)
                
                # Reset mocks
                mock_load.reset_mock()
                mock_start_monitors.reset_mock()
                
                # Second initialization attempt
                await manager.initialize(mock_event_loop)
                
                # Verify methods were not called again
                mock_load.assert_not_called()
                mock_start_monitors.assert_not_called()
            
            # Run the test
            asyncio.run(test_initialization())

    def test_ensure_all_attributes_exist_new_attributes(self):
        """Test creation of new integration attributes when they don't exist."""
        manager = IntegrationManager()
        
        # Create integration
        integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )
        
        # Create metadata with attribute types
        metadata = IntegrationMetaData(
            integration_id='test_integration',
            label='Test Integration',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        # Verify no attributes exist initially
        self.assertEqual(integration.attributes.count(), 0)
        
        # Call method to ensure attributes exist
        manager._ensure_all_attributes_exist(metadata, integration)
        
        # Verify attribute was created
        self.assertEqual(integration.attributes.count(), 1)
        
        created_attr = integration.attributes.first()
        self.assertEqual(created_attr.name, 'Test Attribute')
        self.assertEqual(created_attr.value, 'default')
        self.assertEqual(created_attr.value_type_str, str(AttributeValueType.TEXT))
        self.assertTrue(created_attr.is_editable)
        self.assertTrue(created_attr.is_required)
        
        # Verify integration key format
        expected_key = f'test_integration.{str(MockIntegrationAttributeType.TEST_ATTR).lower()}'
        self.assertEqual(created_attr.integration_key_str, expected_key)

    def test_ensure_all_attributes_exist_no_duplicates(self):
        """Test that existing attributes are not duplicated."""
        manager = IntegrationManager()
        
        integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )
        
        # Create existing attribute
        existing_key = IntegrationKey(
            integration_id='test_integration',
            integration_name=str(MockIntegrationAttributeType.TEST_ATTR)
        )
        IntegrationAttribute.objects.create(
            integration=integration,
            name='Existing Attribute',
            value='existing_value',
            value_type_str=str(AttributeValueType.TEXT),
            integration_key_str=str(existing_key),
            attribute_type_str=AttributeType.PREDEFINED
        )
        
        # Verify one attribute exists
        self.assertEqual(integration.attributes.count(), 1)
        
        # Create metadata
        metadata = IntegrationMetaData(
            integration_id='test_integration',
            label='Test Integration',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        # Call method
        manager._ensure_all_attributes_exist(metadata, integration)
        
        # Verify no new attributes were created
        self.assertEqual(integration.attributes.count(), 1)
        
        # Verify existing attribute was not modified
        attr = integration.attributes.first()
        self.assertEqual(attr.name, 'Existing Attribute')
        self.assertEqual(attr.value, 'existing_value')

    def test_disable_integration_database_transaction(self):
        """Test disable integration with database transaction and monitor stop."""
        manager = IntegrationManager()
        
        integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )
        
        gateway = MockIntegrationGateway('test_integration')
        data = IntegrationData(
            integration_gateway=gateway,
            integration=integration
        )
        
        with patch.object(manager, '_stop_integration_monitor') as mock_stop:
            # Call disable
            manager.disable_integration(data)
            
            # Verify database changes
            integration.refresh_from_db()
            self.assertFalse(integration.is_enabled)
            
            # Verify monitor was stopped
            mock_stop.assert_called_once_with(integration_data=data)

    def test_data_lock_thread_safety_during_attribute_creation(self):
        """Test thread safety of attribute creation operations."""
        # Note: This test verifies the presence of thread safety mechanisms
        # Full concurrency testing is difficult with SQLite's table locking
        manager = IntegrationManager()
        
        integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )
        
        metadata = IntegrationMetaData(
            integration_id='test_integration',
            label='Test Integration',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        # Verify the method uses the data lock
        with patch.object(manager, '_data_lock') as mock_lock:
            manager._ensure_all_attributes_exist(metadata, integration)
            
            # Verify the lock was used as a context manager
            mock_lock.__enter__.assert_called_once()
            mock_lock.__exit__.assert_called_once()
        
        # Verify attribute was created
        self.assertEqual(integration.attributes.count(), 1)

    @patch('hi.integrations.integration_manager.logger')
    def test_discover_defined_integrations_error_handling(self, mock_logger):
        """Test error handling during integration discovery."""
        manager = IntegrationManager()
        
        # Mock app configs
        mock_app = Mock()
        mock_app.name = 'hi.services.failing_service'
        
        with patch('hi.integrations.integration_manager.apps.get_app_configs', return_value=[mock_app]), \
             patch('hi.integrations.integration_manager.import_module_safe', side_effect=Exception("Import failed")):
            
            # Execute discovery
            result = manager._discover_defined_integrations()
            
            # Verify empty result when import fails
            self.assertEqual(result, {})
            
            # Verify error was logged
            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args[0]
            self.assertIn('Problem getting integration gateway', call_args[0])
            self.assertIn('hi.services.failing_service.integration', call_args[0])

    def test_monitor_management_methods(self):
        """Test monitor start/stop management methods."""
        manager = IntegrationManager()
        
        integration = Integration.objects.create(
            integration_id='test_integration',
            is_enabled=True
        )
        
        gateway = MockIntegrationGateway('test_integration')
        data = IntegrationData(
            integration_gateway=gateway,
            integration=integration
        )
        
        # Test stopping non-existent monitor
        manager._stop_integration_monitor(data)  # Should not raise error
        
        # Test with monitor in map
        mock_monitor = Mock()
        mock_monitor.is_running = True
        manager._monitor_map['test_integration'] = mock_monitor
        
        # Test stopping existing monitor
        manager._stop_integration_monitor(data)
        
        # Verify monitor was stopped and removed
        mock_monitor.stop.assert_called_once()
        self.assertNotIn('test_integration', manager._monitor_map)
        
        # Test stopping already stopped monitor
        mock_monitor2 = Mock()
        mock_monitor2.is_running = False
        manager._monitor_map['test_integration'] = mock_monitor2
        
        manager._stop_integration_monitor(data)
        
        # Verify stop was not called on already stopped monitor
        mock_monitor2.stop.assert_not_called()
        self.assertNotIn('test_integration', manager._monitor_map)
