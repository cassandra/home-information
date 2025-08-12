import logging
from datetime import datetime
import unittest
from unittest.mock import patch

from hi.apps.weather.aggregated_weather_data import AggregatedWeatherData
from hi.apps.weather.transient_models import (
    BooleanDataPoint,
    DataPointSource,
    IntervalEnvironmentalData,
    NumericDataPoint,
    StringDataPoint,
    TimeDataPoint,
    TimeInterval,
    WeatherForecastData,
)
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAggregatedWeatherData(BaseTestCase):
    """Test the AggregatedWeatherData class for single interval aggregation."""

    def setUp(self):
        """Set up test data."""
        self.test_source_high_priority = DataPointSource(
            id='high_priority',
            label='High Priority Source',
            abbreviation='HIGH',
            priority=1
        )
        
        self.test_source_low_priority = DataPointSource(
            id='low_priority', 
            label='Low Priority Source',
            abbreviation='LOW',
            priority=2
        )
        
        self.test_interval = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 13, 0, 0)
        )
        
        self.forecast_data = WeatherForecastData()
        
        self.interval_data = IntervalEnvironmentalData(
            interval=self.test_interval,
            data=self.forecast_data
        )
        
        self.aggregated_data = AggregatedWeatherData(
            interval_data=self.interval_data,
            source_data={},
            data_class=WeatherForecastData
        )
        return

    def test_aggregated_weather_data_initialization(self):
        """Test AggregatedWeatherData initialization."""
        self.assertEqual(self.aggregated_data.interval_data, self.interval_data)
        self.assertEqual(self.aggregated_data.data_class, WeatherForecastData)
        self.assertEqual(self.aggregated_data.source_data, {})
        return

    def test_from_time_interval_class_method(self):
        """Test AggregatedWeatherData.from_time_interval() class method."""
        aggregated_data = AggregatedWeatherData.from_time_interval(
            time_interval=self.test_interval,
            data_class=WeatherForecastData
        )
        
        self.assertIsInstance(aggregated_data, AggregatedWeatherData)
        self.assertEqual(aggregated_data.interval_data.interval, self.test_interval)
        
        # Verify source_data is properly initialized with SourceFieldData for each DataPoint field
        self.assertIsInstance(aggregated_data.source_data, dict)
        self.assertGreater(len(aggregated_data.source_data), 0)  # Should have DataPoint fields
        
        # Check that all expected WeatherForecastData DataPoint fields are initialized
        expected_fields = ['description_short', 'temperature', 'relative_humidity', 'is_daytime']
        for field_name in expected_fields:
            self.assertIn(field_name, aggregated_data.source_data)
            self.assertIsNotNone(aggregated_data.source_data[field_name])
        return

    def test_numeric_data_point_aggregation(self):
        """Test aggregation of numeric data points with time weighting."""
        # Create test intervals and data points
        interval1 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 12, 30, 0)  # 30 minutes
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 30, 0), 
            end=datetime(2024, 1, 1, 13, 0, 0)   # 30 minutes
        )
        
        data_point1 = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 15, 0),
            quantity_ave=UnitQuantity(20.0, 'degC'),
            quantity_min=UnitQuantity(18.0, 'degC'),
            quantity_max=UnitQuantity(22.0, 'degC')
        )
        
        data_point2 = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 45, 0),
            quantity_ave=UnitQuantity(30.0, 'degC'),
            quantity_min=UnitQuantity(28.0, 'degC'),
            quantity_max=UnitQuantity(32.0, 'degC')
        )
        
        interval_data_point_map = {
            interval1: data_point1,
            interval2: data_point2
        }
        
        # Mock the interval overlap calculation 
        with patch('hi.apps.weather.transient_models.TimeInterval.overlap_seconds', 
                   return_value=1800.0):  # 30 minutes = 1800 seconds
            
            result = self.aggregated_data.aggregate_numeric_data_points(interval_data_point_map)
            
            # Should be time-weighted average: (20*1800 + 30*1800) / (1800+1800) = 25.0
            self.assertEqual(result.quantity_ave.magnitude, 25.0)
            self.assertEqual(result.quantity_ave.units, 'degree_Celsius')
            self.assertEqual(result.quantity_min.magnitude, 18.0)  # Minimum of mins
            self.assertEqual(result.quantity_max.magnitude, 32.0)  # Maximum of maxs
        return

    def test_boolean_data_point_aggregation(self):
        """Test aggregation of boolean data points with duration weighting."""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 12, 30, 0)
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 30, 0),
            end=datetime(2024, 1, 1, 13, 0, 0)
        )
        
        data_point1 = BooleanDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 15, 0),
            value=True
        )
        
        data_point2 = BooleanDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 45, 0),
            value=False
        )
        
        interval_data_point_map = {
            interval1: data_point1,
            interval2: data_point2
        }
        
        # Mock equal overlap duration for both intervals
        with patch('hi.apps.weather.transient_models.TimeInterval.overlap_seconds',
                   return_value=1800.0):  # 30 minutes each
            
            result = self.aggregated_data.aggregate_boolean_data_points(interval_data_point_map)
            
            # Equal duration, so should be False (ties go to False)
            self.assertFalse(result.value)
        return

    def test_boolean_data_point_aggregation_true_majority(self):
        """Test boolean aggregation when True has longer duration."""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 12, 40, 0)  # 40 minutes
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 40, 0),
            end=datetime(2024, 1, 1, 13, 0, 0)   # 20 minutes
        )
        
        data_point1 = BooleanDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 20, 0),
            value=True
        )
        
        data_point2 = BooleanDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 50, 0),
            value=False
        )
        
        interval_data_point_map = {
            interval1: data_point1,
            interval2: data_point2
        }
        
        # Mock different overlap durations
        def mock_overlap_seconds(self, other):
            return 2400.0 if other == interval1 else 1200.0
        
        with patch('hi.apps.weather.transient_models.TimeInterval.overlap_seconds', mock_overlap_seconds):
            
            result = self.aggregated_data.aggregate_boolean_data_points(interval_data_point_map)
            
            # True has longer duration (40 min vs 20 min)
            self.assertTrue(result.value)
        return

    def test_string_data_point_aggregation(self):
        """Test aggregation of string data points (longest duration wins)."""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 12, 20, 0)  # 20 minutes
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 20, 0),
            end=datetime(2024, 1, 1, 13, 0, 0)   # 40 minutes
        )
        
        data_point1 = StringDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 10, 0),
            value="Partly Cloudy"
        )
        
        data_point2 = StringDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 40, 0),
            value="Mostly Sunny"
        )
        
        interval_data_point_map = {
            interval1: data_point1,
            interval2: data_point2
        }
        
        # Mock overlap durations - interval2 has longer duration
        def mock_overlap_seconds(self, other):
            return 1200.0 if other == interval1 else 2400.0
        
        with patch('hi.apps.weather.transient_models.TimeInterval.overlap_seconds', mock_overlap_seconds):
            
            result = self.aggregated_data.aggregate_string_data_points(interval_data_point_map)
            
            # Longest duration wins
            self.assertEqual(result.value, "Mostly Sunny")
        return

    def test_time_data_point_aggregation(self):
        """Test aggregation of time data points (longest duration wins)."""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 12, 20, 0)
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 20, 0),
            end=datetime(2024, 1, 1, 13, 0, 0)
        )
        
        from datetime import time
        
        data_point1 = TimeDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 10, 0),
            value=time(6, 30, 0)  # 6:30 AM
        )
        
        data_point2 = TimeDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 40, 0),
            value=time(7, 15, 0)  # 7:15 AM
        )
        
        interval_data_point_map = {
            interval1: data_point1,
            interval2: data_point2
        }
        
        # Mock overlap durations - interval2 has longer duration
        def mock_overlap_seconds(self, other):
            return 1200.0 if other == interval1 else 2400.0
        
        with patch('hi.apps.weather.transient_models.TimeInterval.overlap_seconds', mock_overlap_seconds):
            
            result = self.aggregated_data.aggregate_time_data_points(interval_data_point_map)
            
            # Longest duration wins
            self.assertEqual(result.value, time(7, 15, 0))
        return

    def test_numeric_aggregation_single_data_point(self):
        """Test numeric aggregation with only one data point."""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 13, 0, 0)
        )
        
        data_point1 = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 30, 0),
            quantity_ave=UnitQuantity(25.0, 'degC'),
            quantity_min=UnitQuantity(23.0, 'degC'),
            quantity_max=UnitQuantity(27.0, 'degC')
        )
        
        interval_data_point_map = {interval1: data_point1}
        
        with patch('hi.apps.weather.transient_models.TimeInterval.overlap_seconds',
                   return_value=3600.0):  # 1 hour
            
            result = self.aggregated_data.aggregate_numeric_data_points(interval_data_point_map)
            
            # Should return the original values
            self.assertEqual(result.quantity_ave.magnitude, 25.0)
            self.assertEqual(result.quantity_min.magnitude, 23.0)
            self.assertEqual(result.quantity_max.magnitude, 27.0)
        return

    def test_numeric_aggregation_with_none_values(self):
        """Test numeric aggregation handling None min/max values."""
        interval1 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 12, 30, 0)
        )
        interval2 = TimeInterval(
            start=datetime(2024, 1, 1, 12, 30, 0),
            end=datetime(2024, 1, 1, 13, 0, 0)
        )
        
        # Data point with only average, no min/max
        data_point1 = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 15, 0),
            quantity_ave=UnitQuantity(20.0, 'degC')
        )
        
        # Data point with min/max
        data_point2 = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 45, 0),
            quantity_ave=UnitQuantity(30.0, 'degC'),
            quantity_min=UnitQuantity(28.0, 'degC'),
            quantity_max=UnitQuantity(32.0, 'degC')
        )
        
        interval_data_point_map = {
            interval1: data_point1,
            interval2: data_point2
        }
        
        with patch('hi.apps.weather.transient_models.TimeInterval.overlap_seconds',
                   return_value=1800.0):
            
            result = self.aggregated_data.aggregate_numeric_data_points(interval_data_point_map)
            
            # Should handle None values gracefully
            self.assertEqual(result.quantity_ave.magnitude, 25.0)  # Average of 20 and 30
            self.assertEqual(result.quantity_min.magnitude, 20.0)  # Min of 20.0 and 28.0 = 20.0
            self.assertEqual(result.quantity_max.magnitude, 32.0)  # Max of 20.0 and 32.0 = 32.0
        return

    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_best_data_point_source_by_priority(self, mock_now):
        """Test data source selection based on priority."""
        mock_now.return_value = datetime(2024, 1, 1, 13, 0, 0)
        
        # Create mock source map
        from hi.apps.weather.interval_models import IntervalDataPoints
        
        high_priority_intervals = IntervalDataPoints()
        low_priority_intervals = IntervalDataPoints()
        
        # Both sources have fresh data
        fresh_data_point = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 30, 0),  # 30 minutes ago (fresh)
            quantity_ave=UnitQuantity(25.0, 'degC')
        )
        
        high_priority_intervals[self.test_interval] = fresh_data_point
        low_priority_intervals[self.test_interval] = fresh_data_point
        
        source_map = {
            self.test_source_high_priority: high_priority_intervals,
            self.test_source_low_priority: low_priority_intervals
        }
        
        result = self.aggregated_data.get_best_data_point_source(source_map)
        
        # Should select high priority source when both are fresh
        self.assertEqual(result, self.test_source_high_priority)
        return

    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_best_data_point_source_by_freshness(self, mock_now):
        """Test data source selection based on data freshness when priority source is stale."""
        mock_now.return_value = datetime(2024, 1, 1, 16, 0, 0)  # 4 hours later
        
        from hi.apps.weather.interval_models import IntervalDataPoints
        
        high_priority_intervals = IntervalDataPoints()
        low_priority_intervals = IntervalDataPoints()
        
        # High priority source has stale data (4 hours old)
        stale_data_point = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 12, 0, 0),  # 4 hours ago (stale)
            quantity_ave=UnitQuantity(20.0, 'degC')
        )
        
        # Low priority source has fresh data (30 minutes old)
        fresh_data_point = NumericDataPoint(
            station=None,
            source_datetime=datetime(2024, 1, 1, 15, 30, 0),  # 30 minutes ago (fresh)
            quantity_ave=UnitQuantity(25.0, 'degC')
        )
        
        high_priority_intervals[self.test_interval] = stale_data_point
        low_priority_intervals[self.test_interval] = fresh_data_point
        
        source_map = {
            self.test_source_high_priority: high_priority_intervals,
            self.test_source_low_priority: low_priority_intervals
        }
        
        result = self.aggregated_data.get_best_data_point_source(source_map)
        
        # Should select low priority source when it has fresh data and high priority is stale
        self.assertEqual(result, self.test_source_low_priority)
        return


if __name__ == '__main__':
    unittest.main()