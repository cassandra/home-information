from django.test import TestCase
from unittest.mock import patch
from datetime import datetime
import pytz

from hi.apps.weather.interval_data_manager import IntervalDataManager
from hi.apps.weather.transient_models import (
    WeatherForecastData, DataPointSource, IntervalEnvironmentalData, TimeInterval
)


class IntervalUpdatingTest(TestCase):
    """Test that intervals are properly updated as time passes."""

    def setUp(self):
        # Create a test source
        self.test_source = DataPointSource(
            id='test',
            label='Test Source', 
            abbreviation='TEST',
            priority=1
        )
        
        # Create daily forecast manager
        self.daily_manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=3,  # Keep it small for testing
            is_order_ascending=True,
            data_class=WeatherForecastData
        )

    def test_interval_updating_over_time(self):
        """Test that intervals are updated when time advances."""
        
        # Test at a specific time: 2025-08-11 14:00:00 UTC
        initial_time = datetime(2025, 8, 11, 14, 0, 0, tzinfo=pytz.UTC)
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=initial_time):
            self.daily_manager.ensure_initialized()
            
            # Check initial intervals
            initial_intervals = []
            for agg_data in self.daily_manager._aggregated_interval_data_list:
                interval = agg_data.interval_data.interval
                initial_intervals.append((interval.start.date(), interval.end.date()))
            
            # Should start from today and extend into future
            expected_initial = [
                (datetime(2025, 8, 11).date(), datetime(2025, 8, 12).date()),
                (datetime(2025, 8, 12).date(), datetime(2025, 8, 13).date()),
                (datetime(2025, 8, 13).date(), datetime(2025, 8, 14).date()),
            ]
            self.assertEqual(initial_intervals, expected_initial)
            
            # Simulate adding some data
            test_data = IntervalEnvironmentalData(
                interval=TimeInterval(
                    start=datetime(2025, 8, 11, 0, 0, 0, tzinfo=pytz.UTC),
                    end=datetime(2025, 8, 12, 0, 0, 0, tzinfo=pytz.UTC)
                ),
                data=WeatherForecastData()
            )
            
            self.daily_manager.add_data(self.test_source, [test_data])
            
            # Intervals should remain the same since time hasn't changed
            after_add_intervals = []
            for agg_data in self.daily_manager._aggregated_interval_data_list:
                interval = agg_data.interval_data.interval
                after_add_intervals.append((interval.start.date(), interval.end.date()))
            
            self.assertEqual(after_add_intervals, expected_initial)
        
        # Now advance time by 1 day and add more data
        advanced_time = datetime(2025, 8, 12, 14, 0, 0, tzinfo=pytz.UTC)
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=advanced_time):
            # Add more data - this should trigger interval updating
            test_data2 = IntervalEnvironmentalData(
                interval=TimeInterval(
                    start=datetime(2025, 8, 12, 0, 0, 0, tzinfo=pytz.UTC),
                    end=datetime(2025, 8, 13, 0, 0, 0, tzinfo=pytz.UTC)
                ),
                data=WeatherForecastData()
            )
            
            self.daily_manager.add_data(self.test_source, [test_data2])
            
            # Check updated intervals
            updated_intervals = []
            for agg_data in self.daily_manager._aggregated_interval_data_list:
                interval = agg_data.interval_data.interval
                updated_intervals.append((interval.start.date(), interval.end.date()))
            
            # Should now start from the advanced day, removing old intervals
            expected_updated = [
                (datetime(2025, 8, 12).date(), datetime(2025, 8, 13).date()),
                (datetime(2025, 8, 13).date(), datetime(2025, 8, 14).date()),
                (datetime(2025, 8, 14).date(), datetime(2025, 8, 15).date()),
            ]
            self.assertEqual(updated_intervals, expected_updated)
            
            # Verify the old 2025-08-11 interval is gone
            for start_date, end_date in updated_intervals:
                self.assertNotEqual(start_date, datetime(2025, 8, 11).date())

    def test_hourly_interval_updating(self):
        """Test that hourly intervals are also properly updated."""
        
        # Create hourly forecast manager
        hourly_manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=3,  # Keep it small for testing
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        # Test at a specific time: 2025-08-11 14:30:00 UTC
        initial_time = datetime(2025, 8, 11, 14, 30, 0, tzinfo=pytz.UTC)
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=initial_time):
            hourly_manager.ensure_initialized()
            
            # Check initial intervals
            initial_intervals = []
            for agg_data in hourly_manager._aggregated_interval_data_list:
                interval = agg_data.interval_data.interval
                initial_intervals.append((interval.start.hour, interval.end.hour))
            
            # Should start from current hour (14:00-15:00) and extend forward
            expected_initial = [(14, 15), (15, 16), (16, 17)]
            self.assertEqual(initial_intervals, expected_initial)
        
        # Advance time by 2 hours
        advanced_time = datetime(2025, 8, 11, 16, 30, 0, tzinfo=pytz.UTC)
        
        with patch('hi.apps.common.datetimeproxy.now', return_value=advanced_time):
            # Add data - this should trigger interval updating
            test_data = IntervalEnvironmentalData(
                interval=TimeInterval(
                    start=datetime(2025, 8, 11, 16, 0, 0, tzinfo=pytz.UTC),
                    end=datetime(2025, 8, 11, 17, 0, 0, tzinfo=pytz.UTC)
                ),
                data=WeatherForecastData()
            )
            
            hourly_manager.add_data(self.test_source, [test_data])
            
            # Check updated intervals
            updated_intervals = []
            for agg_data in hourly_manager._aggregated_interval_data_list:
                interval = agg_data.interval_data.interval
                updated_intervals.append((interval.start.hour, interval.end.hour))
            
            # Should now start from advanced hour (16:00), removing old intervals
            expected_updated = [(16, 17), (17, 18), (18, 19)]
            self.assertEqual(updated_intervals, expected_updated)
            
            # Verify old hours (14, 15) are gone
            for start_hour, end_hour in updated_intervals:
                self.assertNotIn(start_hour, [14, 15])
                
