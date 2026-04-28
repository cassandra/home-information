"""
Unit tests for IntegrationManager.
"""

import asyncio
import logging
import threading
from unittest.mock import Mock, AsyncMock, patch

from django.test import TestCase

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.models import Entity, EntityAttribute
from hi.integrations.exceptions import IntegrationConnectionError
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationKey,
)
from hi.integrations.enums import IntegrationAttributeType, IntegrationDisableMode

logging.disable(logging.CRITICAL)


class MockIntegrationAttributeType(IntegrationAttributeType):
    """Mock integration attribute type for testing."""
    
    TEST_ATTR = ('Test Attribute', 'Test description', AttributeValueType.TEXT, {}, True, True, 'default')


class MockIntegrationGateway(IntegrationGateway):
    """Mock integration gateway for testing."""

    def __init__(self, integration_id='test_integration', label='Test Integration',
                 connection_test_result=None):
        self.integration_id = integration_id
        self.label = label
        # Default to a passing probe so existing resume/pause tests don't
        # need to know about the new test_connection step.
        self.connection_test_result = (
            connection_test_result if connection_test_result is not None
            else ConnectionTestResult.success()
        )

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

    def test_connection(self, integration_attributes, timeout_secs):
        return self.connection_test_result


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
    def testdiscover_defined_integrations(self, mock_import, mock_get_apps):
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
        result = manager.discover_defined_integrations()
        
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
        manager.reset_for_testing()
        
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

    def testensure_all_attributes_exist_new_attributes(self):
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
        manager.ensure_all_attributes_exist(metadata, integration)
        
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

    def testensure_all_attributes_exist_no_duplicates(self):
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
        manager.ensure_all_attributes_exist(metadata, integration)
        
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
            is_enabled=True,
            is_paused=True,
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
            # Disable also clears is_paused so a subsequent Configure starts clean.
            self.assertFalse(integration.is_paused)

            # Verify monitor was stopped
            mock_stop.assert_called_once_with(integration_data=data)

    def _make_integration_with_entities(self, integration_id, include_user_data_entity):
        """
        Fixture helper: create an integration with two attached entities —
        one integration-only (no user data) and optionally one with
        user-created attributes. Also creates retained IntegrationAttribute
        rows to verify config retention on disable.
        """
        integration = Integration.objects.create(
            integration_id=integration_id,
            is_enabled=True,
            is_paused=False,
        )
        # Retained configuration attributes (should survive disable).
        IntegrationAttribute.objects.create(
            integration=integration,
            name='API URL',
            value='http://example.com',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED),
        )

        integration_only_entity = Entity.objects.create(
            name='Integration Only Entity',
            entity_type_str='LIGHT',
            integration_id=integration_id,
            integration_name='device_no_user_data',
        )
        EntityAttribute.objects.create(
            entity=integration_only_entity,
            name='Integration Config',
            value='from integration',
            value_type_str=str(AttributeValueType.TEXT),
            attribute_type_str=str(AttributeType.PREDEFINED),
            integration_key_str=f'{integration_id}:device_no_user_data',
        )

        user_data_entity = None
        if include_user_data_entity:
            user_data_entity = Entity.objects.create(
                name='User Data Entity',
                entity_type_str='LIGHT',
                integration_id=integration_id,
                integration_name='device_with_user_data',
            )
            EntityAttribute.objects.create(
                entity=user_data_entity,
                name='User Note',
                value='user-supplied note',
                value_type_str=str(AttributeValueType.TEXT),
                attribute_type_str=str(AttributeType.CUSTOM),
            )

        gateway = MockIntegrationGateway(integration_id)
        data = IntegrationData(integration_gateway=gateway, integration=integration)
        return integration, data, integration_only_entity, user_data_entity

    def test_disable_integration_safe_mode_splits_entities_by_user_data(self):
        """SAFE mode deletes no-user-data entities and preserves user-data entities."""
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration, data, integration_only_entity, user_data_entity = (
            self._make_integration_with_entities('disable_safe_test', include_user_data_entity=True)
        )
        no_user_id = integration_only_entity.id
        user_data_id = user_data_entity.id

        with patch.object(manager, '_stop_integration_monitor'):
            manager.disable_integration(data, mode=IntegrationDisableMode.SAFE)

        # Integration-only entity is gone.
        self.assertFalse(Entity.objects.filter(id=no_user_id).exists())
        # User-data entity survives and is disconnected (integration_id cleared).
        preserved = Entity.objects.get(id=user_data_id)
        self.assertIsNone(preserved.integration_id)
        self.assertTrue(preserved.name.startswith('[Disconnected]'))

        # Configuration attributes retained for re-Configure.
        self.assertEqual(integration.attributes.count(), 1)

    def test_disable_integration_all_mode_deletes_everything(self):
        """ALL mode hard-deletes every attached entity regardless of user data."""
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration, data, integration_only_entity, user_data_entity = (
            self._make_integration_with_entities('disable_all_test', include_user_data_entity=True)
        )
        no_user_id = integration_only_entity.id
        user_data_id = user_data_entity.id

        with patch.object(manager, '_stop_integration_monitor'):
            manager.disable_integration(data, mode=IntegrationDisableMode.ALL)

        self.assertFalse(Entity.objects.filter(id=no_user_id).exists())
        self.assertFalse(Entity.objects.filter(id=user_data_id).exists())

        # Configuration attributes retained even when entities all deleted.
        self.assertEqual(integration.attributes.count(), 1)

    def test_disable_integration_stops_monitor_before_entity_changes(self):
        """Monitors must stop before any entity mutation to avoid races with sync."""
        manager = IntegrationManager()
        manager.reset_for_testing()

        _integration, data, integration_only_entity, _ = (
            self._make_integration_with_entities('disable_order_test', include_user_data_entity=False)
        )
        entity_id = integration_only_entity.id

        call_order = []

        def record_stop(**_kwargs):
            # At the moment the monitor is stopped, the entity must still exist.
            call_order.append(('stop', Entity.objects.filter(id=entity_id).exists()))

        def record_entity_delete_observer(sender, instance, **_kwargs):
            if instance.id == entity_id:
                call_order.append(('entity_delete', instance.id))

        from django.db.models.signals import pre_delete
        pre_delete.connect(record_entity_delete_observer, sender=Entity)
        try:
            with patch.object(manager, '_stop_integration_monitor', side_effect=record_stop):
                manager.disable_integration(data, mode=IntegrationDisableMode.SAFE)
        finally:
            pre_delete.disconnect(record_entity_delete_observer, sender=Entity)

        self.assertEqual(call_order[0][0], 'stop')
        self.assertTrue(call_order[0][1], 'Entity should still exist when stop is called')
        self.assertTrue(any(event[0] == 'entity_delete' for event in call_order))

    def test_pause_integration_noop_when_not_enabled(self):
        """Pause on a not-enabled integration is a no-op (no DB write, no stop)."""
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration = Integration.objects.create(
            integration_id='pause_noop_test',
            is_enabled=False,
            is_paused=False,
        )
        gateway = MockIntegrationGateway('pause_noop_test')
        data = IntegrationData(integration_gateway=gateway, integration=integration)

        with patch.object(manager, '_stop_integration_monitor') as mock_stop:
            manager.pause_integration(data)

            integration.refresh_from_db()
            self.assertFalse(integration.is_enabled)
            self.assertFalse(integration.is_paused)
            mock_stop.assert_not_called()

    def test_pause_integration_noop_when_already_paused(self):
        """Pause on an already-paused integration is a no-op."""
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration = Integration.objects.create(
            integration_id='pause_already_test',
            is_enabled=True,
            is_paused=True,
        )
        gateway = MockIntegrationGateway('pause_already_test')
        data = IntegrationData(integration_gateway=gateway, integration=integration)

        with patch.object(manager, '_stop_integration_monitor') as mock_stop:
            manager.pause_integration(data)

            integration.refresh_from_db()
            self.assertTrue(integration.is_paused)
            mock_stop.assert_not_called()

    def test_resume_integration_noop_when_not_enabled(self):
        """Resume on a not-enabled integration is a no-op."""
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration = Integration.objects.create(
            integration_id='resume_noop_test',
            is_enabled=False,
            is_paused=False,
        )
        gateway = MockIntegrationGateway('resume_noop_test')
        data = IntegrationData(integration_gateway=gateway, integration=integration)

        with patch.object(manager, '_launch_integration_monitor_task') as mock_launch:
            manager.resume_integration(data)

            integration.refresh_from_db()
            self.assertFalse(integration.is_enabled)
            mock_launch.assert_not_called()

    def test_resume_integration_retries_launch_when_not_paused(self):
        """Resume always attempts the launch even when is_paused is already False.

        This allows the user to recover from a prior failed launch by invoking
        resume again. _launch_integration_monitor_task is idempotent when the
        monitor is already running.
        """
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration = Integration.objects.create(
            integration_id='resume_retry_test',
            is_enabled=True,
            is_paused=False,
        )
        gateway = MockIntegrationGateway('resume_retry_test')
        data = IntegrationData(integration_gateway=gateway, integration=integration)

        with patch.object(manager, '_launch_integration_monitor_task') as mock_launch:
            manager.resume_integration(data)

            mock_launch.assert_called_once_with(integration_data=data)

    def test_resume_integration_short_circuits_when_connection_test_fails(self):
        """Resume must not relaunch monitors when the connection probe fails.

        Without this short-circuit a paused integration could be resumed
        against an unreachable upstream and silently fail in the background.
        """
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration = Integration.objects.create(
            integration_id='resume_probe_fail',
            is_enabled=True,
            is_paused=True,
        )
        gateway = MockIntegrationGateway(
            'resume_probe_fail',
            connection_test_result=ConnectionTestResult.failure(
                'Cannot reach upstream'
            ),
        )
        data = IntegrationData(integration_gateway=gateway, integration=integration)

        with patch.object(manager, '_launch_integration_monitor_task') as mock_launch:
            with self.assertRaises(IntegrationConnectionError) as context:
                manager.resume_integration(data)

            self.assertIn('Cannot reach upstream', str(context.exception))
            mock_launch.assert_not_called()

            # is_paused state must NOT have been flipped to False.
            integration.refresh_from_db()
            self.assertTrue(integration.is_paused)

    def test_resume_integration_passes_bounded_timeout_to_gateway(self):
        """Resume must invoke test_connection with the configured bounded timeout."""
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration = Integration.objects.create(
            integration_id='resume_timeout_test',
            is_enabled=True,
            is_paused=True,
        )
        gateway = MockIntegrationGateway('resume_timeout_test')
        data = IntegrationData(integration_gateway=gateway, integration=integration)

        with patch.object(gateway, 'test_connection',
                          return_value=ConnectionTestResult.success()) as mock_probe:
            with patch.object(manager, '_launch_integration_monitor_task'):
                manager.resume_integration(data)

            mock_probe.assert_called_once()
            kwargs = mock_probe.call_args.kwargs
            self.assertEqual(kwargs['timeout_secs'],
                             IntegrationManager.HEALTH_CHECK_TIMEOUT_SECS)

    def test_resume_integration_aborts_when_disabled_during_probe(self):
        """
        TOCTOU close-out: if another caller disables the integration
        while resume_integration is running its lock-free probe, the
        post-probe state mutation must be abandoned (no monitor launch,
        is_paused not flipped) and the caller must be told why.
        """
        manager = IntegrationManager()
        manager.reset_for_testing()

        integration = Integration.objects.create(
            integration_id='resume_toctou_test',
            is_enabled=True,
            is_paused=True,
        )
        gateway = MockIntegrationGateway('resume_toctou_test')
        data = IntegrationData(integration_gateway=gateway, integration=integration)

        # Simulate a concurrent disable that lands BETWEEN the lock-free
        # probe and the lock-acquired state mutation. test_connection's
        # side_effect mutates the DB row to is_enabled=False right before
        # returning success, then resume_integration's inside-lock
        # refresh_from_db() picks that up.
        def disable_during_probe(*args, **kwargs):
            integration.is_enabled = False
            integration.save()
            return ConnectionTestResult.success()

        with patch.object(gateway, 'test_connection',
                          side_effect=disable_during_probe):
            with patch.object(manager, '_launch_integration_monitor_task') as mock_launch:
                with self.assertRaises(IntegrationConnectionError) as context:
                    manager.resume_integration(data)

                self.assertIn('disabled while resume was probing',
                              str(context.exception))
                mock_launch.assert_not_called()

        # is_paused must NOT have been flipped — disable_integration is
        # responsible for the disabled-state cleanup, not us.
        integration.refresh_from_db()
        self.assertTrue(integration.is_paused)
        self.assertFalse(integration.is_enabled)


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
            manager.ensure_all_attributes_exist(metadata, integration)
            
            # Verify the lock was used as a context manager
            mock_lock.__enter__.assert_called_once()
            mock_lock.__exit__.assert_called_once()
        
        # Verify attribute was created
        self.assertEqual(integration.attributes.count(), 1)

    @patch('hi.integrations.integration_manager.logger')
    def testdiscover_defined_integrations_error_handling(self, mock_logger):
        """Test error handling during integration discovery."""
        manager = IntegrationManager()
        
        # Mock app configs
        mock_app = Mock()
        mock_app.name = 'hi.services.failing_service'
        
        with patch('hi.integrations.integration_manager.apps.get_app_configs', return_value=[mock_app]), \
             patch('hi.integrations.integration_manager.import_module_safe', side_effect=Exception("Import failed")):
            
            # Execute discovery
            result = manager.discover_defined_integrations()
            
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
