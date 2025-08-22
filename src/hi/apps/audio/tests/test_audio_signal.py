import logging

from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.audio.settings import AudioSetting
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAudioSignal(BaseTestCase):

    def test_audio_signal_audio_setting_mapping(self):
        """Test audio setting association - critical for audio configuration."""
        # Each AudioSignal should have proper audio setting
        self.assertEqual(AudioSignal.EVENT_INFO.audio_setting, AudioSetting.EVENT_INFO_AUDIO_FILE)
        self.assertEqual(AudioSignal.EVENT_WARNING.audio_setting, AudioSetting.EVENT_WARNING_AUDIO_FILE)
        self.assertEqual(AudioSignal.EVENT_CRITICAL.audio_setting, AudioSetting.EVENT_CRITICAL_AUDIO_FILE)
        
        self.assertEqual(AudioSignal.WEATHER_INFO.audio_setting, AudioSetting.WEATHER_INFO_AUDIO_FILE)
        self.assertEqual(AudioSignal.WEATHER_WARNING.audio_setting, AudioSetting.WEATHER_WARNING_AUDIO_FILE)
        self.assertEqual(AudioSignal.WEATHER_CRITICAL.audio_setting, AudioSetting.WEATHER_CRITICAL_AUDIO_FILE)
        
        # Special weather signals
        self.assertEqual(AudioSignal.WEATHER_TORNADO.audio_setting, AudioSetting.WEATHER_TORNADO_AUDIO_FILE)
        return

    def test_audio_signal_labels(self):
        """Test AudioSignal labels - important for UI display."""
        # Event signals
        self.assertEqual(AudioSignal.EVENT_INFO.label, 'EventInfo')
        self.assertEqual(AudioSignal.EVENT_WARNING.label, 'EventWarning')
        self.assertEqual(AudioSignal.EVENT_CRITICAL.label, 'EventCritical')
        
        # Weather signals
        self.assertEqual(AudioSignal.WEATHER_INFO.label, 'WeatherInfo')
        self.assertEqual(AudioSignal.WEATHER_WARNING.label, 'WeatherWarning')
        self.assertEqual(AudioSignal.WEATHER_CRITICAL.label, 'WeatherCritical')
        
        # Special weather signals
        self.assertEqual(AudioSignal.WEATHER_TORNADO.label, 'TornadoAlert')
        
        # Console signals
        self.assertEqual(AudioSignal.CONSOLE_WARNING.label, 'ConsoleWarning')
        self.assertEqual(AudioSignal.CONSOLE_INFO.label, 'ConsoleInfo')
        return

    def test_tornado_weather_gets_special_audio_signal(self):
        """Test that tornado weather events get special tornado audio signal regardless of level."""
        # Tornado should get special signal regardless of alarm level
        test_levels = [AlarmLevel.INFO, AlarmLevel.WARNING, AlarmLevel.CRITICAL]
        
        for alarm_level in test_levels:
            signal = AudioSignal.from_alarm_attributes(
                alarm_level, 
                AlarmSource.WEATHER, 
                'TORNADO'  # Use string directly as that's what's used in the implementation
            )
            self.assertEqual(signal, AudioSignal.WEATHER_TORNADO)
            self.assertEqual(signal.audio_setting, AudioSetting.WEATHER_TORNADO_AUDIO_FILE)
        return

    def test_non_tornado_weather_uses_level_based_mapping(self):
        """Test that non-tornado weather events use alarm level based mapping."""
        # Non-tornado weather should use level-based mapping
        signal = AudioSignal.from_alarm_attributes(
            AlarmLevel.WARNING, 
            AlarmSource.WEATHER, 
            'SEVERE_THUNDERSTORM'  # Use string directly
        )
        self.assertEqual(signal, AudioSignal.WEATHER_WARNING)
        
        signal = AudioSignal.from_alarm_attributes(
            AlarmLevel.CRITICAL, 
            AlarmSource.WEATHER, 
            'HURRICANE'  # Use string directly
        )
        self.assertEqual(signal, AudioSignal.WEATHER_CRITICAL)
        return

    def test_weather_vs_event_differentiation_allows_custom_audio(self):
        """Test that weather and event alerts map to different signals for customization."""
        # Same alarm level should map to different signals for weather vs event
        weather_info = AudioSignal.from_alarm_attributes(AlarmLevel.INFO, AlarmSource.WEATHER, None)
        event_info = AudioSignal.from_alarm_attributes(AlarmLevel.INFO, AlarmSource.EVENT, None)
        
        weather_warning = AudioSignal.from_alarm_attributes(AlarmLevel.WARNING, AlarmSource.WEATHER, None)
        event_warning = AudioSignal.from_alarm_attributes(AlarmLevel.WARNING, AlarmSource.EVENT, None)
        
        # Should be different signals
        self.assertNotEqual(weather_info, event_info)
        self.assertNotEqual(weather_warning, event_warning)
        
        # Should have different audio settings for separate configuration
        self.assertNotEqual(weather_info.audio_setting, event_info.audio_setting)
        self.assertNotEqual(weather_warning.audio_setting, event_warning.audio_setting)
        return

    def test_console_signals_are_available(self):
        """Test that console audio signals are available for console functionality."""
        # Console signals should exist and have proper settings
        self.assertEqual(AudioSignal.CONSOLE_WARNING.audio_setting, AudioSetting.CONSOLE_WARNING_AUDIO_FILE)
        self.assertEqual(AudioSignal.CONSOLE_INFO.audio_setting, AudioSetting.CONSOLE_INFO_AUDIO_FILE)
        
        # Should have distinct labels for frontend use
        self.assertEqual(AudioSignal.CONSOLE_WARNING.label, 'ConsoleWarning')
        self.assertEqual(AudioSignal.CONSOLE_INFO.label, 'ConsoleInfo')
        return

    def test_invalid_alarm_level_returns_none(self):
        """Test that invalid alarm levels return None gracefully."""
        signal = AudioSignal.from_alarm_attributes(AlarmLevel.NONE, AlarmSource.EVENT, None)
        self.assertIsNone(signal)
        
        # Test with None alarm level
        signal = AudioSignal.from_alarm_attributes(None, AlarmSource.EVENT, None)
        self.assertIsNone(signal)
        return
