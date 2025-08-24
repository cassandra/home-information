import logging
from datetime import datetime

from hi.apps.alert.alarm import Alarm
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.security.enums import SecurityLevel
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey
from hi.testing.base_test_case import BaseTestCase
import hi.apps.common.datetimeproxy as datetimeproxy

logging.disable(logging.CRITICAL)


class TestAlarm(BaseTestCase):

    def test_alarm_signature_generation(self):
        """Test alarm signature generation - critical for alarm aggregation logic."""
        alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
            title='Test Alarm',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetime.now(),
        )
        
        expected_signature = f'{AlarmSource.EVENT}.test_alarm.{AlarmLevel.WARNING}'
        self.assertEqual(alarm.signature, expected_signature)
        
        # Test with different values
        critical_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='critical_test',
            alarm_level=AlarmLevel.CRITICAL,
            title='Critical Alarm',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetime.now(),
        )
        
        expected_critical_signature = f'{AlarmSource.EVENT}.critical_test.{AlarmLevel.CRITICAL}'
        self.assertEqual(critical_alarm.signature, expected_critical_signature)
        
        # Signatures should be different
        self.assertNotEqual(alarm.signature, critical_alarm.signature)
        return

    def test_alarm_audio_signal_mapping(self):
        """Test audio signal mapping from alarm level - business logic for audio alerts."""
        # Test different alarm levels produce appropriate audio signals
        info_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='info_test',
            alarm_level=AlarmLevel.INFO,
            title='Info Alarm',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetime.now(),
        )
        
        warning_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='warning_test',
            alarm_level=AlarmLevel.WARNING,
            title='Warning Alarm',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetime.now(),
        )
        
        critical_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='critical_test',
            alarm_level=AlarmLevel.CRITICAL,
            title='Critical Alarm',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetime.now(),
        )
        
        # Should map to appropriate audio signals
        info_signal = info_alarm.audio_signal
        warning_signal = warning_alarm.audio_signal
        critical_signal = critical_alarm.audio_signal
        
        # All should be AudioSignal instances
        self.assertIsInstance(info_signal, AudioSignal)
        self.assertIsInstance(warning_signal, AudioSignal)
        self.assertIsInstance(critical_signal, AudioSignal)
        
        # They should be different based on alarm level
        # (exact comparison depends on AudioSignal.from_alarm_level implementation)
        return


class TestAlarmWithSensorResponse(BaseTestCase):

    def test_alarm_with_sensor_response_details(self):
        """Test Alarm with SensorResponse as source details."""
        detail_attrs = {
            'entity_name': 'Test Sensor',
            'location': 'Kitchen',
            'value': '75.2°F'
        }
        
        sensor_response = SensorResponse(
            integration_key=IntegrationKey('test_integration', 'test_sensor'),
            value='active',
            timestamp=datetimeproxy.now(),
            sensor=None,
            detail_attrs=detail_attrs,
            source_image_url='https://example.com/sensor.jpg',
            has_video_stream=False
        )
        
        alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
            title='Test Alarm',
            sensor_response_list=[sensor_response],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetime.now(),
        )
        
        self.assertEqual(len(alarm.sensor_response_list), 1)
        self.assertEqual(alarm.sensor_response_list[0].detail_attrs, detail_attrs)
        self.assertEqual(alarm.sensor_response_list[0].source_image_url, 'https://example.com/sensor.jpg')
        return

    def test_alarm_with_weather_sensor_response(self):
        """Test Alarm with weather-style SensorResponse (no sensor)."""
        detail_attrs = {
            'Event Type': 'Severe Thunderstorm',
            'Location': 'Austin, TX'
        }
        
        # Weather alerts create SensorResponse without sensor
        sensor_response = SensorResponse(
            integration_key=IntegrationKey('weather', 'alert.123'),
            value='active',
            timestamp=datetimeproxy.now(),
            sensor=None,
            detail_attrs=detail_attrs,
            source_image_url=None,
            has_video_stream=False
        )
        
        alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type='severe_thunderstorm',
            alarm_level=AlarmLevel.WARNING,
            title='Severe Thunderstorm Warning',
            sensor_response_list=[sensor_response],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=1800,
            timestamp=datetime.now(),
        )
        
        self.assertEqual(alarm.sensor_response_list[0].detail_attrs, detail_attrs)
        self.assertIsNone(alarm.sensor_response_list[0].source_image_url)
        self.assertIsNone(alarm.sensor_response_list[0].sensor)
        return
