from django.test import TestCase
from unittest.mock import patch
from datetime import datetime
import pytz

from hi.apps.weather.interval_data_manager import IntervalDataManager
from hi.apps.weather.transient_models import WeatherForecastData, WeatherHistoryData


class TimezoneIntervalTest(TestCase):
    """Test that daily intervals use local timezone boundaries."""

    def test_daily_intervals_use_local_timezone_boundaries(self):
        """Test that daily forecasts align with local timezone day boundaries."""
        
        # Test with US/Central timezone (UTC-6 in winter, UTC-5 in summer)
        test_timezone = 'America/Chicago'
        
        with patch('hi.apps.console.console_helper.ConsoleSettingsHelper.get_tz_name',
                   return_value=test_timezone):
            # Create daily forecast manager
            daily_manager = IntervalDataManager(
                interval_hours=24,
                max_interval_count=3,
                is_order_ascending=True,
                data_class=WeatherForecastData
            )
            
            # Test at a specific time: 2025-08-11 22:00 UTC (which is 4:00 PM Central)
            # This should result in intervals starting from Aug 11 local time, not Aug 12
            test_utc_time = datetime(2025, 8, 11, 22, 0, 0, tzinfo=pytz.UTC)
            
            with patch('hi.apps.common.datetimeproxy.now', return_value=test_utc_time):
                daily_manager.ensure_initialized()
                
                # Check intervals
                intervals = []
                for agg_data in daily_manager._aggregated_interval_data_list:
                    interval = agg_data.interval_data.interval
                    intervals.append(interval)
                
                # Convert to local timezone for verification
                central_tz = pytz.timezone(test_timezone)
                local_intervals = []
                for interval in intervals:
                    local_start = interval.start.astimezone(central_tz)
                    local_end = interval.end.astimezone(central_tz)
                    local_intervals.append((local_start.date(), local_end.date()))
                
                # Should start from today (Aug 11) in local timezone
                expected_dates = [
                    (datetime(2025, 8, 11).date(), datetime(2025, 8, 12).date()),
                    (datetime(2025, 8, 12).date(), datetime(2025, 8, 13).date()),
                    (datetime(2025, 8, 13).date(), datetime(2025, 8, 14).date()),
                ]
                
                self.assertEqual(local_intervals, expected_dates)
                
                # Verify the first interval starts at midnight local time
                first_interval = intervals[0]
                local_start = first_interval.start.astimezone(central_tz)
                self.assertEqual(local_start.hour, 0)
                self.assertEqual(local_start.minute, 0)
                self.assertEqual(local_start.second, 0)

    def test_daily_history_intervals_use_local_timezone_boundaries(self):
        """Test that daily history uses local timezone boundaries in descending order."""
        
        test_timezone = 'America/New_York'  # UTC-5 in winter, UTC-4 in summer
        
        with patch('hi.apps.console.console_helper.ConsoleSettingsHelper.get_tz_name',
                   return_value=test_timezone):
            # Create daily history manager (descending order)
            history_manager = IntervalDataManager(
                interval_hours=24,
                max_interval_count=3,
                is_order_ascending=False,
                data_class=WeatherHistoryData
            )
            
            # Test at a specific time: 2025-08-11 18:00 UTC (which is 2:00 PM Eastern)
            test_utc_time = datetime(2025, 8, 11, 18, 0, 0, tzinfo=pytz.UTC)
            
            with patch('hi.apps.common.datetimeproxy.now', return_value=test_utc_time):
                history_manager.ensure_initialized()
                
                # Check intervals
                intervals = []
                for agg_data in history_manager._aggregated_interval_data_list:
                    interval = agg_data.interval_data.interval
                    intervals.append(interval)
                
                # Convert to local timezone for verification
                eastern_tz = pytz.timezone(test_timezone)
                local_intervals = []
                for interval in intervals:
                    local_start = interval.start.astimezone(eastern_tz)
                    local_end = interval.end.astimezone(eastern_tz)
                    local_intervals.append((local_start.date(), local_end.date()))
                
                # For history (descending), should go backwards from yesterday
                expected_dates = [
                    (datetime(2025, 8, 10).date(), datetime(2025, 8, 11).date()),  # yesterday
                    (datetime(2025, 8, 9).date(), datetime(2025, 8, 10).date()),   # day before
                    (datetime(2025, 8, 8).date(), datetime(2025, 8, 9).date()),    # day before that
                ]
                
                self.assertEqual(local_intervals, expected_dates)

    def test_hourly_intervals_still_use_utc_boundaries(self):
        """Test that hourly intervals continue to use UTC boundaries."""
        
        test_timezone = 'America/Chicago'
        
        with patch('hi.apps.console.console_helper.ConsoleSettingsHelper.get_tz_name',
                   return_value=test_timezone):
            # Create hourly forecast manager
            hourly_manager = IntervalDataManager(
                interval_hours=1,
                max_interval_count=3,
                is_order_ascending=True,
                data_class=WeatherForecastData
            )
            
            # Test at a specific time: 2025-08-11 22:30 UTC
            test_utc_time = datetime(2025, 8, 11, 22, 30, 0, tzinfo=pytz.UTC)
            
            with patch('hi.apps.common.datetimeproxy.now', return_value=test_utc_time):
                hourly_manager.ensure_initialized()
                
                # Check intervals - should be based on UTC hours
                intervals = []
                for agg_data in hourly_manager._aggregated_interval_data_list:
                    interval = agg_data.interval_data.interval
                    intervals.append((interval.start.hour, interval.end.hour))
                
                # Handle the hour rollover for the third interval
                actual_hours = []
                for start_hour, end_hour in intervals:
                    if end_hour == 0 and start_hour == 23:
                        actual_hours.append((start_hour, 24))  # Normalize for comparison
                    elif start_hour == 0:
                        actual_hours.append((24, end_hour))   # Normalize for comparison
                    else:
                        actual_hours.append((start_hour, end_hour))
                
                expected_normalized = [(22, 23), (23, 24), (24, 1)]
                self.assertEqual(actual_hours, expected_normalized)

    def test_timezone_change_updates_intervals(self):
        """Test that changing timezone properly updates daily intervals."""
        
        # Start with one timezone
        initial_timezone = 'America/Chicago'
        new_timezone = 'America/New_York'
        
        daily_manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=2,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        test_utc_time = datetime(2025, 8, 11, 20, 0, 0, tzinfo=pytz.UTC)
        
        # Initialize with first timezone
        with patch('hi.apps.console.console_helper.ConsoleSettingsHelper.get_tz_name',
                   return_value=initial_timezone):
            with patch('hi.apps.common.datetimeproxy.now', return_value=test_utc_time):
                daily_manager.ensure_initialized()
                
                # Get initial intervals
                initial_intervals = []
                for agg_data in daily_manager._aggregated_interval_data_list:
                    interval = agg_data.interval_data.interval
                    initial_intervals.append(interval.start)
        
        # Simulate timezone change by creating new manager (since timezone is cached)
        daily_manager_new_tz = IntervalDataManager(
            interval_hours=24,
            max_interval_count=2,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        
        # Initialize with new timezone
        with patch('hi.apps.console.console_helper.ConsoleSettingsHelper.get_tz_name',
                   return_value=new_timezone):
            with patch('hi.apps.common.datetimeproxy.now', return_value=test_utc_time):
                daily_manager_new_tz.ensure_initialized()
                
                # Get new intervals
                new_intervals = []
                for agg_data in daily_manager_new_tz._aggregated_interval_data_list:
                    interval = agg_data.interval_data.interval
                    new_intervals.append(interval.start)
        
        # Intervals should be different due to timezone change (1 hour difference between Central and Eastern)
        self.assertNotEqual(initial_intervals, new_intervals)
        
        # The difference should be exactly 1 hour (Eastern is 1 hour ahead of Central)
        time_diff = new_intervals[0] - initial_intervals[0]
        self.assertEqual(time_diff.total_seconds(), -3600)  # 1 hour earlier in UTC for Eastern
        
