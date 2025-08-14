import logging

from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.audio.settings import AudioSetting
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestConsoleAudio(BaseTestCase):
    """Tests for console-specific audio functionality."""

    def test_console_audio_signals_exist(self):
        """Test that console audio signals are properly defined."""
        # Console signals should exist
        self.assertTrue(hasattr(AudioSignal, 'CONSOLE_WARNING'))
        self.assertTrue(hasattr(AudioSignal, 'CONSOLE_INFO'))
        
        # Should have proper labels
        self.assertEqual(AudioSignal.CONSOLE_WARNING.label, 'ConsoleWarning')
        self.assertEqual(AudioSignal.CONSOLE_INFO.label, 'ConsoleInfo')
        return

    def test_console_audio_settings_mapping(self):
        """Test that console audio signals map to correct settings."""
        # Console signals should map to console settings
        self.assertEqual(AudioSignal.CONSOLE_WARNING.audio_setting, AudioSetting.CONSOLE_WARNING_AUDIO_FILE)
        self.assertEqual(AudioSignal.CONSOLE_INFO.audio_setting, AudioSetting.CONSOLE_INFO_AUDIO_FILE)
        return

    def test_console_audio_in_audio_map(self):
        """Test that console signals appear in the audio manager's audio map."""
        from hi.apps.audio.audio_manager import AudioManager
        
        manager = AudioManager()
        manager.ensure_initialized()
        audio_map = manager.get_audio_map()
        
        # Console signals should be in the audio map
        self.assertIn('ConsoleWarning', audio_map)
        self.assertIn('ConsoleInfo', audio_map)
        
        # Should have valid URLs
        self.assertTrue(audio_map['ConsoleWarning'].startswith('/static/audio/'))
        self.assertTrue(audio_map['ConsoleInfo'].startswith('/static/audio/'))
        return

    def test_console_signal_names_match_javascript_constants(self):
        """Test that signal names match the JavaScript constants."""
        # These should match the constants in audio.js
        expected_warning_name = 'ConsoleWarning'
        expected_info_name = 'ConsoleInfo'
        
        self.assertEqual(AudioSignal.CONSOLE_WARNING.label, expected_warning_name)
        self.assertEqual(AudioSignal.CONSOLE_INFO.label, expected_info_name)
        return