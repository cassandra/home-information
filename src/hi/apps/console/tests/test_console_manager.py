import logging
from unittest.mock import Mock, patch

from hi.apps.console.console_manager import ConsoleManager
from hi.apps.console.transient_models import VideoStreamEntity
from hi.tests.base_test_case import BaseTestCase

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

    def test_console_manager_method_existence(self):
        """Test ConsoleManager has expected methods - critical API consistency."""
        manager = ConsoleManager()
        
        # Should have public interface methods
        self.assertTrue(hasattr(manager, 'get_console_audio_map'))
        self.assertTrue(hasattr(manager, 'get_video_stream_entity_list'))
        self.assertTrue(callable(manager.get_console_audio_map))
        self.assertTrue(callable(manager.get_video_stream_entity_list))
        return

    def test_console_manager_reload_methods_exist(self):
        """Test reload method existence - critical for change handling."""
        manager = ConsoleManager()
        
        # Should have reload methods for change listeners
        self.assertTrue(hasattr(manager, '_reload_console_audio_map'))
        self.assertTrue(hasattr(manager, '_reload_video_stream_entity_list'))
        
        # Methods should be callable
        self.assertTrue(callable(manager._reload_console_audio_map))
        self.assertTrue(callable(manager._reload_video_stream_entity_list))
        return

    def test_console_manager_build_methods_exist(self):
        """Test build method existence - critical for data construction."""
        manager = ConsoleManager()
        
        # Should have build methods
        self.assertTrue(hasattr(manager, '_build_console_audio_map'))
        self.assertTrue(hasattr(manager, '_build_video_stream_entity_list'))
        
        # Methods should be callable
        self.assertTrue(callable(manager._build_console_audio_map))
        self.assertTrue(callable(manager._build_video_stream_entity_list))
        return