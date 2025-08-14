import logging

from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.security.enums import SecurityLevel
from hi.tests.base_test_case import BaseTestCase

import hi.apps.common.datetimeproxy as datetimeproxy

logging.disable(logging.CRITICAL)


class TestAudioIntegration(BaseTestCase):
    """Integration tests for the enhanced audio system with weather vs system differentiation."""

    def test_weather_alert_gets_weather_specific_audio(self):
        """Test that weather alerts get weather-specific audio signals."""
        # Create a weather alarm (non-tornado to test general weather level-based mapping)
        weather_alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type='SEVERE_THUNDERSTORM',
            alarm_level=AlarmLevel.CRITICAL,
            title='Severe Thunderstorm Warning',
            source_details_list=[AlarmSourceDetails(detail_attrs={'location': 'Austin, TX'})],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=1800,
            timestamp=datetimeproxy.now(),
        )
        
        # Should get weather-specific audio signal
        audio_signal = weather_alarm.audio_signal
        self.assertEqual(audio_signal, AudioSignal.WEATHER_CRITICAL)
        self.assertIn('Weather', audio_signal.label)
        return

    def test_tornado_alert_gets_tornado_specific_audio(self):
        """Test that tornado alerts get tornado-specific audio signals."""
        # Create a tornado alarm
        tornado_alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type='TORNADO',
            alarm_level=AlarmLevel.CRITICAL,
            title='Tornado Warning',
            source_details_list=[AlarmSourceDetails(detail_attrs={'location': 'Austin, TX'})],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=1800,
            timestamp=datetimeproxy.now(),
        )
        
        # Should get tornado-specific audio signal (not general weather critical)
        audio_signal = tornado_alarm.audio_signal
        self.assertEqual(audio_signal, AudioSignal.WEATHER_TORNADO)
        self.assertEqual(audio_signal.label, 'TornadoAlert')
        return

    def test_event_alert_gets_event_specific_audio(self):
        """Test that event alerts get event-specific audio signals."""
        # Create a system alarm
        system_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='DEVICE_FAILURE',
            alarm_level=AlarmLevel.CRITICAL,
            title='Device Failure',
            source_details_list=[AlarmSourceDetails(detail_attrs={'device': 'Sensor-01'})],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=3600,
            timestamp=datetimeproxy.now(),
        )
        
        # Should get event-specific audio signal
        audio_signal = system_alarm.audio_signal
        self.assertEqual(audio_signal, AudioSignal.EVENT_CRITICAL)
        self.assertIn('Event', audio_signal.label)
        return

    def test_same_level_different_source_gets_different_audio(self):
        """Test that same alarm level with different sources get different audio signals."""
        # Create weather and system alarms with same level
        weather_alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type='SEVERE_THUNDERSTORM',
            alarm_level=AlarmLevel.WARNING,
            title='Severe Thunderstorm Warning',
            source_details_list=[AlarmSourceDetails(detail_attrs={'location': 'Austin, TX'})],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=1800,
            timestamp=datetimeproxy.now(),
        )
        
        system_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='HIGH_TEMP',
            alarm_level=AlarmLevel.WARNING,
            title='High Temperature Alert',
            source_details_list=[AlarmSourceDetails(detail_attrs={'sensor': 'Temp-01'})],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=3600,
            timestamp=datetimeproxy.now(),
        )
        
        # Should get different audio signals
        weather_audio = weather_alarm.audio_signal
        event_audio = system_alarm.audio_signal
        
        self.assertNotEqual(weather_audio, event_audio)
        self.assertEqual(weather_audio, AudioSignal.WEATHER_WARNING)
        self.assertEqual(event_audio, AudioSignal.EVENT_WARNING)
        return

    def test_audio_settings_mapping_works(self):
        """Test that audio signals correctly map to their audio settings."""
        # Create alarms of different types and levels
        test_cases = [
            (AlarmSource.WEATHER, AlarmLevel.INFO, AudioSignal.WEATHER_INFO),
            (AlarmSource.WEATHER, AlarmLevel.WARNING, AudioSignal.WEATHER_WARNING),
            (AlarmSource.WEATHER, AlarmLevel.CRITICAL, AudioSignal.WEATHER_CRITICAL),
            (AlarmSource.EVENT, AlarmLevel.INFO, AudioSignal.EVENT_INFO),
            (AlarmSource.EVENT, AlarmLevel.WARNING, AudioSignal.EVENT_WARNING),
            (AlarmSource.EVENT, AlarmLevel.CRITICAL, AudioSignal.EVENT_CRITICAL),
        ]
        
        for alarm_source, alarm_level, expected_signal in test_cases:
            with self.subTest(source=alarm_source, level=alarm_level):
                alarm = Alarm(
                    alarm_source=alarm_source,
                    alarm_type='TEST',
                    alarm_level=alarm_level,
                    title='Test Alarm',
                    source_details_list=[AlarmSourceDetails(detail_attrs={'test': 'data'})],
                    security_level=SecurityLevel.OFF,
                    alarm_lifetime_secs=3600,
                    timestamp=datetimeproxy.now(),
                )
                
                # Should get expected audio signal
                audio_signal = alarm.audio_signal
                self.assertEqual(audio_signal, expected_signal)
                
                # Should have corresponding audio setting
                self.assertIsNotNone(audio_signal.audio_setting)
        return