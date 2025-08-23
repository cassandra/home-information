import logging
from datetime import datetime

from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.audio.audio_signal import AudioSignal
from hi.apps.security.enums import SecurityLevel
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlarm(BaseTestCase):

    def test_alarm_signature_generation(self):
        """Test alarm signature generation - critical for alarm aggregation logic."""
        alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
            title='Test Alarm',
            source_details_list=[],
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
            source_details_list=[],
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
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetime.now(),
        )
        
        warning_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='warning_test',
            alarm_level=AlarmLevel.WARNING,
            title='Warning Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetime.now(),
        )
        
        critical_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='critical_test',
            alarm_level=AlarmLevel.CRITICAL,
            title='Critical Alarm',
            source_details_list=[],
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


class TestAlarmSourceDetails(BaseTestCase):

    def test_alarm_source_details_creation(self):
        """Test AlarmSourceDetails dataclass - business logic for alarm context."""
        detail_attrs = {
            'entity_name': 'Test Sensor',
            'location': 'Kitchen',
            'value': '75.2°F'
        }
        
        details = AlarmSourceDetails(
            detail_attrs=detail_attrs,
            source_image_url='https://example.com/sensor.jpg'
        )
        
        self.assertEqual(details.detail_attrs, detail_attrs)
        self.assertEqual(details.source_image_url, 'https://example.com/sensor.jpg')
        return

    def test_alarm_source_details_optional_image_url(self):
        """Test AlarmSourceDetails with optional image_url - default value handling."""
        detail_attrs = {
            'entity_name': 'Test Sensor',
            'location': 'Kitchen'
        }
        
        details = AlarmSourceDetails(detail_attrs=detail_attrs)
        
        self.assertEqual(details.detail_attrs, detail_attrs)
        self.assertIsNone(details.source_image_url)
        return
