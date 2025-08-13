import logging
from unittest.mock import Mock
from threading import Lock
import threading

from hi.apps.config.models import Subsystem, SubsystemAttribute
from hi.apps.config.settings_manager import SettingsManager
from hi.apps.attribute.enums import AttributeValueType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSettingsManager(BaseTestCase):

    def test_singleton_behavior(self):
        """Test SettingsManager singleton pattern - critical for system consistency."""
        manager1 = SettingsManager()
        manager2 = SettingsManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_set_setting_value_with_database_update(self):
        """Test set_setting_value updates both memory and database - complex business logic."""
        manager = SettingsManager()
        
        # Create test data
        subsystem = Subsystem.objects.create(
            name='Test Subsystem',
            subsystem_key='test_subsystem',
        )
        test_key = 'test.set.setting.key'
        SubsystemAttribute.objects.create(
            subsystem=subsystem,
            setting_key=test_key,
            value_type=AttributeValueType.TEXT,
            value='initial_value',
        )
        
        manager.reload()
        
        # Create a mock setting enum for testing
        mock_setting = Mock()
        mock_setting.key = test_key
        
        # Update setting value
        manager.set_setting_value(mock_setting, 'new_value')
        
        # Verify value was updated in memory
        value = manager._attribute_value_map.get(test_key)
        self.assertEqual(value, 'new_value')
        
        # Verify database was updated
        attribute = SubsystemAttribute.objects.get(setting_key=test_key)
        self.assertEqual(attribute.value, 'new_value')
        return

    def test_set_setting_value_nonexistent_key_error(self):
        """Test set_setting_value error handling for non-existent settings - critical error handling."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Create mock setting with non-existent key
        mock_setting = Mock()
        mock_setting.key = 'non.existent.setting.key'
        
        with self.assertRaises(KeyError):
            manager.set_setting_value(mock_setting, 'any_value')
        return

    def test_change_listener_system_notification(self):
        """Test change listener system - core functionality for system integration."""
        manager = SettingsManager()
        
        # Create mock callbacks
        callback1 = Mock()
        callback2 = Mock()
        
        manager.register_change_listener(callback1)
        manager.register_change_listener(callback2)
        
        # Create minimal test data for reload
        Subsystem.objects.create(
            name='Test Subsystem',
            subsystem_key='test_subsystem',
        )
        
        manager.ensure_initialized()
        
        # Reset mocks to focus on reload call
        callback1.reset_mock()
        callback2.reset_mock()
        
        # Trigger reload which should notify listeners
        manager.reload()
        
        callback1.assert_called_once()
        callback2.assert_called_once()
        return

    def test_change_listener_exception_handling(self):
        """Test change listener error handling - system should be resilient to callback failures."""
        manager = SettingsManager()
        
        # Create callback that raises exception
        def failing_callback():
            raise ValueError("Test exception")
        
        # Create normal callback
        normal_callback = Mock()
        
        manager.register_change_listener(failing_callback)
        manager.register_change_listener(normal_callback)
        
        # Create minimal test data
        Subsystem.objects.create(
            name='Test Subsystem',
            subsystem_key='test_subsystem',
        )
        
        # Clear any previous calls to focus on this test
        normal_callback.reset_mock()
        
        # Reload should not fail despite exception in callback
        manager.reload()
        
        # Normal callback should still be called
        normal_callback.assert_called_once()
        return

    def test_reload_picks_up_database_changes(self):
        """Test reload method detects database changes - critical synchronization logic."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Test that reload picks up changes by modifying an existing system setting
        existing_attrs = list(SubsystemAttribute.objects.all()[:1])
        if existing_attrs:
            attr = existing_attrs[0]
            original_value = attr.value
            
            # Change the value
            attr.value = f'test_modified_{original_value}'
            attr.save()
            
            # Reload should pick up the change
            manager.reload()
            updated_value = manager._attribute_value_map.get(attr.setting_key)
            self.assertEqual(updated_value, f'test_modified_{original_value}')
            
            # Restore original value
            attr.value = original_value
            attr.save()
            manager.reload()
        else:
            self.skipTest("No existing attributes to test reload with")
        return

    def test_thread_safety_locks_exist(self):
        """Test thread safety locks are properly initialized - critical for concurrent access."""
        manager = SettingsManager()
        
        # Verify locks exist and are proper lock types  
        lock_types = (type(Lock()), type(threading.Lock()), type(threading.RLock()))
        self.assertIsInstance(manager._subsystems_lock, lock_types)
        self.assertIsInstance(manager._attributes_lock, lock_types)
        return