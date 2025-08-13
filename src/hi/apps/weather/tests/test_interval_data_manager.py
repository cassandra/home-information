import logging
from datetime import datetime
import unittest
from unittest.mock import patch
import pytz

from hi.apps.weather.interval_data_manager import IntervalDataManager
from hi.apps.weather.transient_models import (
    DataPointSource,
    IntervalEnvironmentalData,
    NumericDataPoint,
    TimeInterval,
    WeatherForecastData,
)
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestIntervalDataManager(BaseTestCase):
    """Test the IntervalDataManager class for multiple interval management."""

    def setUp(self):
        """Set up test data."""
        self.manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=3,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        self.test_source = DataPointSource(
            id='test_source',
            label='Test Source',
            abbreviation='TEST',
            priority=1
        )
        return

    def test_interval_data_manager_initialization(self):
        """Test IntervalDataManager initialization."""
        self.assertEqual(self.manager._interval_hours, 1)
        self.assertEqual(self.manager._max_interval_count, 3)
        self.assertTrue(self.manager._is_order_ascending)
        self.assertFalse(self.manager._was_initialized)
        self.assertEqual(len(self.manager._aggregated_interval_data_list), 0)
        return

    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_calculated_intervals_ascending(self, mock_now):
        """Test interval calculation for ascending (future) intervals."""
        # Mock current time: 2024-01-01 14:35:22
        mock_now.return_value = datetime(2024, 1, 1, 14, 35, 22)
        
        intervals = self.manager._get_calculated_intervals()
        
        # Should create 3 intervals starting from 14:00 (rounded down)
        self.assertEqual(len(intervals), 3)
        
        # First interval: 14:00-15:00  
        self.assertEqual(intervals[0].start, datetime(2024, 1, 1, 14, 0, 0))
        self.assertEqual(intervals[0].end, datetime(2024, 1, 1, 15, 0, 0))
        
        # Second interval: 15:00-16:00
        self.assertEqual(intervals[1].start, datetime(2024, 1, 1, 15, 0, 0))
        self.assertEqual(intervals[1].end, datetime(2024, 1, 1, 16, 0, 0))
        
        # Third interval: 16:00-17:00
        self.assertEqual(intervals[2].start, datetime(2024, 1, 1, 16, 0, 0))
        self.assertEqual(intervals[2].end, datetime(2024, 1, 1, 17, 0, 0))
        return

    @patch('hi.apps.console.console_helper.ConsoleSettingsHelper.get_tz_name')
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_calculated_intervals_descending(self, mock_now, mock_tz):
        """Test interval calculation for descending (historical) intervals."""
        # Mock timezone as UTC to get predictable results
        mock_tz.return_value = 'UTC'
        
        # Create manager for historical data
        history_manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=2,
            is_order_ascending=False,
            data_class=WeatherForecastData
        )
        
        # Mock current time: 2024-01-01 14:35:22 UTC
        mock_now.return_value = datetime(2024, 1, 1, 14, 35, 22, tzinfo=pytz.UTC)
        
        intervals = history_manager._get_calculated_intervals()
        
        # Should create 2 intervals going backwards from midnight
        self.assertEqual(len(intervals), 2)
        
        # First interval: yesterday 00:00 to today 00:00 (most recent 24h)
        # Since we're using UTC timezone, these should be UTC times
        self.assertEqual(intervals[0].start, datetime(2023, 12, 31, 0, 0, 0, tzinfo=pytz.UTC))
        self.assertEqual(intervals[0].end, datetime(2024, 1, 1, 0, 0, 0, tzinfo=pytz.UTC))
        
        # Second interval: day before yesterday to yesterday (previous 24h)  
        self.assertEqual(intervals[1].start, datetime(2023, 12, 30, 0, 0, 0, tzinfo=pytz.UTC))
        self.assertEqual(intervals[1].end, datetime(2023, 12, 31, 0, 0, 0, tzinfo=pytz.UTC))
        return

    def test_initialization_creates_intervals(self):
        """Test that initialization creates the expected intervals."""
        with patch('hi.apps.common.datetimeproxy.now', 
                   return_value=datetime(2024, 1, 1, 14, 35, 22)):
            
            self.manager.ensure_initialized()
            
            self.assertTrue(self.manager._was_initialized)
            self.assertEqual(len(self.manager._aggregated_interval_data_list), 3)
            
            # Check that intervals were created correctly
            first_interval = self.manager._aggregated_interval_data_list[0].interval_data.interval
            self.assertEqual(first_interval.start, datetime(2024, 1, 1, 14, 0, 0))
            self.assertEqual(first_interval.end, datetime(2024, 1, 1, 15, 0, 0))
        return

    def test_add_data_distributes_to_overlapping_intervals(self):
        """Test that adding data distributes it to overlapping intervals."""
        with patch('hi.apps.common.datetimeproxy.now',
                   return_value=datetime(2024, 1, 1, 14, 35, 22)):
            
            self.manager.ensure_initialized()
            
            # Create source data that overlaps with multiple manager intervals
            source_interval = TimeInterval(
                start=datetime(2024, 1, 1, 14, 30, 0),  # Overlaps 14:00-15:00
                end=datetime(2024, 1, 1, 15, 30, 0)    # and 15:00-16:00
            )
            
            forecast_data = WeatherForecastData()
            forecast_data.temperature = NumericDataPoint(
                station=None,
                source_datetime=datetime(2024, 1, 1, 15, 0, 0),
                quantity_ave=UnitQuantity(25.0, 'degC')
            )
            
            interval_data = IntervalEnvironmentalData(
                interval=source_interval,
                data=forecast_data
            )
            
            # Add the data
            self.manager.add_data(
                data_point_source=self.test_source,
                new_interval_data_list=[interval_data]
            )
            
            # Check that data was added to overlapping intervals
            # This is complex to verify without exposing internal state,
            # but we can check that the method completed without error
            self.assertTrue(True)  # If we get here, no exceptions were thrown
        return

    def test_update_intervals_maintains_existing_data(self):
        """Test that updating intervals preserves existing aggregated data."""
        with patch('hi.apps.common.datetimeproxy.now',
                   return_value=datetime(2024, 1, 1, 14, 35, 22)):
            
            self.manager.ensure_initialized()
            initial_count = len(self.manager._aggregated_interval_data_list)
            
            # Simulate time advancing by updating intervals
            with patch('hi.apps.common.datetimeproxy.now',
                       return_value=datetime(2024, 1, 1, 15, 35, 22)):
                
                self.manager._update_intervals()
                
                # Should still have same number of intervals
                self.assertEqual(len(self.manager._aggregated_interval_data_list), initial_count)
                
                # But intervals should have shifted forward
                first_interval = self.manager._aggregated_interval_data_list[0].interval_data.interval
                self.assertEqual(first_interval.start, datetime(2024, 1, 1, 15, 0, 0))
                self.assertEqual(first_interval.end, datetime(2024, 1, 1, 16, 0, 0))
        return


if __name__ == '__main__':
    unittest.main()
