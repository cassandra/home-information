import logging
from unittest.mock import patch

from django.utils import timezone

from hi.apps.alert.alert import Alert
from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlertViewUrl(BaseTestCase):
    """Test Alert model's view URL generation - high-value business logic."""

    def test_event_alarm_with_sensor_id_generates_camera_url(self):
        """Test EVENT alarms with sensor_id generate proper camera URLs - core functionality."""
        # Create alarm with sensor details
        source_details = AlarmSourceDetails(
            detail_attrs={'location': 'Front Door'},
            image_url=None,
            sensor_id='cam_123'
        )
        
        event_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Motion detected at Front Door',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()
        )
        
        alert = Alert(event_alarm)
        
        # Mock at system boundary (django.urls.reverse)
        with patch('django.urls.reverse') as mock_reverse:
            mock_reverse.return_value = '/console/sensor/video_stream/cam_123/'
            
            view_url = alert.get_view_url()
            
            # Test actual return value (behavior)
            self.assertEqual(view_url, '/console/sensor/video_stream/cam_123/')
            # Verify correct URL pattern is used
            mock_reverse.assert_called_once_with(
                'console_sensor_video_stream',
                kwargs={'sensor_id': 'cam_123'}
            )

    def test_event_alarm_without_sensor_id_returns_none(self):
        """Test EVENT alarms without sensor_id return None - error handling."""
        source_details = AlarmSourceDetails(
            detail_attrs={'location': 'Front Door'},  # No sensor_id
            image_url=None
        )
        
        event_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Motion detected at Front Door',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()
        )
        
        alert = Alert(event_alarm)
        view_url = alert.get_view_url()
        
        # Test actual business logic result
        self.assertIsNone(view_url)

    def test_weather_alarm_returns_none(self):
        """Test WEATHER alarms return None - business logic for unsupported types."""
        source_details = AlarmSourceDetails(
            detail_attrs={'weather_type': 'tornado', 'severity': 'warning'},
            image_url=None
        )
        
        weather_alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type='tornado_warning',
            alarm_level=AlarmLevel.CRITICAL,
            title='Tornado Warning for Area',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=1800,
            timestamp=timezone.now()
        )
        
        alert = Alert(weather_alarm)
        view_url = alert.get_view_url()
        
        # Test business rule: WEATHER alarms not supported yet
        self.assertIsNone(view_url)

    def test_url_generation_exception_handling(self):
        """Test graceful handling of URL generation failures - error resilience."""
        source_details = AlarmSourceDetails(
            detail_attrs={},
            image_url=None,
            sensor_id='invalid_sensor'
        )
        
        event_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Test Motion',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()
        )
        
        alert = Alert(event_alarm)
        
        # Mock system boundary to simulate failure
        with patch('django.urls.reverse') as mock_reverse:
            mock_reverse.side_effect = Exception("URL pattern not found")
            
            view_url = alert.get_view_url()
            
            # Test error handling behavior: should return None on failure
            self.assertIsNone(view_url)

    def test_multiple_source_details_uses_first_sensor_id(self):
        """Test business logic for multiple source details - uses first valid sensor_id."""
        # Create multiple source details, first without sensor_id, second with
        source_details_1 = AlarmSourceDetails(
            detail_attrs={'location': 'Area A'},  # No sensor_id
            image_url=None
        )
        source_details_2 = AlarmSourceDetails(
            detail_attrs={'location': 'Area B'},
            image_url=None,
            sensor_id='cam_456'
        )
        
        event_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Motion detected',
            source_details_list=[source_details_1, source_details_2],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()
        )
        
        alert = Alert(event_alarm)
        
        with patch('django.urls.reverse') as mock_reverse:
            mock_reverse.return_value = '/console/sensor/video_stream/cam_456/'
            
            view_url = alert.get_view_url()
            
            # Test business logic: should find first valid sensor_id
            self.assertEqual(view_url, '/console/sensor/video_stream/cam_456/')
            mock_reverse.assert_called_once_with(
                'console_sensor_video_stream',
                kwargs={'sensor_id': 'cam_456'}
            )
