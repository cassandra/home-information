import logging

from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.audio.settings import AudioSetting
from hi.tests.base_test_case import BaseTestCase

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

    def test_audio_signal_completeness_with_alarm_levels(self):
        """Test AudioSignal covers all relevant AlarmLevels for both event and weather - critical for complete coverage."""
        # Should have mappings for all non-NONE alarm levels for both event and weather
        event_mapped_levels = []
        weather_mapped_levels = []
        
        for alarm_level in AlarmLevel:
            if alarm_level == AlarmLevel.NONE:
                continue
                
            event_signal = AudioSignal.from_alarm_attributes(alarm_level, AlarmSource.EVENT, None)
            weather_signal = AudioSignal.from_alarm_attributes(alarm_level, AlarmSource.WEATHER, None)
            
            if event_signal is not None:
                event_mapped_levels.append(alarm_level)
            if weather_signal is not None:
                weather_mapped_levels.append(alarm_level)
        
        expected_mapped_levels = [AlarmLevel.INFO, AlarmLevel.WARNING, AlarmLevel.CRITICAL]
        self.assertEqual(set(event_mapped_levels), set(expected_mapped_levels))
        self.assertEqual(set(weather_mapped_levels), set(expected_mapped_levels))
        return

    def test_audio_signal_weather_vs_event_differentiation(self):
        """Test that weather and event alerts map to different signals - critical for user customization."""
        # Same alarm level should map to different signals for weather vs event
        self.assertNotEqual(
            AudioSignal.from_alarm_attributes(AlarmLevel.INFO, AlarmSource.WEATHER, None),
            AudioSignal.from_alarm_attributes(AlarmLevel.INFO, AlarmSource.EVENT, None)
        )
        self.assertNotEqual(
            AudioSignal.from_alarm_attributes(AlarmLevel.WARNING, AlarmSource.WEATHER, None),
            AudioSignal.from_alarm_attributes(AlarmLevel.WARNING, AlarmSource.EVENT, None)
        )
        self.assertNotEqual(
            AudioSignal.from_alarm_attributes(AlarmLevel.CRITICAL, AlarmSource.WEATHER, None),
            AudioSignal.from_alarm_attributes(AlarmLevel.CRITICAL, AlarmSource.EVENT, None)
        )
        return
