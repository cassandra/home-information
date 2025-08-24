import logging

from hi.apps.alert.alarm import Alarm
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.weather.enums import WeatherEventType
from hi.integrations.transient_models import IntegrationKey
from hi.testing.base_test_case import BaseTestCase

import hi.apps.common.datetimeproxy as datetimeproxy

logging.disable(logging.CRITICAL)


class TestTornadoAudio(BaseTestCase):
    """Tests for tornado-specific audio handling."""

    def test_tornado_gets_special_audio_regardless_of_level(self):
        """Test that tornado alerts get tornado-specific audio signal regardless of alarm level."""
        # Test tornado alerts at different levels all get tornado-specific signal
        tornado_levels = [AlarmLevel.INFO, AlarmLevel.WARNING, AlarmLevel.CRITICAL]
        
        for alarm_level in tornado_levels:
            with self.subTest(level=alarm_level):
                tornado_alarm = Alarm(
                    alarm_source=AlarmSource.WEATHER,
                    alarm_type=WeatherEventType.TORNADO.name,  # This is how weather alerts set alarm_type
                    alarm_level=alarm_level,
                    title=f'Tornado {alarm_level.label} Alert',
                    sensor_response_list=[SensorResponse(integration_key=IntegrationKey("test", "audio_test"), value="active", timestamp=datetimeproxy.now(), sensor=None, detail_attrs={'location': 'Austin, TX'}, source_image_url=None, has_video_stream=False)],
                    security_level=SecurityLevel.OFF,
                    alarm_lifetime_secs=1800,
                    timestamp=datetimeproxy.now(),
                )
                
                # Should always get tornado-specific audio signal
                audio_signal = tornado_alarm.audio_signal
                self.assertEqual(audio_signal, AudioSignal.WEATHER_TORNADO)
                self.assertEqual(audio_signal.label, 'TornadoAlert')
        return

    def test_other_weather_alerts_get_level_based_audio(self):
        """Test that non-tornado weather alerts still get level-based audio signals."""
        # Test that severe thunderstorm alerts get level-based signals
        severe_storm_alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type=WeatherEventType.SEVERE_THUNDERSTORM.name,
            alarm_level=AlarmLevel.WARNING,
            title='Severe Thunderstorm Warning',
            sensor_response_list=[SensorResponse(integration_key=IntegrationKey("test", "audio_test"), value="active", timestamp=datetimeproxy.now(), sensor=None, detail_attrs={'location': 'Austin, TX'}, source_image_url=None, has_video_stream=False)],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=1800,
            timestamp=datetimeproxy.now(),
        )
        
        # Should get weather warning signal, not tornado signal
        audio_signal = severe_storm_alarm.audio_signal
        self.assertEqual(audio_signal, AudioSignal.WEATHER_WARNING)
        self.assertNotEqual(audio_signal, AudioSignal.WEATHER_TORNADO)
        return

    def test_tornado_audio_signal_enum_method_mapping(self):
        """Test that the enum mapping method correctly handles tornado types."""
        # Direct method testing
        tornado_signal = AudioSignal.from_alarm_attributes(
            AlarmLevel.INFO, 
            AlarmSource.WEATHER, 
            WeatherEventType.TORNADO.name
        )
        self.assertEqual(tornado_signal, AudioSignal.WEATHER_TORNADO)
        
        # Test different levels all return tornado signal
        for level in [AlarmLevel.INFO, AlarmLevel.WARNING, AlarmLevel.CRITICAL]:
            signal = AudioSignal.from_alarm_attributes(
                level, 
                AlarmSource.WEATHER, 
                WeatherEventType.TORNADO.name
            )
            self.assertEqual(signal, AudioSignal.WEATHER_TORNADO)
        return

    def test_non_tornado_weather_events_use_level_based_mapping(self):
        """Test that non-tornado weather events still use level-based mapping."""
        # Test severe thunderstorm
        severe_storm_signal = AudioSignal.from_alarm_attributes(
            AlarmLevel.WARNING, 
            AlarmSource.WEATHER, 
            WeatherEventType.SEVERE_THUNDERSTORM.name
        )
        self.assertEqual(severe_storm_signal, AudioSignal.WEATHER_WARNING)
        
        # Test hurricane
        hurricane_signal = AudioSignal.from_alarm_attributes(
            AlarmLevel.CRITICAL, 
            AlarmSource.WEATHER, 
            WeatherEventType.HURRICANE.name
        )
        self.assertEqual(hurricane_signal, AudioSignal.WEATHER_CRITICAL)
        return

    def test_event_alerts_unaffected_by_tornado_logic(self):
        """Test that event alerts are unaffected by tornado-specific logic."""
        # Event alerts should still get event-based signals
        event_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='DEVICE_FAILURE',
            alarm_level=AlarmLevel.CRITICAL,
            title='Device Failure',
            sensor_response_list=[SensorResponse(integration_key=IntegrationKey("test", "audio_test"), value="active", timestamp=datetimeproxy.now(), sensor=None, detail_attrs={'device': 'Sensor-01'}, source_image_url=None, has_video_stream=False)],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=3600,
            timestamp=datetimeproxy.now(),
        )
        
        audio_signal = event_alarm.audio_signal
        self.assertEqual(audio_signal, AudioSignal.EVENT_CRITICAL)
        self.assertNotEqual(audio_signal, AudioSignal.WEATHER_TORNADO)
        return
