import logging

from hi.apps.console.console_manager import ConsoleManager
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestConsoleManager(BaseTestCase):

    def test_console_manager_singleton_behavior(self):
        """Test ConsoleManager singleton pattern - critical for system consistency."""
        manager1 = ConsoleManager()
        manager2 = ConsoleManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_console_manager_initialization_state(self):
        """Test ConsoleManager initialization state tracking - critical setup logic."""
        manager = ConsoleManager()
        
        # May already be initialized due to singleton pattern
        # Test ensure_initialized sets proper state
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        
        # Subsequent calls should not change state
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        return

    def test_console_manager_mixin_inheritance(self):
        """Test ConsoleManager mixin inheritance - critical for system integration."""
        manager = ConsoleManager()
        
        # Should inherit from SettingsMixin
        self.assertTrue(hasattr(manager, 'settings_manager'))
        
        # Should inherit from SensorResponseMixin
        self.assertTrue(hasattr(manager, 'sensor_response_manager'))
        
        # Should be a Singleton
        from hi.apps.common.singleton import Singleton
        self.assertIsInstance(manager, Singleton)
        return

    def test_ensure_initialized_idempotent(self):
        """Test ensure_initialized can be called multiple times safely."""
        manager = ConsoleManager()
        
        # Call ensure_initialized multiple times
        manager.ensure_initialized()
        first_list = manager._video_stream_entity_list
        
        manager.ensure_initialized()
        second_list = manager._video_stream_entity_list
        
        # Should maintain initialization state
        self.assertTrue(manager._was_initialized)
        
        # List reference should remain the same (no unnecessary rebuilds)
        self.assertIs(first_list, second_list)
        return
