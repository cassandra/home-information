import logging
from unittest.mock import Mock, patch

from hi.apps.console.console_manager import ConsoleManager
from hi.apps.console.transient_models import VideoStreamEntity
from hi.apps.entity.enums import EntityStateType
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

    def test_get_video_stream_entity_list_returns_list(self):
        """Test get_video_stream_entity_list returns a list of VideoStreamEntity objects."""
        manager = ConsoleManager()
        manager.ensure_initialized()
        
        result = manager.get_video_stream_entity_list()
        
        # Should return a list
        self.assertIsInstance(result, list)
        
        # If there are results, they should be VideoStreamEntity objects
        for item in result:
            self.assertIsInstance(item, VideoStreamEntity)
        return

    @patch('hi.apps.console.console_manager.EntityManager')
    def test_build_video_stream_entity_list_behavior(self, mock_entity_manager_class):
        """Test _build_video_stream_entity_list processes entity data correctly."""
        # Setup test entity with video stream state
        mock_entity = Mock()
        mock_entity.name = 'Test Camera'
        
        mock_video_state = Mock()
        mock_video_state.entity_state_type = EntityStateType.VIDEO_STREAM
        
        mock_sensor = Mock()
        mock_video_state.sensors.all.return_value = [mock_sensor]
        mock_entity.states.all.return_value = [mock_video_state]
        
        # Setup EntityManager mock
        mock_entity_manager = Mock()
        mock_entity_manager.get_view_stream_entities.return_value = [mock_entity]
        mock_entity_manager.register_change_listener = Mock()
        mock_entity_manager_class.return_value = mock_entity_manager
        
        # Reset singleton for clean test
        ConsoleManager._instances = {}
        manager = ConsoleManager()
        
        # Test build method directly
        result = manager._build_video_stream_entity_list()
        
        # Should create VideoStreamEntity objects
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], VideoStreamEntity)
        self.assertEqual(result[0].entity.name, 'Test Camera')
        return

    def test_reload_video_stream_entity_list_callable(self):
        """Test _reload_video_stream_entity_list method can be called."""
        manager = ConsoleManager()
        manager.ensure_initialized()
        
        # Call reload method - should not raise exception
        manager._reload_video_stream_entity_list()
        
        # Should still have a list (may be same or different content)
        self.assertIsNotNone(manager._video_stream_entity_list)
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
