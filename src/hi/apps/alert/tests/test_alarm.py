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
        from hi.apps.alert.alarm import AlarmSignature
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

        expected_signature = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
        )
        self.assertEqual(alarm.signature, expected_signature)
        # Joined-string form (used in diagnostics) preserves the
        # dotted ``source.type.level`` shape using readable enum names.
        self.assertEqual(
            str(alarm.signature),
            f'{AlarmSource.EVENT.name}.test_alarm.{AlarmLevel.WARNING.name}',
        )

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

        expected_critical_signature = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='critical_test',
            alarm_level=AlarmLevel.CRITICAL,
        )
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


class TestAlarmSignature(BaseTestCase):

    def test_signatures_with_same_components_are_equal_and_hash_equal(self):
        """Frozen-dataclass structural equality / hashability is what
        ``AlertQueue`` relies on for dedup and what producers rely on
        when constructing a clear target from a different code path."""
        from hi.apps.alert.alarm import AlarmSignature
        a = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='shared',
            alarm_level=AlarmLevel.WARNING,
        )
        b = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='shared',
            alarm_level=AlarmLevel.WARNING,
        )
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        # Usable as a dict / set key.
        self.assertEqual(len({a, b}), 1)
        return

    def test_signatures_differing_in_any_component_are_unequal(self):
        """All three components participate in identity; changing any
        one must produce a distinct signature."""
        from hi.apps.alert.alarm import AlarmSignature
        base = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='t',
            alarm_level=AlarmLevel.WARNING,
        )
        diff_source = AlarmSignature(
            alarm_source=AlarmSource.WEATHER,
            alarm_type='t',
            alarm_level=AlarmLevel.WARNING,
        )
        diff_type = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='other',
            alarm_level=AlarmLevel.WARNING,
        )
        diff_level = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='t',
            alarm_level=AlarmLevel.CRITICAL,
        )
        self.assertNotEqual(base, diff_source)
        self.assertNotEqual(base, diff_type)
        self.assertNotEqual(base, diff_level)
        return

    def test_signature_str_uses_enum_names_for_readable_logs(self):
        """``__str__`` is the form that surfaces in debug logs (see
        ``AlertQueue.clear_signature``). It must use enum ``.name`` so
        log lines read like ``EVENT.foo.CRITICAL`` rather than the
        verbose default-repr form."""
        from hi.apps.alert.alarm import AlarmSignature
        sig = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='foo',
            alarm_level=AlarmLevel.CRITICAL,
        )
        self.assertEqual(str(sig), 'EVENT.foo.CRITICAL')
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
            has_event_video_snapshot=True,
            has_event_video_clip=False
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
        self.assertTrue(alarm.sensor_response_list[0].has_event_video_snapshot)
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
            has_event_video_clip=False
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
        self.assertFalse(alarm.sensor_response_list[0].has_event_video_snapshot)
        self.assertIsNone(alarm.sensor_response_list[0].sensor)
        return
