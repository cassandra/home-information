"""
Tests for WeatherAlertAlarmMapper - converting weather alerts to system alarms.
"""
import logging
from unittest.mock import patch
from datetime import datetime, timedelta

from django.utils import timezone

from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.apps.weather.enums import (
    AlertCategory,
    AlertSeverity, 
    AlertStatus,
    AlertUrgency,
    AlertCertainty,
    WeatherEventType,
)
from hi.apps.weather.transient_models import WeatherAlert
from hi.apps.weather.weather_alert_alarm_mapper import WeatherAlertAlarmMapper
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestWeatherAlertAlarmMapper(BaseTestCase):
    """Test weather alert to system alarm conversion logic."""
    
    def setUp(self):
        self.mapper = WeatherAlertAlarmMapper()
        # Use timezone-aware datetime like real NWS data
        self.base_datetime = timezone.make_aware(datetime(2024, 3, 15, 20, 0, 0), timezone.utc)
    
    def create_test_weather_alert(self, 
                                  event_type: WeatherEventType = WeatherEventType.TORNADO,
                                  severity: AlertSeverity = AlertSeverity.EXTREME,
                                  status: AlertStatus = AlertStatus.ACTUAL,
                                  urgency: AlertUrgency = AlertUrgency.IMMEDIATE,
                                  event: str = "Test Weather Event",
                                  headline: str = "Test headline",
                                  expires_hours: int = 1) -> WeatherAlert:
        """Helper to create test weather alerts."""
        return WeatherAlert(
            event_type=event_type,
            event=event,
            status=status,
            category=AlertCategory.METEOROLOGICAL,
            headline=headline,
            description="Test weather alert description for testing purposes.",
            instruction="Take appropriate action as needed.",
            affected_areas="Test County",
            effective=self.base_datetime,
            onset=self.base_datetime,
            expires=self.base_datetime + timedelta(hours=expires_hours),
            ends=self.base_datetime + timedelta(hours=expires_hours),
            severity=severity,
            certainty=AlertCertainty.OBSERVED,
            urgency=urgency,
        )
    
    def test_critical_event_types_always_create_alarms(self):
        """Test that critical event types always create alarms regardless of severity."""
        critical_types = [
            WeatherEventType.TORNADO,
            WeatherEventType.FLASH_FLOOD,
            WeatherEventType.EARTHQUAKE,
            WeatherEventType.TSUNAMI,
            WeatherEventType.EVACUATION,
            WeatherEventType.AMBER_ALERT,
        ]
        
        for event_type in critical_types:
            for severity in [ AlertSeverity.MINOR, AlertSeverity.MODERATE,
                              AlertSeverity.SEVERE, AlertSeverity.EXTREME ]:
                with self.subTest(event_type=event_type, severity=severity):
                    alert = self.create_test_weather_alert(
                        event_type=event_type,
                        severity=severity
                    )
                    
                    # Should always create alarm
                    self.assertTrue(self.mapper.should_create_alarm(alert))
                    
                    # Should get an alarm
                    alarm = self.mapper.create_alarm(alert)
                    self.assertIsNotNone(alarm)
                    self.assertEqual(alarm.alarm_source, AlarmSource.WEATHER)
                    self.assertEqual(alarm.alarm_type, event_type.name)
    
    def test_severity_dependent_events(self):
        """Test that severity-dependent events create alarms based on severity."""
        event_type = WeatherEventType.SEVERE_THUNDERSTORM
        
        # EXTREME and SEVERE should create alarms
        for severity in [AlertSeverity.EXTREME, AlertSeverity.SEVERE]:
            with self.subTest(severity=severity):
                alert = self.create_test_weather_alert(
                    event_type=event_type,
                    severity=severity
                )
                
                self.assertTrue(self.mapper.should_create_alarm(alert))
                alarm = self.mapper.create_alarm(alert)
                self.assertIsNotNone(alarm)
        
        # MODERATE with IMMEDIATE urgency should create alarm
        alert = self.create_test_weather_alert(
            event_type=event_type,
            severity=AlertSeverity.MODERATE,
            urgency=AlertUrgency.IMMEDIATE
        )
        self.assertTrue(self.mapper.should_create_alarm(alert))
        
        # MODERATE with non-immediate urgency should not create alarm
        alert = self.create_test_weather_alert(
            event_type=event_type,
            severity=AlertSeverity.MODERATE,
            urgency=AlertUrgency.EXPECTED
        )
        self.assertFalse(self.mapper.should_create_alarm(alert))
        
        # MINOR should not create alarm
        alert = self.create_test_weather_alert(
            event_type=event_type,
            severity=AlertSeverity.MINOR
        )
        self.assertFalse(self.mapper.should_create_alarm(alert))
    
    def test_informational_events_no_alarms(self):
        """Test that informational events don't create alarms."""
        informational_types = [
            WeatherEventType.TEST_MESSAGE,
            WeatherEventType.ADMINISTRATIVE,
            WeatherEventType.SPECIAL_WEATHER,
            WeatherEventType.AURORA,
            WeatherEventType.METEOR_SHOWER,
        ]
        
        for event_type in informational_types:
            with self.subTest(event_type=event_type):
                alert = self.create_test_weather_alert(
                    event_type=event_type,
                    severity=AlertSeverity.EXTREME  # Even extreme shouldn't create alarm
                )
                
                self.assertFalse(self.mapper.should_create_alarm(alert))
                alarm = self.mapper.create_alarm(alert)
                self.assertIsNone(alarm)
    
    def test_test_and_exercise_alerts_excluded(self):
        """Test that test and exercise alerts don't create alarms."""
        test_statuses = [AlertStatus.TEST, AlertStatus.EXERCISE, AlertStatus.DRAFT]
        
        for status in test_statuses:
            with self.subTest(status=status):
                alert = self.create_test_weather_alert(
                    event_type=WeatherEventType.TORNADO,  # Critical type
                    severity=AlertSeverity.EXTREME,       # Extreme severity
                    status=status                          # But test status
                )
                
                self.assertFalse(self.mapper.should_create_alarm(alert))
                alarm = self.mapper.create_alarm(alert)
                self.assertIsNone(alarm)
    
    def test_alarm_level_mapping(self):
        """Test alarm level mapping based on event type and severity."""
        # Critical event type with extreme severity -> CRITICAL
        alert = self.create_test_weather_alert(
            event_type=WeatherEventType.TORNADO,
            severity=AlertSeverity.EXTREME
        )
        self.assertEqual(self.mapper.get_alarm_level(alert), AlarmLevel.CRITICAL)
        
        # Critical event type with severe severity -> CRITICAL (still critical event)
        alert = self.create_test_weather_alert(
            event_type=WeatherEventType.TORNADO,
            severity=AlertSeverity.SEVERE
        )
        self.assertEqual(self.mapper.get_alarm_level(alert), AlarmLevel.CRITICAL)
        
        # Warning-level event with extreme severity -> CRITICAL
        alert = self.create_test_weather_alert(
            event_type=WeatherEventType.SEVERE_THUNDERSTORM,
            severity=AlertSeverity.EXTREME
        )
        self.assertEqual(self.mapper.get_alarm_level(alert), AlarmLevel.CRITICAL)
        
        # Warning-level event with severe severity -> WARNING
        alert = self.create_test_weather_alert(
            event_type=WeatherEventType.SEVERE_THUNDERSTORM,
            severity=AlertSeverity.SEVERE
        )
        self.assertEqual(self.mapper.get_alarm_level(alert), AlarmLevel.WARNING)
        
        # Info-level event with severe severity -> WARNING
        alert = self.create_test_weather_alert(
            event_type=WeatherEventType.EXTREME_HEAT,
            severity=AlertSeverity.SEVERE
        )
        self.assertEqual(self.mapper.get_alarm_level(alert), AlarmLevel.WARNING)
        
        # Info-level event with moderate severity -> INFO
        alert = self.create_test_weather_alert(
            event_type=WeatherEventType.EXTREME_HEAT,
            severity=AlertSeverity.MODERATE,
            urgency=AlertUrgency.IMMEDIATE  # Needed for moderate to create alarm
        )
        self.assertEqual(self.mapper.get_alarm_level(alert), AlarmLevel.INFO)
    
    def test_alarm_lifetime_from_expires(self):
        """Test that alarm lifetime is calculated from alert expires time."""
        # Create alert that expires in 3 hours
        alert = self.create_test_weather_alert(expires_hours=3)
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_datetime):
            lifetime = self.mapper.get_alarm_lifetime(alert)
            self.assertEqual(lifetime, 3 * 60 * 60)  # 3 hours in seconds
    
    def test_alarm_lifetime_from_event_type(self):
        """Test that alarm lifetime falls back to event type mapping."""
        # Create alert without expires time
        alert = self.create_test_weather_alert()
        alert.expires = None
        
        lifetime = self.mapper.get_alarm_lifetime(alert)
        expected_lifetime = self.mapper.EVENT_TYPE_TO_LIFETIME.get(
            WeatherEventType.TORNADO, 
            self.mapper.DEFAULT_LIFETIME_SECS
        )
        self.assertEqual(lifetime, expected_lifetime)
    
    def test_alarm_lifetime_bounds(self):
        """Test that alarm lifetime is bounded by min/max values."""
        # Test minimum bound (15 minutes)
        alert = self.create_test_weather_alert(expires_hours=0.1)  # 6 minutes
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_datetime):
            lifetime = self.mapper.get_alarm_lifetime(alert)
            self.assertEqual(lifetime, 15 * 60)  # Should be minimum 15 minutes
        
        # Test maximum bound (48 hours)  
        alert = self.create_test_weather_alert(expires_hours=72)  # 72 hours
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_datetime):
            lifetime = self.mapper.get_alarm_lifetime(alert)
            self.assertEqual(lifetime, 48 * 60 * 60)  # Should be maximum 48 hours
    
    def test_alarm_properties(self):
        """Test that created alarms have correct properties."""
        alert = self.create_test_weather_alert(
            event_type=WeatherEventType.TORNADO,
            severity=AlertSeverity.EXTREME,
            headline="Tornado Warning for Test County"
        )
        
        alarm = self.mapper.create_alarm(alert)
        
        # Verify basic properties
        self.assertEqual(alarm.alarm_source, AlarmSource.WEATHER)
        self.assertEqual(alarm.alarm_type, WeatherEventType.TORNADO.name)
        self.assertEqual(alarm.alarm_level, AlarmLevel.CRITICAL)
        self.assertEqual(alarm.title, "Tornado Warning for Test County")
        self.assertEqual(alarm.security_level, SecurityLevel.OFF)  # Applies to all security levels
        
        # Verify source details
        self.assertEqual(len(alarm.sensor_response_list), 1)
        details = alarm.sensor_response_list[0]
        self.assertIn('Event Type', details.detail_attrs)
        self.assertIn('Severity', details.detail_attrs)
        self.assertIn('Affected Areas', details.detail_attrs)
        self.assertEqual(details.detail_attrs['Event Type'], WeatherEventType.TORNADO.label)
    
    def test_multiple_alerts_processing(self):
        """Test processing multiple weather alerts."""
        alerts = [
            self.create_test_weather_alert(
                event_type=WeatherEventType.TORNADO,
                severity=AlertSeverity.EXTREME,
                headline="Tornado Warning"
            ),
            self.create_test_weather_alert(
                event_type=WeatherEventType.SEVERE_THUNDERSTORM,
                severity=AlertSeverity.SEVERE,
                headline="Severe Thunderstorm Warning"
            ),
            self.create_test_weather_alert(
                event_type=WeatherEventType.SPECIAL_WEATHER,
                severity=AlertSeverity.MINOR,
                headline="Special Weather Statement"
            ),
            self.create_test_weather_alert(
                event_type=WeatherEventType.TEST_MESSAGE,
                severity=AlertSeverity.EXTREME,
                headline="Test Message"
            ),
        ]
        
        alarms = self.mapper.create_alarms_from_weather_alerts(alerts)
        
        # Should create alarms for tornado and severe thunderstorm, but not special weather or test
        self.assertEqual(len(alarms), 2)
        
        # Verify the alarms created
        alarm_types = [alarm.alarm_type for alarm in alarms]
        self.assertIn(WeatherEventType.TORNADO.name, alarm_types)
        self.assertIn(WeatherEventType.SEVERE_THUNDERSTORM.name, alarm_types)
    
    def test_alarm_signature_consistency(self):
        """Test that alarms from same event type have consistent signatures for grouping."""
        alert1 = self.create_test_weather_alert(
            event_type=WeatherEventType.TORNADO,
            severity=AlertSeverity.EXTREME,
            headline="First Tornado Warning"
        )
        
        alert2 = self.create_test_weather_alert(
            event_type=WeatherEventType.TORNADO,
            severity=AlertSeverity.SEVERE,  # Different severity
            headline="Second Tornado Warning"  # Different headline
        )
        
        alarm1 = self.mapper.create_alarm(alert1)
        alarm2 = self.mapper.create_alarm(alert2)
        
        # Both should have same alarm type (for signature)
        self.assertEqual(alarm1.alarm_type, alarm2.alarm_type)
        self.assertEqual(alarm1.alarm_type, WeatherEventType.TORNADO.name)
        
        # But different alarm levels based on severity
        self.assertEqual(alarm1.alarm_level, AlarmLevel.CRITICAL)
        self.assertEqual(alarm2.alarm_level, AlarmLevel.CRITICAL)  # Tornado is always critical
    
    def test_edge_case_missing_fields(self):
        """Test handling of alerts with missing optional fields."""
        alert = WeatherAlert(
            event_type=WeatherEventType.TORNADO,
            event="Tornado Warning",
            status=AlertStatus.ACTUAL,
            category=AlertCategory.METEOROLOGICAL,
            headline="",  # Empty headline
            description="",  # Empty description
            instruction="",  # Empty instruction
            affected_areas="Unknown",
            effective=self.base_datetime,
            onset=self.base_datetime,
            expires=None,  # No expiration
            ends=None,     # No end time
            severity=AlertSeverity.EXTREME,
            certainty=AlertCertainty.OBSERVED,
            urgency=AlertUrgency.IMMEDIATE,
        )
        
        # Should still create alarm
        self.assertTrue(self.mapper.should_create_alarm(alert))
        alarm = self.mapper.create_alarm(alert)
        self.assertIsNotNone(alarm)
        
        # Should generate reasonable title
        self.assertIn("Tornado", alarm.title)
        self.assertIn("Extreme", alarm.title)
        
        # Should use event-type based lifetime
        expected_lifetime = self.mapper.EVENT_TYPE_TO_LIFETIME.get(
            WeatherEventType.TORNADO,
            self.mapper.DEFAULT_LIFETIME_SECS
        )
        self.assertEqual(alarm.alarm_lifetime_secs, expected_lifetime)
        
