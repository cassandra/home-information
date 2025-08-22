import logging

from hi.apps.audio.audio_manager import AudioManager
from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.audio.settings import AudioSetting
from hi.testing.base_test_case import BaseTestCase

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

    def test_console_audio_configuration_independence(self):
        """Test that console audio can be configured independently from alarm audio."""
        # Console signals should have distinct settings from alarm signals
        console_warning_setting = AudioSignal.CONSOLE_WARNING.audio_setting
        console_info_setting = AudioSignal.CONSOLE_INFO.audio_setting
        
        event_warning_setting = AudioSignal.EVENT_WARNING.audio_setting
        weather_info_setting = AudioSignal.WEATHER_INFO.audio_setting
        
        # Console settings should be distinct
        self.assertNotEqual(console_warning_setting, event_warning_setting)
        self.assertNotEqual(console_info_setting, weather_info_setting)
        self.assertNotEqual(console_warning_setting, console_info_setting)
        return

    def test_console_audio_integration_with_audio_manager(self):
        """Test that console audio integrates properly with audio manager."""
        manager = AudioManager()
        manager.ensure_initialized()
        audio_map = manager.get_audio_map()
        
        # Console signals should be available for configuration
        # They may or may not be in the map depending on settings, but that's fine
        self.assertIsInstance(audio_map, dict)
        
        # If console signals are configured, they should have valid URLs
        if 'ConsoleWarning' in audio_map:
            self.assertTrue(audio_map['ConsoleWarning'].startswith('/static/audio/'))
        if 'ConsoleInfo' in audio_map:
            self.assertTrue(audio_map['ConsoleInfo'].startswith('/static/audio/'))
        return

    def test_console_audio_labels_for_frontend_integration(self):
        """Test that console signal labels work for frontend JavaScript integration."""
        # Labels should be consistent for frontend use
        warning_label = AudioSignal.CONSOLE_WARNING.label
        info_label = AudioSignal.CONSOLE_INFO.label
        
        # Should be distinct and properly formatted for JS
        self.assertEqual(warning_label, 'ConsoleWarning')
        self.assertEqual(info_label, 'ConsoleInfo')
        self.assertNotEqual(warning_label, info_label)
        
        # Should not contain spaces or special characters that would break JS
        self.assertNotIn(' ', warning_label)
        self.assertNotIn(' ', info_label)
        return
