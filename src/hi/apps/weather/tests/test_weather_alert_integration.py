"""
Integration tests for weather alert to system alarm conversion.
Tests the complete flow from NWS data parsing to alarm creation.
"""
import logging
from unittest.mock import Mock, AsyncMock

from hi.apps.weather.enums import WeatherEventType, AlertSeverity
from hi.apps.weather.weather_sources.nws import NationalWeatherService
from hi.apps.weather.weather_manager import WeatherManager
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity
from hi.testing.async_task_utils import AsyncTaskTestCase

logging.disable(logging.CRITICAL)


class TestWeatherAlertIntegration(AsyncTaskTestCase):
    """Test end-to-end weather alert to alarm integration."""
    
    def test_nws_tornado_warning_creates_critical_alarm(self):
        """Test that a tornado warning from NWS creates a critical system alarm."""
        # Create test location
        test_location = GeographicLocation(
            latitude=30.27,
            longitude=-97.74,
            elevation=UnitQuantity(167.0, 'm')
        )
        
        # NWS API response for tornado warning with event code
        tornado_alert_data = {
            "features": [
                {
                    "properties": {
                        "event": "Tornado Warning",
                        "status": "Actual",
                        "category": "Met",
                        "severity": "Extreme",
                        "certainty": "Observed",
                        "urgency": "Immediate",
                        "headline": "Tornado Warning issued March 15 at 8:00PM CDT until 8:30PM CDT",
                        "description": "At 800 PM CDT, a severe thunderstorm capable of producing a tornado was located near downtown Austin...",
                        "instruction": "TAKE COVER NOW! Move to a basement or an interior room on the lowest floor of a sturdy building.",
                        "areaDesc": "Travis County",
                        "effective": "2024-03-15T20:00:00-05:00",
                        "expires": "2024-03-15T20:30:00-05:00",
                        "onset": "2024-03-15T20:00:00-05:00",
                        "ends": "2024-03-15T20:30:00-05:00",
                        "eventCode": {
                            "SAME": ["NWS"],
                            "NationalWeatherService": ["TOR"]
                        }
                    }
                }
            ]
        }
        
        # Parse the alert data
        nws = NationalWeatherService()
        weather_alerts = nws._parse_alerts_data(
            alerts_data=tornado_alert_data,
            geographic_location=test_location
        )
        
        # Verify we got a weather alert with correct canonical type
        self.assertEqual(len(weather_alerts), 1)
        alert = weather_alerts[0]
        self.assertEqual(alert.event_type, WeatherEventType.TORNADO)
        self.assertEqual(alert.event, "Tornado Warning")
        self.assertEqual(alert.severity, AlertSeverity.EXTREME)
        
        # Test alarm creation from the alert
        weather_manager = WeatherManager()
        mapper = weather_manager._weather_alert_alarm_mapper
        
        # Should create an alarm
        self.assertTrue(mapper.should_create_alarm(alert))
        
        # Create the alarm
        alarm = mapper.create_alarm(alert)
        self.assertIsNotNone(alarm)
        
        # Verify alarm properties
        self.assertEqual(alarm.alarm_type, WeatherEventType.TORNADO.name)
        self.assertEqual(alarm.alarm_level.name, 'CRITICAL')
        self.assertIn("Tornado Warning", alarm.title)
        self.assertEqual(alarm.security_level.name, 'OFF')  # Applies to all security levels
        
        # Verify alarm details contain weather info
        self.assertEqual(len(alarm.sensor_response_list), 1)
        details = alarm.sensor_response_list[0]
        self.assertEqual(details.detail_attrs['Event Type'], WeatherEventType.TORNADO.label)
        self.assertEqual(details.detail_attrs['Severity'], AlertSeverity.EXTREME.label)
        self.assertEqual(details.detail_attrs['Affected Areas'], "Travis County")
    
    def test_nws_lake_wind_advisory_creates_no_alarm(self):
        """Test that a lake wind advisory (informational marine weather) doesn't create an alarm."""
        test_location = GeographicLocation(
            latitude=47.8,
            longitude=-114.0,
            elevation=UnitQuantity(880.0, 'm')
        )
        
        # NWS API response for lake wind advisory
        advisory_data = {
            "features": [
                {
                    "properties": {
                        "event": "Lake Wind Advisory",
                        "status": "Actual",
                        "category": "Met",
                        "severity": "Moderate",
                        "certainty": "Likely",
                        "urgency": "Expected",
                        "headline": "Lake Wind Advisory issued until 9:00PM MDT",
                        "description": "Southwest winds 10 to 20 mph with gusts up to 30 mph expected.",
                        "instruction": "Boaters on area lakes should use extra caution.",
                        "areaDesc": "Flathead/Mission Valleys",
                        "effective": "2024-03-15T12:00:00-06:00",
                        "expires": "2024-03-15T21:00:00-06:00",
                        "eventCode": {
                            "SAME": ["NWS"],
                            "NationalWeatherService": ["LWY"]
                        }
                    }
                }
            ]
        }
        
        # Parse the alert data
        nws = NationalWeatherService()
        weather_alerts = nws._parse_alerts_data(
            alerts_data=advisory_data,
            geographic_location=test_location
        )
        
        # Verify we got a weather alert with correct canonical type
        self.assertEqual(len(weather_alerts), 1)
        alert = weather_alerts[0]
        self.assertEqual(alert.event_type, WeatherEventType.MARINE_WEATHER)
        self.assertEqual(alert.event, "Lake Wind Advisory")
        self.assertEqual(alert.severity, AlertSeverity.MODERATE)
        
        # Test alarm creation - should NOT create alarm for marine weather advisory
        weather_manager = WeatherManager()
        mapper = weather_manager._weather_alert_alarm_mapper
        
        # Should NOT create an alarm (marine weather is informational)
        self.assertFalse(mapper.should_create_alarm(alert))
        
        # Verify no alarm is created
        alarm = mapper.create_alarm(alert)
        self.assertIsNone(alarm)
    
    def test_weather_manager_integration(self):
        """Test that WeatherManager properly creates alarms from weather alerts."""
        # Mock alert manager to capture alarms
        mock_alert_manager = AsyncMock()
        mock_weather_manager = WeatherManager()
        
        # Override the alert manager with our mock
        mock_weather_manager.alert_manager_async = AsyncMock(return_value=mock_alert_manager)
        
        # Create test weather alerts (mix of alarm-worthy and non-alarm-worthy)
        test_alerts = [
            # Should create CRITICAL alarm
            self._create_test_alert(
                event_type=WeatherEventType.TORNADO,
                severity=AlertSeverity.EXTREME,
                headline="Tornado Warning"
            ),
            # Should create WARNING alarm
            self._create_test_alert(
                event_type=WeatherEventType.SEVERE_THUNDERSTORM,
                severity=AlertSeverity.SEVERE,
                headline="Severe Thunderstorm Warning"
            ),
            # Should NOT create alarm (informational)
            self._create_test_alert(
                event_type=WeatherEventType.SPECIAL_WEATHER,
                severity=AlertSeverity.MINOR,
                headline="Special Weather Statement"
            ),
        ]
        
        # Mock weather data source
        mock_data_source = Mock()
        mock_data_source.id = "test_nws"
        
        # Update weather alerts (this should create alarms)
        async def test_update():
            await mock_weather_manager.update_weather_alerts(
                data_point_source=mock_data_source.data_point_source,
                weather_alerts=test_alerts
            )

        self.run_async(test_update())
        
        # Verify alert manager was called to add alarms
        self.assertEqual(mock_alert_manager.add_alarm.call_count, 2)  # Only 2 should create alarms
        
        # Verify the alarms that were created
        call_args_list = mock_alert_manager.add_alarm.call_args_list
        alarm1 = call_args_list[0][0][0]  # First alarm
        alarm2 = call_args_list[1][0][0]  # Second alarm
        
        # Check alarm types
        alarm_types = {alarm1.alarm_type, alarm2.alarm_type}
        expected_types = {WeatherEventType.TORNADO.name, WeatherEventType.SEVERE_THUNDERSTORM.name}
        self.assertEqual(alarm_types, expected_types)
        
        # Verify weather alerts were stored
        stored_alerts = mock_weather_manager.get_weather_alerts()
        self.assertEqual(len(stored_alerts), 3)  # All alerts stored, regardless of alarm creation
    
    def _create_test_alert(self, event_type, severity, headline):
        """Helper to create test weather alerts."""
        from hi.apps.weather.transient_models import WeatherAlert
        from hi.apps.weather.enums import AlertCategory, AlertStatus, AlertUrgency, AlertCertainty
        from datetime import datetime
        from django.utils import timezone
        
        base_time = timezone.make_aware(datetime(2024, 3, 15, 20, 0, 0), timezone.utc)
        
        return WeatherAlert(
            event_type=event_type,
            event=headline,
            status=AlertStatus.ACTUAL,
            category=AlertCategory.METEOROLOGICAL,
            headline=headline,
            description="Test description for integration test.",
            instruction="Test instruction.",
            affected_areas="Test County",
            effective=base_time,
            onset=base_time,
            expires=base_time.replace(hour=21),  # 1 hour later
            ends=base_time.replace(hour=21),
            severity=severity,
            certainty=AlertCertainty.OBSERVED,
            urgency=AlertUrgency.IMMEDIATE,
        )


        
