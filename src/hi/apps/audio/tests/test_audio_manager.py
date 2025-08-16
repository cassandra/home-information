import logging

from hi.apps.audio.audio_manager import AudioManager
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAudioManager(BaseTestCase):

    def test_audio_manager_singleton_ensures_consistent_state(self):
        """Test that singleton behavior maintains consistent state across instances."""
        manager1 = AudioManager()
        manager1.ensure_initialized()
        
        manager2 = AudioManager()
        
        # Both should reference same instance with same state
        self.assertIs(manager1, manager2)
        self.assertTrue(manager2._was_initialized)
        return

    def test_initialization_ensures_proper_state(self):
        """Test that initialization properly sets up manager state."""
        manager = AudioManager()
        
        # Ensure initialization has been called
        manager.ensure_initialized()
        
        # Should be properly initialized
        self.assertTrue(manager._was_initialized)
        
        # Should have a valid audio map
        audio_map = manager.get_audio_map()
        self.assertIsInstance(audio_map, dict)
        return

    def test_audio_map_returns_dict_with_audio_urls(self):
        """Test that audio map building returns valid dictionary structure."""
        manager = AudioManager()
        manager.ensure_initialized()
        audio_map = manager.get_audio_map()
        
        # Should return a dictionary
        self.assertIsInstance(audio_map, dict)
        
        # All values should be valid audio URLs if they exist
        for signal_name, url in audio_map.items():
            self.assertIsInstance(signal_name, str)
            self.assertIsInstance(url, str)
            if url:  # If URL is not empty
                self.assertTrue(url.startswith('/static/audio/'))
                self.assertTrue(url.endswith('.wav'))
        return

    def test_multiple_initialization_calls_are_safe(self):
        """Test that multiple initialization calls don't cause issues."""
        manager = AudioManager()
        
        # Multiple calls should be safe
        manager.ensure_initialized()
        manager.ensure_initialized()
        manager.ensure_initialized()
        
        # Should still be properly initialized
        self.assertTrue(manager._was_initialized)
        
        # Should still return valid audio map
        audio_map = manager.get_audio_map()
        self.assertIsInstance(audio_map, dict)
        return

    def test_settings_change_reload_functionality(self):
        """Test that settings change handling works correctly."""
        manager = AudioManager()
        manager.ensure_initialized()
        
        # Simulate settings change by calling reload directly
        manager._reload_audio_map()
        
        # Should still have valid audio map after reload
        reloaded_map = manager.get_audio_map()
        self.assertIsInstance(reloaded_map, dict)
        return

    def test_audio_mixin_provides_manager_access(self):
        """Test that AudioMixin provides convenient access to audio manager."""
        from hi.apps.audio.audio_mixins import AudioMixin
        
        mixin = AudioMixin()
        manager = mixin.audio_manager()
        
        # Should return the singleton instance
        direct_manager = AudioManager()
        self.assertIs(manager, direct_manager)
        
        # Should be initialized and functional
        manager.ensure_initialized()
        audio_map = manager.get_audio_map()
        self.assertIsInstance(audio_map, dict)
        return
