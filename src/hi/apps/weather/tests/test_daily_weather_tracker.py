"""
Unit tests for DailyWeatherTracker - daily weather statistics tracking.
"""
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.utils import timezone
import pytz

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.daily_weather_tracker import DailyWeatherTracker
from hi.apps.weather.transient_models import WeatherConditionsData, NumericDataPoint, DataPointSource, Station
from hi.units import UnitQuantity


class TestDailyWeatherTracker(unittest.TestCase):
    """Test daily weather statistics tracking functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear cache before each test
        cache.clear()
        
        # Use UTC timezone for consistent testing
        self.test_timezone = pytz.UTC
        self.tracker = DailyWeatherTracker(user_timezone=self.test_timezone)
        
        # Create test data point source and station
        self.test_source = DataPointSource(
            id="test_source",
            label="Test Weather Source",
            abbreviation="TWS",
            priority=1
        )
        
        self.test_station = Station(
            source=self.test_source,
            station_id="TEST123",
            name="Test Station"
        )
        
        # Base test time - use timezone-aware datetime
        self.base_time = timezone.make_aware(datetime(2024, 3, 15, 12, 0, 0), self.test_timezone)
    
    def create_test_temperature_datapoint(self, temp_celsius, timestamp=None):
        """Helper to create test temperature data points."""
        if timestamp is None:
            timestamp = self.base_time
            
        return NumericDataPoint(
            station=self.test_station,
            source_datetime=timestamp,
            quantity_ave=UnitQuantity(temp_celsius, 'degree_Celsius')
        )
    
    def create_test_weather_conditions(self, temp_celsius, timestamp=None):
        """Helper to create test weather conditions data."""
        temperature_datapoint = self.create_test_temperature_datapoint(temp_celsius, timestamp)
        
        conditions = WeatherConditionsData()
        conditions.temperature = temperature_datapoint
        return conditions
    
    def test_record_weather_conditions_basic(self):
        """Test basic temperature recording functionality."""
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record a temperature observation
            conditions = self.create_test_weather_conditions(25.0)
            self.tracker.record_weather_conditions(conditions, location_key="test_location")
            
            # Check that data was stored
            summary = self.tracker.get_daily_summary(location_key="test_location")
            self.assertIsNotNone(summary)
            self.assertEqual(summary['date'], '2024-03-15')
            self.assertIn('temperature', summary['fields'])
            
            temp_stats = summary['fields']['temperature']
            self.assertEqual(temp_stats[self.tracker.STAT_MIN]['value'], 25.0)
            self.assertEqual(temp_stats[self.tracker.STAT_MAX]['value'], 25.0)
    
    def test_temperature_min_max_tracking(self):
        """Test that min/max temperatures are tracked correctly."""
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            location_key = "test_location"
            
            # Record multiple temperatures throughout the day
            temps_and_times = [
                (20.0, self.base_time.replace(hour=6)),   # Morning low
                (25.0, self.base_time.replace(hour=10)),  # Mid-morning
                (30.0, self.base_time.replace(hour=14)),  # Afternoon high
                (22.0, self.base_time.replace(hour=18)),  # Evening
                (18.0, self.base_time.replace(hour=22)),  # Night low
            ]
            
            for temp, time in temps_and_times:
                conditions = self.create_test_weather_conditions(temp, time)
                self.tracker.record_weather_conditions(conditions, location_key=location_key)
            
            # Get today's min/max
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key=location_key)
            
            # Verify results
            self.assertIsNotNone(min_temp)
            self.assertIsNotNone(max_temp)
            self.assertEqual(min_temp.quantity_ave.magnitude, 18.0)  # Night low
            self.assertEqual(max_temp.quantity_ave.magnitude, 30.0)  # Afternoon high
            
            # Verify timestamps
            self.assertEqual(min_temp.source_datetime, self.base_time.replace(hour=22))
            self.assertEqual(max_temp.source_datetime, self.base_time.replace(hour=14))
    
    def test_multiple_days_tracking(self):
        """Test that data is tracked separately for different days."""
        location_key = "test_location"
        
        # Day 1: Record temperatures
        day1 = self.base_time
        with patch('hi.apps.common.datetimeproxy.now', return_value=day1):
            conditions1 = self.create_test_weather_conditions(20.0, day1)
            self.tracker.record_weather_conditions(conditions1, location_key=location_key)
        
        # Day 2: Record different temperatures
        day2 = self.base_time + timedelta(days=1)
        with patch('hi.apps.common.datetimeproxy.now', return_value=day2):
            conditions2 = self.create_test_weather_conditions(25.0, day2)
            self.tracker.record_weather_conditions(conditions2, location_key=location_key)
        
        # Check day 1 data
        with patch('hi.apps.common.datetimeproxy.now', return_value=day1):
            min_temp1, max_temp1 = self.tracker.get_temperature_min_max_today(location_key=location_key)
            self.assertEqual(min_temp1.quantity_ave.magnitude, 20.0)
            self.assertEqual(max_temp1.quantity_ave.magnitude, 20.0)
        
        # Check day 2 data
        with patch('hi.apps.common.datetimeproxy.now', return_value=day2):
            min_temp2, max_temp2 = self.tracker.get_temperature_min_max_today(location_key=location_key)
            self.assertEqual(min_temp2.quantity_ave.magnitude, 25.0)
            self.assertEqual(max_temp2.quantity_ave.magnitude, 25.0)
    
    def test_timezone_handling(self):
        """Test that day boundaries are correctly handled in different timezones."""
        # Use US/Central timezone for this test
        central_tz = pytz.timezone('US/Central')
        tracker_central = DailyWeatherTracker(user_timezone=central_tz)
        
        # Create time that's late at night in Central time but next day in UTC
        # March 15, 2024 11:30 PM Central = March 16, 2024 4:30 AM UTC
        central_time = central_tz.localize(datetime(2024, 3, 15, 23, 30, 0))
        utc_time = central_time.astimezone(pytz.UTC)
        
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=utc_time):
            conditions = self.create_test_weather_conditions(20.0, utc_time)
            tracker_central.record_weather_conditions(conditions, location_key=location_key)
            
            # Should be stored under March 15 (Central time), not March 16 (UTC)
            summary = tracker_central.get_daily_summary(location_key=location_key)
            self.assertEqual(summary['date'], '2024-03-15')
    
    def test_no_data_scenarios(self):
        """Test behavior when no temperature data is available."""
        location_key = "empty_location"
        
        # Should return None for both min and max when no data
        min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key=location_key)
        self.assertIsNone(min_temp)
        self.assertIsNone(max_temp)
        
        # Summary should be None when no data
        summary = self.tracker.get_daily_summary(location_key=location_key)
        self.assertIsNone(summary)
    
    def test_invalid_temperature_data(self):
        """Test handling of invalid temperature data."""
        location_key = "test_location"
        
        # Test with None temperature
        conditions_none = WeatherConditionsData()
        conditions_none.temperature = None
        self.tracker.record_weather_conditions(conditions_none, location_key=location_key)
        
        # Test with missing conditions data
        conditions_empty = WeatherConditionsData()
        # Don't set temperature field at all
        self.tracker.record_weather_conditions(conditions_empty, location_key=location_key)
        
        # Should have no data recorded
        min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key=location_key)
        self.assertIsNone(min_temp)
        self.assertIsNone(max_temp)
    
    def test_populate_daily_fallbacks(self):
        """Test populating fallback values in weather conditions data."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record some temperature data
            conditions_record = self.create_test_weather_conditions(25.0)
            self.tracker.record_weather_conditions(conditions_record, location_key=location_key)
            
            # Create conditions data without today's min/max
            conditions_empty = WeatherConditionsData()
            self.assertIsNone(conditions_empty.temperature_min_today)
            self.assertIsNone(conditions_empty.temperature_max_today)
            
            # Populate fallbacks
            self.tracker.populate_daily_fallbacks(conditions_empty, location_key=location_key)
            
            # Should now have fallback values
            self.assertIsNotNone(conditions_empty.temperature_min_today)
            self.assertIsNotNone(conditions_empty.temperature_max_today)
            self.assertEqual(conditions_empty.temperature_min_today.quantity_ave.magnitude, 25.0)
            self.assertEqual(conditions_empty.temperature_max_today.quantity_ave.magnitude, 25.0)
    
    def test_fallback_source_properties(self):
        """Test that fallback data points have correct source properties."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            conditions = self.create_test_weather_conditions(20.0)
            self.tracker.record_weather_conditions(conditions, location_key=location_key)
            
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key=location_key)
            
            # Check that fallback source has low priority
            self.assertEqual(min_temp.source.id, "daily_weather_tracker")
            self.assertEqual(min_temp.source.priority, 1000)  # Low priority
            self.assertEqual(max_temp.source.id, "daily_weather_tracker")
            self.assertEqual(max_temp.source.priority, 1000)
    
    def test_cache_storage_and_retrieval(self):
        """Test that data is properly stored and retrieved from cache."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record temperature
            conditions = self.create_test_weather_conditions(25.0)
            self.tracker.record_weather_conditions(conditions, location_key=location_key)
            
            # Manually check cache contents
            date_key = self.base_time.strftime('%Y-%m-%d')
            cache_key = f"{self.tracker.CACHE_KEY_PREFIX}:{location_key}:{date_key}:temperature"
            cached_data = cache.get(cache_key)
            
            self.assertIsNotNone(cached_data)
            parsed_data = json.loads(cached_data)
            self.assertIn(self.tracker.STAT_MIN, parsed_data)
            self.assertIn(self.tracker.STAT_MAX, parsed_data)
            self.assertEqual(parsed_data[self.tracker.STAT_MIN]['value'], 25.0)
    
    def test_clear_today_functionality(self):
        """Test clearing today's temperature data."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record temperature
            conditions = self.create_test_weather_conditions(25.0)
            self.tracker.record_weather_conditions(conditions, location_key=location_key)
            
            # Verify data exists
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key=location_key)
            self.assertIsNotNone(min_temp)
            
            # Clear data
            self.tracker.clear_today(location_key=location_key, field_name="temperature")
            
            # Verify data is cleared
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key=location_key)
            self.assertIsNone(min_temp)
            self.assertIsNone(max_temp)
    
    def test_multiple_locations(self):
        """Test tracking temperatures for multiple locations."""
        location1 = "location_1"
        location2 = "location_2"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record different temperatures for different locations
            conditions1 = self.create_test_weather_conditions(20.0)
            conditions2 = self.create_test_weather_conditions(30.0)
            
            self.tracker.record_weather_conditions(conditions1, location_key=location1)
            self.tracker.record_weather_conditions(conditions2, location_key=location2)
            
            # Verify each location has its own data
            min1, max1 = self.tracker.get_temperature_min_max_today(location_key=location1)
            min2, max2 = self.tracker.get_temperature_min_max_today(location_key=location2)
            
            self.assertEqual(min1.quantity_ave.magnitude, 20.0)
            self.assertEqual(max1.quantity_ave.magnitude, 20.0)
            self.assertEqual(min2.quantity_ave.magnitude, 30.0)
            self.assertEqual(max2.quantity_ave.magnitude, 30.0)
    
    def test_temperature_unit_conversion(self):
        """Test that temperatures are consistently stored in Celsius."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record temperature in Fahrenheit
            fahrenheit_temp = NumericDataPoint(
                station=self.test_station,
                source_datetime=self.base_time,
                quantity_ave=UnitQuantity(77.0, 'degree_Fahrenheit')  # 25°C
            )
            
            conditions = WeatherConditionsData()
            conditions.temperature = fahrenheit_temp
            
            self.tracker.record_weather_conditions(conditions, location_key=location_key)
            
            # Retrieved temperature should be in Celsius
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key=location_key)
            
            self.assertAlmostEqual(min_temp.quantity_ave.magnitude, 25.0, places=1)
            self.assertEqual(min_temp.quantity_ave.units, 'degree_Celsius')
    
    def test_extensibility_for_future_fields(self):
        """Test that the architecture supports future weather field additions."""
        # This test verifies the general field recording mechanism
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Test the internal _record_field_value method for extensibility
            self.tracker._record_field_value(
                location_key=location_key,
                field_name="humidity",
                value=65.0,
                units="percent",
                timestamp=self.base_time,
                track_stats=[self.tracker.STAT_MIN, self.tracker.STAT_MAX]
            )
            
            # Check that field stats were recorded
            field_stats = self.tracker._get_field_stats_today(location_key, "humidity")
            
            self.assertIn(self.tracker.STAT_MIN, field_stats)
            self.assertIn(self.tracker.STAT_MAX, field_stats)
            self.assertEqual(field_stats[self.tracker.STAT_MIN]['value'], 65.0)
            self.assertEqual(field_stats[self.tracker.STAT_MAX]['value'], 65.0)
            self.assertEqual(field_stats[self.tracker.STAT_MIN]['units'], "percent")