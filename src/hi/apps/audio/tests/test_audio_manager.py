import logging

from hi.apps.audio.audio_manager import AudioManager
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAudioManager(BaseTestCase):

    def test_audio_manager_singleton_behavior(self):
        """Test AudioManager singleton pattern - critical for system consistency."""
        manager1 = AudioManager()
        manager2 = AudioManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_audio_manager_initialization_state(self):
        """Test AudioManager initialization state tracking - critical setup logic."""
        manager = AudioManager()
        
        # Test ensure_initialized sets proper state
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        
        # Subsequent calls should not change state
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        return

    def test_audio_manager_mixin_inheritance(self):
        """Test AudioManager mixin inheritance - critical for system integration."""
        manager = AudioManager()
        
        # Should inherit from SettingsMixin
        self.assertTrue(hasattr(manager, 'settings_manager'))
        
        # Should be a Singleton
        from hi.apps.common.singleton import Singleton
        self.assertIsInstance(manager, Singleton)
        return

    def test_audio_manager_method_existence(self):
        """Test AudioManager has expected methods - critical API consistency."""
        manager = AudioManager()
        
        # Should have public interface methods
        self.assertTrue(hasattr(manager, 'get_audio_map'))
        self.assertTrue(callable(manager.get_audio_map))
        return

    def test_audio_manager_audio_map_generation(self):
        """Test audio map generation - critical for UI audio functionality."""
        manager = AudioManager()
        manager.ensure_initialized()
        
        audio_map = manager.get_audio_map()
        
        # Should return a dictionary
        self.assertIsInstance(audio_map, dict)
        
        # Should have entries for the available audio signals
        # (exact content depends on settings, but should not be empty)
        self.assertGreater(len(audio_map), 0)
        return

    def test_audio_manager_audio_mixin_integration(self):
        """Test AudioMixin integration - critical for ease of use."""
        from hi.apps.audio.audio_mixins import AudioMixin
        
        mixin = AudioMixin()
        manager = mixin.audio_manager()
        
        # Should return the same singleton instance
        direct_manager = AudioManager()
        self.assertIs(manager, direct_manager)
        return
