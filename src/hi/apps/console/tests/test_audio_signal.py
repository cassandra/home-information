import logging

from hi.apps.alert.enums import AlarmLevel
from hi.apps.console.audio_signal import AudioSignal
from hi.apps.console.settings import ConsoleSetting
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAudioSignal(BaseTestCase):

    def test_audio_signal_alarm_level_mapping(self):
        """Test from_alarm_level mapping logic - critical for alert audio functionality."""
        # Test valid mappings
        self.assertEqual(AudioSignal.from_alarm_level(AlarmLevel.INFO), AudioSignal.INFO)
        self.assertEqual(AudioSignal.from_alarm_level(AlarmLevel.WARNING), AudioSignal.WARNING)
        self.assertEqual(AudioSignal.from_alarm_level(AlarmLevel.CRITICAL), AudioSignal.CRITICAL)
        
        # Test unmapped alarm level
        self.assertIsNone(AudioSignal.from_alarm_level(AlarmLevel.NONE))
        return

    def test_audio_signal_console_setting_mapping(self):
        """Test console setting association - critical for audio configuration."""
        # Each AudioSignal should have proper console setting
        self.assertEqual(AudioSignal.INFO.console_setting, ConsoleSetting.CONSOLE_INFO_AUDIO_FILE)
        self.assertEqual(AudioSignal.WARNING.console_setting, ConsoleSetting.CONSOLE_WARNING_AUDIO_FILE)
        self.assertEqual(AudioSignal.CRITICAL.console_setting, ConsoleSetting.CONSOLE_CRITICAL_AUDIO_FILE)
        return

    def test_audio_signal_labels(self):
        """Test AudioSignal labels - important for UI display."""
        self.assertEqual(AudioSignal.INFO.label, 'Info')
        self.assertEqual(AudioSignal.WARNING.label, 'Warning')
        self.assertEqual(AudioSignal.CRITICAL.label, 'Critical')
        return

    def test_audio_signal_completeness_with_alarm_levels(self):
        """Test AudioSignal covers all relevant AlarmLevels - critical for complete alert coverage."""
        # Should have mappings for all non-NONE alarm levels
        mapped_levels = []
        for alarm_level in AlarmLevel:
            if alarm_level == AlarmLevel.NONE:
                continue
            audio_signal = AudioSignal.from_alarm_level(alarm_level)
            if audio_signal is not None:
                mapped_levels.append(alarm_level)
        
        expected_mapped_levels = [AlarmLevel.INFO, AlarmLevel.WARNING, AlarmLevel.CRITICAL]
        self.assertEqual(set(mapped_levels), set(expected_mapped_levels))
        return
