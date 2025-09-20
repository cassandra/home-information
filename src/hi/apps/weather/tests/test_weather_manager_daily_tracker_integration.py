"""
Integration tests for WeatherManager and DailyWeatherTracker.
Tests the complete flow of temperature tracking and fallback value population.
"""
import logging
from unittest.mock import patch
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone
import pytz

from hi.apps.weather.weather_manager import WeatherManager
from hi.apps.weather.transient_models import WeatherConditionsData, NumericDataPoint, Station
from hi.apps.weather.weather_data_source import WeatherDataSource
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity
from hi.testing.async_task_utils import AsyncTaskTestCase

logging.disable(logging.CRITICAL)


class MockWeatherDataSource(WeatherDataSource):
    """Mock weather data source for testing."""
    
    @classmethod
    def weather_source_id(cls):
        return 'mock_source'
    
    @classmethod
    def weather_source_label(cls):
        return 'Mock Weather Source'
    
    @classmethod
    def weather_source_abbreviation(cls):
        return 'MOCK'
    
    def __init__(self):
        super().__init__(
            priority=1,
            requests_per_day_limit=1000,
            requests_per_polling_interval=10,
            min_polling_interval_secs=300
        )
        self._mock_location = GeographicLocation(
            latitude=30.270,
            longitude=-97.740,
            elevation=UnitQuantity(167.0, 'm')
        )
    
    async def get_data(self):
        pass  # Not used in these tests


class TestWeatherManagerDailyTrackerIntegration(AsyncTaskTestCase):
    """Test integration between WeatherManager and DailyWeatherTracker."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear cache before each test
        cache.clear()
        
        # Create weather manager instance
        self.weather_manager = WeatherManager()
        self.weather_manager.ensure_initialized()
        
        # Create test data source
        self.mock_source = MockWeatherDataSource()
        
        # Create test station
        self.test_station = Station(
            source=self.mock_source.data_point_source,
            station_id="TEST123",
            name="Test Station"
        )
        
        # Base test time
        self.base_time = timezone.make_aware(datetime(2024, 3, 15, 12, 0, 0), pytz.UTC)

    def tearDown(self):
        """Clean up test environment."""
        # Clear cache to prevent test interference in parallel execution
        cache.clear()
        super().tearDown()

    def create_test_conditions(self, temp_celsius, timestamp=None, include_today_fields=True):
        """Helper to create test weather conditions."""
        if timestamp is None:
            timestamp = self.base_time
        
        temperature_datapoint = NumericDataPoint(
            station=self.test_station,
            source_datetime=timestamp,
            quantity_ave=UnitQuantity(temp_celsius, 'degree_Celsius')
        )
        
        conditions = WeatherConditionsData()
        conditions.temperature = temperature_datapoint
        
        if include_today_fields:
            # Include today fields to test that they don't get overwritten when present
            conditions.temperature_min_today = NumericDataPoint(
                station=self.test_station,
                source_datetime=timestamp,
                quantity_ave=UnitQuantity(temp_celsius - 5, 'degree_Celsius')
            )
            conditions.temperature_max_today = NumericDataPoint(
                station=self.test_station,
                source_datetime=timestamp,
                quantity_ave=UnitQuantity(temp_celsius + 5, 'degree_Celsius')
            )
        
        return conditions
    
    def test_temperature_recording_during_update(self):
        """Test that temperatures are recorded when updating current conditions."""
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Create test conditions
            conditions = self.create_test_conditions(25.0, include_today_fields=False)
            
            # Update current conditions (should record temperature)
            self.run_async(self.weather_manager.update_current_conditions(
                data_point_source=self.mock_source.data_point_source,
                weather_conditions_data=conditions
            ))
            
            # Check that temperature was recorded in daily tracker
            location_key = self.weather_manager._get_location_key()
            summary = self.weather_manager._daily_weather_tracker.get_daily_summary(location_key)
            
            self.assertIsNotNone(summary)
            self.assertEqual(summary['date'], '2024-03-15')
            self.assertIn('temperature', summary['fields'])
            
            temp_stats = summary['fields']['temperature']
            self.assertEqual(temp_stats['min']['value'], 25.0)
            self.assertEqual(temp_stats['max']['value'], 25.0)
    
    def test_weather_stats_separate_from_conditions(self):
        """Test that weather statistics are retrieved separately from current conditions."""
        location_key = "30.270,-97.740"  # Expected location key from mock source
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # First, record some temperature data through the daily tracker
            conditions_to_record = self.create_test_conditions(22.0, include_today_fields=False)
            self.weather_manager._daily_weather_tracker.record_weather_conditions(
                weather_conditions_data=conditions_to_record,
                location_key=location_key
            )
            
            # Now create current conditions WITHOUT today's min/max fields
            current_conditions = WeatherConditionsData()
            current_conditions.temperature = NumericDataPoint(
                station=self.test_station,
                source_datetime=self.base_time,
                quantity_ave=UnitQuantity(25.0, 'degree_Celsius')
            )
            # Explicitly set today fields to None to test they stay None
            current_conditions.temperature_min_today = None
            current_conditions.temperature_max_today = None
            
            # Set as current conditions in weather manager
            self.weather_manager._current_conditions_data = current_conditions
            
            # Mock the location key method to return consistent location
            with patch.object(self.weather_manager, '_get_location_key', return_value=location_key):
                # Get current conditions (should NOT populate fallbacks)
                result_conditions = self.weather_manager.get_current_conditions_data()
                
                # Get weather stats separately
                weather_stats = self.weather_manager.get_weather_stats_today()
            
            # Current conditions should not have fallback values (new architecture)
            self.assertIsNone(result_conditions.temperature_min_today)
            self.assertIsNone(result_conditions.temperature_max_today)
            
            # But weather stats should have the tracked values
            self.assertIsNotNone(weather_stats.temperature)
            # Note: Currently using max temp as the single temperature datapoint
            self.assertEqual(weather_stats.temperature.quantity_ave.magnitude, 22.0)
    
    def test_fallback_does_not_overwrite_existing_data(self):
        """Test that fallback values don't overwrite existing API data."""
        location_key = "30.270,-97.740"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record fallback data
            conditions_to_record = self.create_test_conditions(20.0, include_today_fields=False)
            self.weather_manager._daily_weather_tracker.record_weather_conditions(
                weather_conditions_data=conditions_to_record,
                location_key=location_key
            )
            
            # Create current conditions WITH existing today's min/max (from API)
            current_conditions = WeatherConditionsData()
            current_conditions.temperature = NumericDataPoint(
                station=self.test_station,
                source_datetime=self.base_time,
                quantity_ave=UnitQuantity(25.0, 'degree_Celsius')
            )
            
            # Set existing API values (different from fallback)
            current_conditions.temperature_min_today = NumericDataPoint(
                station=self.test_station,
                source_datetime=self.base_time,
                quantity_ave=UnitQuantity(18.0, 'degree_Celsius')  # API value
            )
            current_conditions.temperature_max_today = NumericDataPoint(
                station=self.test_station,
                source_datetime=self.base_time,
                quantity_ave=UnitQuantity(28.0, 'degree_Celsius')  # API value
            )
            
            self.weather_manager._current_conditions_data = current_conditions
            
            with patch.object(self.weather_manager, '_get_location_key', return_value=location_key):
                result_conditions = self.weather_manager.get_current_conditions_data()
            
            # Should keep original API values, not use fallbacks
            self.assertEqual(result_conditions.temperature_min_today.quantity_ave.magnitude, 18.0)
            self.assertEqual(result_conditions.temperature_max_today.quantity_ave.magnitude, 28.0)
    
    def test_location_key_generation(self):
        """Test that location keys are generated correctly."""
        # Test with weather data source
        
        # Test with no weather data source (should fall back to console settings)
        with patch('hi.apps.console.console_helper.ConsoleSettingsHelper.get_geographic_location') as mock_geo:
            mock_geo.return_value = GeographicLocation(latitude=42.123, longitude=-71.456)
            location_key = self.weather_manager._get_location_key()
            self.assertEqual(location_key, "42.123,-71.456")
        
        # Test with no location available (should fall back to "default")
        with patch('hi.apps.console.console_helper.ConsoleSettingsHelper.get_geographic_location') as mock_geo:
            mock_geo.return_value = None
            location_key = self.weather_manager._get_location_key()
            self.assertEqual(location_key, "default")
    
    def test_multiple_temperature_updates_tracking(self):
        """Test that multiple temperature updates are tracked correctly."""
        location_key = "30.268,-97.743"  # This matches what the WeatherManager actually uses
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Update with multiple different temperatures using different timestamps
            # so each update actually gets recorded (otherwise same timestamp prevents overwrite)
            temperatures = [20.0, 25.0, 18.0, 30.0, 22.0]
            
            for i, temp in enumerate(temperatures):
                # Use incrementing timestamps so each update actually overwrites the previous
                timestamp = self.base_time + timedelta(minutes=i * 10)
                conditions = self.create_test_conditions(temp, timestamp=timestamp, include_today_fields=False)
                self.run_async(self.weather_manager.update_current_conditions(
                    data_point_source=self.mock_source.data_point_source,
                    weather_conditions_data=conditions
                ))
            
            # Check final tracking results
            summary = self.weather_manager._daily_weather_tracker.get_daily_summary(location_key)
            
            self.assertIsNotNone(summary)
            temp_stats = summary['fields']['temperature']
            self.assertEqual(temp_stats['min']['value'], 18.0)  # Lowest recorded
            self.assertEqual(temp_stats['max']['value'], 30.0)  # Highest recorded
    
    def test_weather_stats_source_priority(self):
        """Test that weather stats sources have lower priority than real API sources."""
        location_key = "30.270,-97.740"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record temperature for stats tracking
            conditions_to_record = self.create_test_conditions(20.0, include_today_fields=False)
            self.weather_manager._daily_weather_tracker.record_weather_conditions(
                weather_conditions_data=conditions_to_record,
                location_key=location_key
            )
            
            with patch.object(self.weather_manager, '_get_location_key', return_value=location_key):
                # Get weather stats (new architecture)
                weather_stats = self.weather_manager.get_weather_stats_today()
            
            # Check that weather stats sources have high priority numbers (low priority)
            self.assertIsNotNone(weather_stats.temperature)
            self.assertEqual(weather_stats.temperature.source.priority, 1000)  # Low priority
            self.assertEqual(weather_stats.temperature.source.id, "daily_weather_tracker")
    
    def test_timezone_consistency(self):
        """Test that timezone handling is consistent between recording and retrieval."""
        # Use a different timezone for the daily tracker
        pacific_tz = pytz.timezone('US/Pacific')
        location_key = "30.268,-97.743"  # This matches what the WeatherManager actually uses
        
        # Time that's late in the day Pacific time
        pacific_late = pacific_tz.localize(datetime(2024, 3, 15, 23, 30, 0))
        utc_late = pacific_late.astimezone(pytz.UTC)
        
        # Mock ConsoleSettingsHelper to return Pacific timezone
        with patch('hi.apps.weather.daily_weather_tracker.ConsoleSettingsHelper') as mock_console, \
             patch('hi.apps.common.datetimeproxy.now') as mock_now:
            
            mock_console.return_value.get_tz_name.return_value = 'US/Pacific'
            
            # Mock datetimeproxy.now() to handle timezone conversion properly
            def mock_now_func(tzname=None):
                if tzname is None:
                    return utc_late
                else:
                    tz = pytz.timezone(tzname)
                    return utc_late.astimezone(tz)
            mock_now.side_effect = mock_now_func
            
            # Record temperature
            conditions = self.create_test_conditions(25.0, utc_late, include_today_fields=False)
            self.run_async(self.weather_manager.update_current_conditions(
                data_point_source=self.mock_source.data_point_source,
                weather_conditions_data=conditions
            ))
            
            # Check that it's recorded under correct date
            summary = self.weather_manager._daily_weather_tracker.get_daily_summary(location_key)
            self.assertEqual(summary['date'], '2024-03-15')  # Pacific date, not UTC date
    
    def test_no_fallback_when_no_tracking_data(self):
        """Test that no fallback is provided when no tracking data exists."""
        location_key = "new_location_no_data"
        
        # Create current conditions without today fields
        current_conditions = WeatherConditionsData()
        current_conditions.temperature_min_today = None
        current_conditions.temperature_max_today = None
        self.weather_manager._current_conditions_data = current_conditions
        
        with patch.object(self.weather_manager, '_get_location_key', return_value=location_key):
            result_conditions = self.weather_manager.get_current_conditions_data()
        
        # Should still be None (no fallback data available)
        self.assertIsNone(result_conditions.temperature_min_today)
        self.assertIsNone(result_conditions.temperature_max_today)
