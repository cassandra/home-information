"""
Unit tests for DailyWeatherTracker - daily weather statistics tracking.
"""
import json
import logging
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.utils import timezone
import pytz

from hi.apps.weather.daily_weather_tracker import DailyWeatherTracker
from hi.apps.weather.transient_models import (
    WeatherConditionsData,
    NumericDataPoint,
    DataPointSource,
    Station,
)
from hi.units import UnitQuantity

logging.disable(logging.CRITICAL)


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
    
    # ============= NEW BEHAVIOR-FOCUSED TESTS =============
    # These tests focus on testing the public interface of DailyWeatherTracker
    # rather than testing private implementation details
    
    def test_record_weather_conditions_tracks_temperature_statistics(self):
        """Test that recording weather conditions properly tracks temperature min/max."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record multiple temperature readings throughout the day
            temperatures = [18.0, 25.0, 22.0, 30.0, 15.0, 28.0]
            
            for temp in temperatures:
                weather_data = WeatherConditionsData(
                    temperature=self.create_test_temperature_datapoint(temp)
                )
                
                # Use public interface to record weather conditions
                self.tracker.record_weather_conditions(weather_data, location_key)
            
            # Verify min/max tracking using public interface
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key)
            
            self.assertIsNotNone(min_temp)
            self.assertIsNotNone(max_temp)
            self.assertAlmostEqual(min_temp.quantity_ave.magnitude, 15.0, places=1)
            self.assertAlmostEqual(max_temp.quantity_ave.magnitude, 30.0, places=1)
            self.assertEqual(min_temp.quantity_ave.units, 'degree_Celsius')
            self.assertEqual(max_temp.quantity_ave.units, 'degree_Celsius')
    
    def test_populate_daily_fallbacks_fills_missing_temperature_data(self):
        """Test that populate_daily_fallbacks correctly fills missing temperature min/max."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # First, record some temperature data to establish tracking
            weather_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(20.0)
            )
            self.tracker.record_weather_conditions(weather_data, location_key)
            
            weather_data2 = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(25.0)
            )
            self.tracker.record_weather_conditions(weather_data2, location_key)
            
            # Create weather data with missing daily min/max
            incomplete_weather_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(22.0),
                # Note: temperature_min_today and temperature_max_today are None
            )
            
            # Verify fallbacks are initially None
            self.assertIsNone(incomplete_weather_data.temperature_min_today)
            self.assertIsNone(incomplete_weather_data.temperature_max_today)
            
            # Use public interface to populate fallbacks
            self.tracker.populate_daily_fallbacks(incomplete_weather_data, location_key)
            
            # Verify fallbacks were populated
            self.assertIsNotNone(incomplete_weather_data.temperature_min_today)
            self.assertIsNotNone(incomplete_weather_data.temperature_max_today)
            self.assertAlmostEqual(
                incomplete_weather_data.temperature_min_today.quantity_ave.magnitude, 20.0, places=1)
            self.assertAlmostEqual(
                incomplete_weather_data.temperature_max_today.quantity_ave.magnitude, 25.0, places=1)
    
    def test_populate_daily_fallbacks_preserves_existing_data(self):
        """Test that populate_daily_fallbacks doesn't overwrite existing min/max data."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record some tracking data
            weather_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(20.0)
            )
            self.tracker.record_weather_conditions(weather_data, location_key)
            
            # Create weather data that already has min/max values
            existing_min = self.create_test_temperature_datapoint(15.0)
            existing_max = self.create_test_temperature_datapoint(30.0)
            
            complete_weather_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(22.0),
                temperature_min_today=existing_min,
                temperature_max_today=existing_max
            )
            
            # Use public interface - should not overwrite existing data
            self.tracker.populate_daily_fallbacks(complete_weather_data, location_key)
            
            # Verify existing data was preserved
            self.assertAlmostEqual(
                complete_weather_data.temperature_min_today.quantity_ave.magnitude, 15.0, places=1)
            self.assertAlmostEqual(
                complete_weather_data.temperature_max_today.quantity_ave.magnitude, 30.0, places=1)
    
    def test_get_daily_summary_provides_debug_information(self):
        """Test that get_daily_summary provides useful debugging information."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record some temperature data
            temperatures = [18.0, 25.0, 22.0]
            for temp in temperatures:
                weather_data = WeatherConditionsData(
                    temperature=self.create_test_temperature_datapoint(temp)
                )
                self.tracker.record_weather_conditions(weather_data, location_key)
            
            # Get daily summary using public interface
            summary = self.tracker.get_daily_summary(location_key)
            
            # Verify summary structure and content
            self.assertIn('date', summary)
            self.assertIn('timezone', summary)
            self.assertIn('fields', summary)
            
            # Verify temperature field is included
            self.assertIn('temperature', summary['fields'])
            temp_stats = summary['fields']['temperature']
            
            # Verify statistics are present
            self.assertIn('min', temp_stats)
            self.assertIn('max', temp_stats)
            self.assertEqual(temp_stats['min']['value'], 18.0)
            self.assertEqual(temp_stats['max']['value'], 25.0)
    
    def test_multiple_locations_tracked_independently(self):
        """Test that different locations are tracked independently."""
        location1 = "location_1"
        location2 = "location_2"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record different temperatures for different locations
            weather_data1 = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(10.0)
            )
            self.tracker.record_weather_conditions(weather_data1, location1)
            
            weather_data2 = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(20.0)
            )
            self.tracker.record_weather_conditions(weather_data2, location2)
            
            # Verify each location has its own independent tracking
            min1, max1 = self.tracker.get_temperature_min_max_today(location1)
            min2, max2 = self.tracker.get_temperature_min_max_today(location2)
            
            self.assertAlmostEqual(min1.quantity_ave.magnitude, 10.0, places=1)
            self.assertAlmostEqual(max1.quantity_ave.magnitude, 10.0, places=1)
            self.assertAlmostEqual(min2.quantity_ave.magnitude, 20.0, places=1)
            self.assertAlmostEqual(max2.quantity_ave.magnitude, 20.0, places=1)
    
    def test_clear_today_resets_tracking_data(self):
        """Test that clear_today properly resets tracking for a location."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Record some temperature data
            weather_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(20.0)
            )
            self.tracker.record_weather_conditions(weather_data, location_key)
            
            # Verify data exists
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key)
            self.assertIsNotNone(min_temp)
            self.assertIsNotNone(max_temp)
            
            # Clear the data using public interface
            self.tracker.clear_today(location_key)
            
            # Verify data was cleared
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key)
            self.assertIsNone(min_temp)
            self.assertIsNone(max_temp)
            
            # Verify summary is empty (should return None when no data)
            summary = self.tracker.get_daily_summary(location_key)
            self.assertIsNone(summary)
    
    def test_bug_reproduction_first_bad_reading_sets_both_min_max(self):
        """Test case reproducing Issue #166 - first bad reading sets both min and max to same wrong value."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Scenario: First reading of the day is a bad 88°F (31.1°C) value
            # This sets both min and max to 31.1°C
            bad_weather_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(31.1)  # 88°F
            )
            self.tracker.record_weather_conditions(bad_weather_data, location_key)
            
            # Verify both min and max are set to the bad value
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key)
            self.assertAlmostEqual(min_temp.quantity_ave.magnitude, 31.1, places=1)
            self.assertAlmostEqual(max_temp.quantity_ave.magnitude, 31.1, places=1)
            
            # Simulate the bug: subsequent real readings don't get recorded due to 
            # weather_manager passing incoming data instead of merged data
            # (so this normal reading would have been missed before the fix)
            normal_weather_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(27.2)  # 81°F
            )
            self.tracker.record_weather_conditions(normal_weather_data, location_key)
            
            # After the fix, this should update the min to the lower real value
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key)
            self.assertAlmostEqual(min_temp.quantity_ave.magnitude, 27.2, places=1)  # Should be updated to real min
            self.assertAlmostEqual(max_temp.quantity_ave.magnitude, 31.1, places=1)  # Should remain the higher value
            
            # Record even lower reading that should become the new minimum
            lower_weather_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(21.1)  # ~70°F
            )
            self.tracker.record_weather_conditions(lower_weather_data, location_key)
            
            # Now min should be the lowest real reading
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key)
            self.assertAlmostEqual(min_temp.quantity_ave.magnitude, 21.1, places=1)  # New minimum
            self.assertAlmostEqual(max_temp.quantity_ave.magnitude, 31.1, places=1)  # Unchanged max
    
    def test_current_temperature_outside_cached_range_scenario(self):
        """Test the specific scenario from Issue #166 - current temp outside min/max range should not occur."""
        location_key = "test_location"
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=self.base_time):
            # Simulate the problematic scenario: a high temperature gets recorded first
            high_temp_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(31.1)  # 88°F - the problematic value
            )
            self.tracker.record_weather_conditions(high_temp_data, location_key)
            
            # Verify both min and max are set to the high value initially
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key)
            self.assertIsNotNone(min_temp)
            self.assertIsNotNone(max_temp)
            self.assertAlmostEqual(min_temp.quantity_ave.magnitude, 31.1, places=1)
            self.assertAlmostEqual(max_temp.quantity_ave.magnitude, 31.1, places=1)
            
            # Now record the actual current temperature (81°F = 27.2°C)
            current_temp_data = WeatherConditionsData(
                temperature=self.create_test_temperature_datapoint(27.2)  # 81°F - actual current
            )
            self.tracker.record_weather_conditions(current_temp_data, location_key)
            
            # After the fix, min should update to include the current temperature
            min_temp, max_temp = self.tracker.get_temperature_min_max_today(location_key)
            self.assertIsNotNone(min_temp)
            self.assertIsNotNone(max_temp)
            
            # Critical assertion: current temperature must be within the min/max range
            current_celsius = 27.2
            min_celsius = min_temp.quantity_ave.magnitude
            max_celsius = max_temp.quantity_ave.magnitude
            
            self.assertLessEqual(
                min_celsius, current_celsius, 
                f"Min temperature ({min_celsius:.1f}°C) should not be higher than current ({current_celsius:.1f}°C)")
            self.assertGreaterEqual(
                max_celsius, current_celsius,
                f"Max temperature ({max_celsius:.1f}°C) should not be lower than current ({current_celsius:.1f}°C)")
            
            # Specific values should be correct
            self.assertAlmostEqual(min_celsius, 27.2, places=1)  # Should be updated to current
            self.assertAlmostEqual(max_celsius, 31.1, places=1)  # Should remain the higher value
    
    # ============= ORIGINAL TESTS (TO BE DEPRECATED) =============
    
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
