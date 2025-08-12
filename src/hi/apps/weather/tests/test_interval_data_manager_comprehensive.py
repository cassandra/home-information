import logging
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.interval_data_manager import IntervalDataManager
from hi.apps.weather.transient_models import (
    DataPointSource,
    IntervalEnvironmentalData,
    NumericDataPoint,
    StringDataPoint,
    BooleanDataPoint,
    TimeDataPoint,
    TimeInterval,
    WeatherForecastData,
    WeatherHistoryData,
    Station,
)
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestIntervalDataManagerComprehensive(BaseTestCase):
    """Comprehensive test suite for IntervalDataManager focusing on weather-specific scenarios."""

    def setUp(self):
        """Set up test data and sources."""
        
        # Primary high-priority source (NWS)
        self.primary_source = DataPointSource(
            id='nws',
            label='National Weather Service',
            abbreviation='NWS',
            priority=1
        )
        
        # Secondary lower-priority source (OpenMeteo)
        self.secondary_source = DataPointSource(
            id='openmeteo',
            label='Open-Meteo',
            abbreviation='OpenMeteo',
            priority=2
        )
        
        # Test station
        self.test_station = Station(
            source=self.primary_source,
            station_id='TEST001',
            name='Test Weather Station'
        )
        
        return

    def create_weather_forecast_data(self, temperature_c=None, humidity_pct=None, description=None, is_daytime=None, source_datetime=None, station=None):
        """Helper to create WeatherForecastData with test values."""
        if not station:
            station = self.test_station
        if not source_datetime:
            source_datetime = datetimeproxy.now()
            
        forecast_data = WeatherForecastData()
        
        if temperature_c is not None:
            forecast_data.temperature = NumericDataPoint(
                station=station,
                source_datetime=source_datetime,
                quantity_ave=UnitQuantity(temperature_c, 'degC')
            )
            
        if humidity_pct is not None:
            forecast_data.relative_humidity = NumericDataPoint(
                station=station,
                source_datetime=source_datetime,
                quantity_ave=UnitQuantity(humidity_pct, 'percent')
            )
            
        if description is not None:
            forecast_data.description_short = StringDataPoint(
                station=station,
                source_datetime=source_datetime,
                value=description
            )
            
        if is_daytime is not None:
            forecast_data.is_daytime = BooleanDataPoint(
                station=station,
                source_datetime=source_datetime,
                value=is_daytime
            )
            
        return forecast_data

    def create_interval_weather_forecast(self, start_time, end_time, weather_data):
        """Helper to create IntervalEnvironmentalData with WeatherForecastData."""
        time_interval = TimeInterval(start=start_time, end=end_time)
        return IntervalEnvironmentalData(
            interval=time_interval,
            data=weather_data
        )

    @patch('hi.apps.common.datetimeproxy.now')
    def test_hourly_forecast_realistic_scenario(self, mock_now):
        """Test hourly forecast aggregation with realistic weather data."""
        # Mock current time: 2024-01-15 14:30:00
        current_time = datetime(2024, 1, 15, 14, 30, 0)
        mock_now.return_value = current_time
        
        # Create hourly forecast manager (like WeatherManager uses)
        manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=12,  # 12 hours of forecast
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        manager.ensure_initialized()
        
        # Verify intervals were created correctly  
        self.assertEqual(len(manager._aggregated_interval_data_list), 12)
        first_interval = manager._aggregated_interval_data_list[0].interval_data.interval
        self.assertEqual(first_interval.start, datetime(2024, 1, 15, 14, 0, 0))  # Rounded down to hour
        self.assertEqual(first_interval.end, datetime(2024, 1, 15, 15, 0, 0))
        
        # Create overlapping hourly forecast data from primary source
        source_intervals = [
            # 2-hour forecast: 14:00-16:00 from NWS
            self.create_interval_weather_forecast(
                start_time=datetime(2024, 1, 15, 14, 0, 0),
                end_time=datetime(2024, 1, 15, 16, 0, 0),
                weather_data=self.create_weather_forecast_data(
                    temperature_c=22.0,
                    humidity_pct=65,
                    description="Partly Cloudy",
                    is_daytime=True
                )
            ),
            # Next 2-hour forecast: 16:00-18:00 from NWS
            self.create_interval_weather_forecast(
                start_time=datetime(2024, 1, 15, 16, 0, 0),
                end_time=datetime(2024, 1, 15, 18, 0, 0),
                weather_data=self.create_weather_forecast_data(
                    temperature_c=20.0,
                    humidity_pct=70,
                    description="Cloudy",
                    is_daytime=True
                )
            )
        ]
        
        # Add the forecast data
        manager.add_data(
            data_point_source=self.primary_source,
            new_interval_data_list=source_intervals
        )
        
        # Verify first aggregated interval got data from first source interval
        first_aggregated = manager._aggregated_interval_data_list[0]
        self.assertIsNotNone(first_aggregated.interval_data.data.temperature)
        self.assertEqual(first_aggregated.interval_data.data.temperature.quantity_ave.magnitude, 22.0)
        self.assertEqual(first_aggregated.interval_data.data.description_short.value, "Partly Cloudy")
        
        # Verify second aggregated interval also got data from first source interval (overlap)
        second_aggregated = manager._aggregated_interval_data_list[1] 
        self.assertIsNotNone(second_aggregated.interval_data.data.temperature)
        self.assertEqual(second_aggregated.interval_data.data.temperature.quantity_ave.magnitude, 22.0)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_daily_history_realistic_scenario(self, mock_now):
        """Test daily history aggregation with realistic weather data."""
        # Mock current time: 2024-01-15 14:30:00
        current_time = datetime(2024, 1, 15, 14, 30, 0)
        mock_now.return_value = current_time
        
        # Create daily history manager (like WeatherManager uses)
        manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=7,  # 7 days of history
            is_order_ascending=False,  # Historical data goes backwards
            data_class=WeatherHistoryData
        )
        
        manager.ensure_initialized()
        
        # Verify intervals were created correctly for history
        self.assertEqual(len(manager._aggregated_interval_data_list), 7)
        
        # First interval should be most recent 24h period (yesterday)
        first_interval = manager._aggregated_interval_data_list[0].interval_data.interval
        # Should be from Jan 14 00:00 to Jan 15 00:00
        self.assertEqual(first_interval.start, datetime(2024, 1, 14, 0, 0, 0))
        self.assertEqual(first_interval.end, datetime(2024, 1, 15, 0, 0, 0))
        
        # Create historical data (daily summary from yesterday)
        yesterday_data = WeatherHistoryData()
        yesterday_data.temperature = NumericDataPoint(
            station=self.test_station,
            source_datetime=datetime(2024, 1, 14, 12, 0, 0),  # Noon yesterday
            quantity_min=UnitQuantity(15.0, 'degC'),
            quantity_ave=UnitQuantity(18.0, 'degC'), 
            quantity_max=UnitQuantity(21.0, 'degC')
        )
        
        source_interval = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 14, 0, 0, 0),
            end_time=datetime(2024, 1, 15, 0, 0, 0),
            weather_data=yesterday_data
        )
        
        # Add the history data
        manager.add_data(
            data_point_source=self.primary_source,
            new_interval_data_list=[source_interval]
        )
        
        # Verify aggregated data
        first_aggregated = manager._aggregated_interval_data_list[0]
        self.assertIsNotNone(first_aggregated.interval_data.data.temperature)
        self.assertEqual(first_aggregated.interval_data.data.temperature.quantity_ave.magnitude, 18.0)
        self.assertEqual(first_aggregated.interval_data.data.temperature.quantity_min.magnitude, 15.0)
        self.assertEqual(first_aggregated.interval_data.data.temperature.quantity_max.magnitude, 21.0)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_multiple_source_priority_handling(self, mock_now):
        """Test handling of multiple sources with different priorities."""
        current_time = datetime(2024, 1, 15, 14, 30, 0)
        mock_now.return_value = current_time
        
        manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=3,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        manager.ensure_initialized()
        
        # Add data from lower priority source first
        openmeteo_data = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 15, 14, 0, 0),
            end_time=datetime(2024, 1, 15, 15, 0, 0),
            weather_data=self.create_weather_forecast_data(
                temperature_c=20.0,
                description="OpenMeteo Forecast"
            )
        )
        
        manager.add_data(
            data_point_source=self.secondary_source,  # Priority 2 (lower)
            new_interval_data_list=[openmeteo_data]
        )
        
        # Verify OpenMeteo data is present
        first_aggregated = manager._aggregated_interval_data_list[0]
        self.assertEqual(first_aggregated.interval_data.data.temperature.quantity_ave.magnitude, 20.0)
        self.assertEqual(first_aggregated.interval_data.data.description_short.value, "OpenMeteo Forecast")
        
        # Now add data from higher priority source (should override)
        nws_data = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 15, 14, 0, 0),
            end_time=datetime(2024, 1, 15, 15, 0, 0),
            weather_data=self.create_weather_forecast_data(
                temperature_c=23.0,
                description="NWS Forecast"
            )
        )
        
        manager.add_data(
            data_point_source=self.primary_source,  # Priority 1 (higher)
            new_interval_data_list=[nws_data]
        )
        
        # Verify NWS data has overridden OpenMeteo data
        first_aggregated = manager._aggregated_interval_data_list[0]
        self.assertEqual(first_aggregated.interval_data.data.temperature.quantity_ave.magnitude, 23.0)
        self.assertEqual(first_aggregated.interval_data.data.description_short.value, "NWS Forecast")

    @patch('hi.apps.common.datetimeproxy.now')
    def test_partial_interval_overlap_aggregation(self, mock_now):
        """Test aggregation when source intervals partially overlap target intervals."""
        current_time = datetime(2024, 1, 15, 14, 30, 0)
        mock_now.return_value = current_time
        
        manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=3,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        manager.ensure_initialized()
        
        # Create source data that spans multiple target intervals
        # 14:30-16:30 source interval should overlap with:
        # - 14:00-15:00 (30 min overlap)
        # - 15:00-16:00 (60 min overlap) 
        # - 16:00-17:00 (30 min overlap)
        source_data = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 15, 14, 30, 0),
            end_time=datetime(2024, 1, 15, 16, 30, 0),
            weather_data=self.create_weather_forecast_data(
                temperature_c=25.0,
                humidity_pct=60,
                is_daytime=True
            )
        )
        
        manager.add_data(
            data_point_source=self.primary_source,
            new_interval_data_list=[source_data]
        )
        
        # All three intervals should have received the data
        for i in range(3):
            aggregated = manager._aggregated_interval_data_list[i]
            self.assertIsNotNone(aggregated.interval_data.data.temperature)
            self.assertEqual(aggregated.interval_data.data.temperature.quantity_ave.magnitude, 25.0)
            self.assertEqual(aggregated.interval_data.data.relative_humidity.quantity_ave.magnitude, 60)
            self.assertTrue(aggregated.interval_data.data.is_daytime.value)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_time_boundary_edge_cases(self, mock_now):
        """Test edge cases around time boundaries and interval calculations."""
        
        # Test case 1: Exactly at hour boundary
        mock_now.return_value = datetime(2024, 1, 15, 15, 0, 0)  # Exactly 3 PM
        
        manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=2,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        manager.ensure_initialized()
        
        # First interval should start at 15:00 (current hour)
        first_interval = manager._aggregated_interval_data_list[0].interval_data.interval
        self.assertEqual(first_interval.start, datetime(2024, 1, 15, 15, 0, 0))
        self.assertEqual(first_interval.end, datetime(2024, 1, 15, 16, 0, 0))
        
        # Test case 2: End of day rollover for daily intervals
        mock_now.return_value = datetime(2024, 1, 15, 23, 59, 59)  # Almost midnight
        
        daily_manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=2,
            is_order_ascending=False,  # History
            data_class=WeatherHistoryData
        )
        
        daily_manager.ensure_initialized()
        
        # Should handle day boundary correctly
        intervals = daily_manager._get_calculated_intervals()
        self.assertEqual(len(intervals), 2)
        
        # Most recent 24h period should be from yesterday midnight to today midnight  
        first_interval = intervals[0]
        self.assertEqual(first_interval.start, datetime(2024, 1, 14, 0, 0, 0))
        self.assertEqual(first_interval.end, datetime(2024, 1, 15, 0, 0, 0))

    @patch('hi.apps.common.datetimeproxy.now')
    def test_complex_multi_source_aggregation(self, mock_now):
        """Test complex scenario with multiple overlapping sources and intervals."""
        current_time = datetime(2024, 1, 15, 14, 30, 0)
        mock_now.return_value = current_time
        
        manager = IntervalDataManager(
            interval_hours=2,  # 2-hour intervals 
            max_interval_count=3,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        manager.ensure_initialized()
        
        # Expected intervals: 14:00-16:00, 16:00-18:00, 18:00-20:00
        
        # Add data from multiple sources with different coverage
        
        # NWS provides 6-hour forecast: 14:00-20:00
        nws_data = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 15, 14, 0, 0),
            end_time=datetime(2024, 1, 15, 20, 0, 0),
            weather_data=self.create_weather_forecast_data(
                temperature_c=22.0,
                description="NWS 6h Forecast"
            )
        )
        
        # OpenMeteo provides 3-hour forecast: 15:00-18:00 (overlapping)
        openmeteo_data = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 15, 15, 0, 0),
            end_time=datetime(2024, 1, 15, 18, 0, 0),
            weather_data=self.create_weather_forecast_data(
                temperature_c=21.0,  # Slightly different
                humidity_pct=75     # Additional data NWS doesn't provide
            )
        )
        
        # Add NWS data first (higher priority)
        manager.add_data(
            data_point_source=self.primary_source,
            new_interval_data_list=[nws_data]
        )
        
        # Add OpenMeteo data (should not override temperature due to lower priority)
        manager.add_data(
            data_point_source=self.secondary_source,
            new_interval_data_list=[openmeteo_data]
        )
        
        # Verify aggregation results
        
        # First interval (14:00-16:00): Should have NWS temperature, OpenMeteo humidity (from overlap 15:00-16:00)
        first_agg = manager._aggregated_interval_data_list[0]
        self.assertEqual(first_agg.interval_data.data.temperature.quantity_ave.magnitude, 22.0)
        self.assertEqual(first_agg.interval_data.data.description_short.value, "NWS 6h Forecast")
        self.assertEqual(first_agg.interval_data.data.relative_humidity.quantity_ave.magnitude, 75)  # OpenMeteo fills gap
        
        # Second interval (16:00-18:00): Should have NWS temperature, OpenMeteo humidity
        second_agg = manager._aggregated_interval_data_list[1]
        self.assertEqual(second_agg.interval_data.data.temperature.quantity_ave.magnitude, 22.0)  # NWS wins
        self.assertEqual(second_agg.interval_data.data.relative_humidity.quantity_ave.magnitude, 75)  # OpenMeteo fills gap
        
        # Third interval (18:00-20:00): Should have only NWS data
        third_agg = manager._aggregated_interval_data_list[2]
        self.assertEqual(third_agg.interval_data.data.temperature.quantity_ave.magnitude, 22.0)
        self.assertIsNone(third_agg.interval_data.data.relative_humidity)  # OpenMeteo doesn't cover this period

    @patch('hi.apps.common.datetimeproxy.now')
    def test_interval_update_with_time_advancement(self, mock_now):
        """Test that intervals correctly update as time advances."""
        # Start at 14:30
        mock_now.return_value = datetime(2024, 1, 15, 14, 30, 0)
        
        manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=3,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        manager.ensure_initialized()
        
        # Initial intervals: 14:00-15:00, 15:00-16:00, 16:00-17:00
        initial_intervals = [agg.interval_data.interval for agg in manager._aggregated_interval_data_list]
        self.assertEqual(initial_intervals[0].start, datetime(2024, 1, 15, 14, 0, 0))
        self.assertEqual(initial_intervals[2].end, datetime(2024, 1, 15, 17, 0, 0))
        
        # Add some data to first interval
        source_data = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 15, 14, 0, 0),
            end_time=datetime(2024, 1, 15, 15, 0, 0),
            weather_data=self.create_weather_forecast_data(temperature_c=20.0)
        )
        
        manager.add_data(
            data_point_source=self.primary_source,
            new_interval_data_list=[source_data]
        )
        
        # Verify data is present
        self.assertIsNotNone(manager._aggregated_interval_data_list[0].interval_data.data.temperature)
        
        # Advance time by 2 hours
        mock_now.return_value = datetime(2024, 1, 15, 16, 30, 0)
        
        # Update intervals (simulating what happens in real use)
        manager._update_intervals()
        
        # Intervals should have shifted: 16:00-17:00, 17:00-18:00, 18:00-19:00
        new_intervals = [agg.interval_data.interval for agg in manager._aggregated_interval_data_list]
        self.assertEqual(new_intervals[0].start, datetime(2024, 1, 15, 16, 0, 0))
        self.assertEqual(new_intervals[2].end, datetime(2024, 1, 15, 19, 0, 0))
        
        # Old data from 14:00-15:00 interval should be gone (outside window)
        # All intervals should have fresh, empty data
        for agg in manager._aggregated_interval_data_list:
            self.assertIsNone(agg.interval_data.data.temperature)

    def test_empty_and_null_data_handling(self):
        """Test handling of empty intervals and null data points."""
        manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=2,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        with patch('hi.apps.common.datetimeproxy.now', 
                  return_value=datetime(2024, 1, 15, 14, 30, 0)):
            manager.ensure_initialized()
            
            # Add empty interval data list
            manager.add_data(
                data_point_source=self.primary_source,
                new_interval_data_list=[]  # Empty list
            )
            
            # Should not crash, intervals should remain empty
            for agg in manager._aggregated_interval_data_list:
                self.assertIsNone(agg.interval_data.data.temperature)
            
            # Add interval with null/None data points
            forecast_data = WeatherForecastData()  # All fields None
            
            source_interval = self.create_interval_weather_forecast(
                start_time=datetime(2024, 1, 15, 14, 0, 0),
                end_time=datetime(2024, 1, 15, 15, 0, 0),
                weather_data=forecast_data
            )
            
            manager.add_data(
                data_point_source=self.primary_source,
                new_interval_data_list=[source_interval]
            )
            
            # Should handle gracefully - no data should be set
            first_agg = manager._aggregated_interval_data_list[0]
            self.assertIsNone(first_agg.interval_data.data.temperature)
            self.assertIsNone(first_agg.interval_data.data.relative_humidity)

    @patch('hi.apps.common.datetimeproxy.now')
    def test_nws_12hour_to_daily_aggregation_scenario(self, mock_now):
        """Test NWS-style 12-hour forecast aggregation into daily intervals (real world scenario)."""
        current_time = datetime(2024, 1, 15, 10, 0, 0)  # 10 AM
        mock_now.return_value = current_time
        
        # Daily forecast manager
        manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=5,  # 5 days of forecast
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        manager.ensure_initialized()
        
        # Simulate NWS 12-hour forecast periods that need to be aggregated into daily forecasts
        
        # Today afternoon: 10:00-22:00 (12 hours)
        today_afternoon = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 22, 0, 0),
            weather_data=self.create_weather_forecast_data(
                temperature_c=22.0,
                humidity_pct=60,
                description="Sunny",
                is_daytime=True
            )
        )
        
        # Tonight: 22:00 today to 10:00 tomorrow (12 hours)
        tonight = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 15, 22, 0, 0),
            end_time=datetime(2024, 1, 16, 10, 0, 0),
            weather_data=self.create_weather_forecast_data(
                temperature_c=10.0,
                humidity_pct=80,
                description="Clear",
                is_daytime=False
            )
        )
        
        # Tomorrow afternoon: 10:00-22:00 (12 hours)
        tomorrow_afternoon = self.create_interval_weather_forecast(
            start_time=datetime(2024, 1, 16, 10, 0, 0),
            end_time=datetime(2024, 1, 16, 22, 0, 0),
            weather_data=self.create_weather_forecast_data(
                temperature_c=25.0,
                humidity_pct=55,
                description="Partly Cloudy",
                is_daytime=True
            )
        )
        
        # Add all NWS 12-hour periods
        manager.add_data(
            data_point_source=self.primary_source,
            new_interval_data_list=[today_afternoon, tonight, tomorrow_afternoon]
        )
        
        # Verify daily aggregation results
        
        # Today (Jan 15): Should aggregate today afternoon + tonight
        today_daily = manager._aggregated_interval_data_list[0] 
        today_interval = today_daily.interval_data.interval
        self.assertEqual(today_interval.start, datetime(2024, 1, 15, 0, 0, 0))
        self.assertEqual(today_interval.end, datetime(2024, 1, 16, 0, 0, 0))
        
        # Should have aggregated data from both 12-hour periods
        self.assertIsNotNone(today_daily.interval_data.data.temperature)
        # Temperature should be time-weighted average of 22°C (12h) and 10°C (2h overlap)
        # The algorithm will weight by overlap duration with the daily interval
        
        # Tomorrow (Jan 16): Should have tomorrow afternoon data
        tomorrow_daily = manager._aggregated_interval_data_list[1]
        tomorrow_interval = tomorrow_daily.interval_data.interval
        self.assertEqual(tomorrow_interval.start, datetime(2024, 1, 16, 0, 0, 0))
        self.assertEqual(tomorrow_interval.end, datetime(2024, 1, 17, 0, 0, 0))
        
        # Should have data from tonight (partial) and tomorrow afternoon
        self.assertIsNotNone(tomorrow_daily.interval_data.data.temperature)
        
        # Description should be from interval with longest overlap (tomorrow afternoon for tomorrow's daily)
        # Since tomorrow afternoon (12h) overlaps more with tomorrow's daily than tonight (10h)
        self.assertEqual(tomorrow_daily.interval_data.data.description_short.value, "Partly Cloudy")

    def test_source_field_data_structure_bug_reproduction(self):
        """Test to reproduce the suspected bug in AggregatedWeatherData.from_time_interval()."""
        
        # Create a manager and initialize it to trigger the from_time_interval method
        manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=1,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        with patch('hi.apps.common.datetimeproxy.now', 
                  return_value=datetime(2024, 1, 15, 14, 30, 0)):
            
            manager.ensure_initialized()
            
            # Get the aggregated data that was created
            agg_data = manager._aggregated_interval_data_list[0]
            
            # Check that source_data was properly initialized for DataPoint fields
            # This should expose the bug in from_time_interval() if present
            self.assertIsNotNone(agg_data.source_data)
            self.assertIsInstance(agg_data.source_data, dict)
            
            # These fields should exist in source_data if initialization worked correctly
            forecast_fields = ['temperature', 'relative_humidity', 'description_short', 'is_daytime']
            
            for field_name in forecast_fields:
                self.assertIn(field_name, agg_data.source_data, 
                             f"Field {field_name} missing from source_data - initialization bug detected")
                self.assertIsNotNone(agg_data.source_data[field_name],
                                   f"Field {field_name} is None in source_data - initialization bug detected")


if __name__ == '__main__':
    unittest.main()