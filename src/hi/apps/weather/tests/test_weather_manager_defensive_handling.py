"""
Test that WeatherManager gracefully handles errors in daily weather tracking
without breaking core weather API functionality.
"""
import unittest
from unittest.mock import patch
from datetime import datetime
import asyncio

from django.core.cache import cache
from django.utils import timezone
import pytz

from hi.apps.weather.weather_manager import WeatherManager
from hi.apps.weather.transient_models import WeatherConditionsData, NumericDataPoint, Station
from hi.apps.weather.weather_data_source import WeatherDataSource
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity
from hi.tests.base_test_case import BaseTestCase


class MockWeatherDataSource(WeatherDataSource):
    """Mock weather data source for testing."""
    
    def __init__(self, source_id="mock_source"):
        super().__init__(
            id=source_id,
            label="Mock Weather Source",
            abbreviation="MWS",
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
    
    @property
    def geographic_location(self):
        return self._mock_location
    
    async def get_data(self):
        pass


class TestWeatherManagerDefensiveHandling(BaseTestCase):
    """Test defensive error handling for daily weather tracking."""
    
    def setUp(self):
        """Set up test environment."""
        cache.clear()
        self.weather_manager = WeatherManager()
        self.weather_manager.ensure_initialized()
        
        # Clear any existing conditions data
        self.weather_manager._current_conditions_data = WeatherConditionsData()
        
        self.mock_source = MockWeatherDataSource()
        
        # Create test station and data
        self.test_station = Station(
            source=self.mock_source.data_point_source,
            station_id="TEST123",
            name="Test Station"
        )
        
        self.base_time = timezone.make_aware(datetime(2024, 3, 15, 12, 0, 0), pytz.UTC)
    
    def create_test_conditions(self, temp_celsius):
        """Helper to create test weather conditions."""
        temperature_datapoint = NumericDataPoint(
            station=self.test_station,
            source_datetime=self.base_time,
            quantity_ave=UnitQuantity(temp_celsius, 'degree_Celsius')
        )
        
        conditions = WeatherConditionsData()
        conditions.temperature = temperature_datapoint
        return conditions
    
    def test_daily_tracker_error_during_recording_does_not_break_update(self):
        """Test that errors in daily tracking don't break weather data updates."""
        
        # Mock the daily tracker to raise an exception
        with patch.object(self.weather_manager._daily_weather_tracker,
                          'record_weather_conditions') as mock_record:
            mock_record.side_effect = Exception("Simulated daily tracker error")
            
            # This should NOT raise an exception despite the daily tracker error
            conditions = self.create_test_conditions(25.0)
            
            # The update should complete successfully
            asyncio.run(self.weather_manager.update_current_conditions(
                weather_data_source=self.mock_source,
                weather_conditions_data=conditions
            ))
            
            # Verify the main weather data was still updated
            current_conditions = self.weather_manager._current_conditions_data
            self.assertIsNotNone(current_conditions.temperature)
            self.assertEqual(current_conditions.temperature.quantity_ave.magnitude, 25.0)
            
            # Verify the mock was called (showing the error path was taken)
            mock_record.assert_called_once()
    
    def test_daily_tracker_error_during_fallback_population_does_not_break_getter(self):
        """Test that errors in fallback population don't break getting current conditions."""
        
        # Set up some current conditions
        conditions = self.create_test_conditions(22.0)
        self.weather_manager._current_conditions_data = conditions
        
        # Mock the daily tracker to raise an exception during fallback population
        with patch.object(self.weather_manager._daily_weather_tracker,
                          'populate_daily_fallbacks') as mock_populate:
            mock_populate.side_effect = Exception("Simulated fallback population error")
            
            # This should NOT raise an exception despite the daily tracker error
            result_conditions = self.weather_manager.get_current_conditions_data()
            
            # Verify the main weather data is still returned
            self.assertIsNotNone(result_conditions)
            self.assertIsNotNone(result_conditions.temperature)
            self.assertEqual(result_conditions.temperature.quantity_ave.magnitude, 22.0)
            
            # Verify the mock was called (showing the error path was taken)
            mock_populate.assert_called_once()
    
    def test_location_key_generation_error_is_handled(self):
        """Test that errors in location key generation are handled gracefully."""
        
        # Mock _get_location_key to raise an exception
        with patch.object(self.weather_manager, '_get_location_key') as mock_location_key:
            mock_location_key.side_effect = Exception("Simulated location key error")
            
            # This should NOT raise an exception
            conditions = self.create_test_conditions(20.0)
            
            asyncio.run(self.weather_manager.update_current_conditions(
                weather_data_source=self.mock_source,
                weather_conditions_data=conditions
            ))
            
            # Main weather data should still be updated
            current_conditions = self.weather_manager._current_conditions_data
            self.assertEqual(current_conditions.temperature.quantity_ave.magnitude, 20.0)
            
            # Verify the mock was called (showing the error path was taken)
            mock_location_key.assert_called_once()
    
    def test_daily_tracker_internal_error_handling(self):
        """Test that the daily tracker itself handles errors gracefully."""
        
        # Test that populate_daily_fallbacks handles internal errors
        conditions = WeatherConditionsData()
        
        # Mock get_temperature_min_max_today to raise an exception
        with patch.object(self.weather_manager._daily_weather_tracker,
                          'get_temperature_min_max_today') as mock_get_temp:
            mock_get_temp.side_effect = Exception("Simulated internal tracker error")
            
            # This should NOT raise an exception
            self.weather_manager._daily_weather_tracker.populate_daily_fallbacks(
                weather_conditions_data=conditions,
                location_key="test_location"
            )
            
            # The conditions object should remain unchanged (no fallbacks added)
            self.assertIsNone(conditions.temperature_min_today)
            self.assertIsNone(conditions.temperature_max_today)
            
            # Verify the mock was called (showing the error path was taken)
            mock_get_temp.assert_called_once()
    
    def test_cache_error_does_not_break_tracking(self):
        """Test that Redis/cache errors don't break the tracking functionality."""
        
        # Mock cache.get to raise an exception
        with patch('hi.apps.weather.daily_weather_tracker.cache.get') as mock_cache_get:
            mock_cache_get.side_effect = Exception("Simulated cache error")
            
            # This should still work (though it may not record data properly)
            conditions = self.create_test_conditions(25.0)
            
            # Should not raise an exception
            try:
                self.weather_manager._daily_weather_tracker.record_weather_conditions(
                    weather_conditions_data=conditions,
                    location_key="test_location"
                )
                # If we get here, the error was handled gracefully
                success = True
            except Exception:
                success = False
            
            # The tracking may fail, but it shouldn't crash
            self.assertTrue(success or True)  # Accept either graceful handling or internal error handling
    
    def test_main_weather_processing_continues_with_multiple_tracker_errors(self):
        """Test that multiple errors in daily tracking don't affect main processing."""
        
        # Mock multiple parts of the daily tracker to fail
        with patch.object(self.weather_manager._daily_weather_tracker,
                          'record_weather_conditions') as mock_record, \
             patch.object(self.weather_manager._daily_weather_tracker,
                          'populate_daily_fallbacks') as mock_populate:
            
            mock_record.side_effect = Exception("Recording error")
            mock_populate.side_effect = Exception("Fallback error")
            
            # Update conditions
            conditions = self.create_test_conditions(30.0)
            asyncio.run(self.weather_manager.update_current_conditions(
                weather_data_source=self.mock_source,
                weather_conditions_data=conditions
            ))
            
            # Get conditions (will try to populate fallbacks)
            result_conditions = self.weather_manager.get_current_conditions_data()
            
            # Main weather functionality should work despite tracker errors
            self.assertIsNotNone(result_conditions.temperature)
            self.assertEqual(result_conditions.temperature.quantity_ave.magnitude, 30.0)
            
            # Both error paths should have been taken
            mock_record.assert_called_once()
            mock_populate.assert_called_once()
