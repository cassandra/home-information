from datetime import timedelta, datetime
import logging
from unittest.mock import patch, AsyncMock
import asyncio
import pytz

import hi.apps.common.datetimeproxy as datetimeproxy

from hi.apps.weather.transient_models import (
    DataPointSource, IntervalWeatherHistory, WeatherHistoryData,
    TimeInterval, NumericDataPoint, StringDataPoint, Station
)
from hi.apps.weather.weather_manager import WeatherManager
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase
from hi.apps.weather.tests.synthetic_data import WeatherSyntheticData

logging.disable(logging.CRITICAL)


class TestWeatherManager( BaseTestCase ):
    
    @patch.object( WeatherManager, 'STALE_DATA_POINT_AGE_SECONDS', new = 60 )
    def test_update_weather_data(self):

        test_data_list = [
            {
                # No new data, same source priority
                'current_data_priority': 1,
                'new_data_priority': 1,
                'current_data_time_offset_secs': 20,
                'new_data_time_offset_secs': 10,
                'null_current_data': False,
                'null_new_data': True,
                'expect_overwrite': False,
            },
            {
                # New data, same source priority
                'current_data_priority': 1,
                'new_data_priority': 1,
                'current_data_time_offset_secs': 20,
                'new_data_time_offset_secs': 10,
                'null_current_data': False,
                'null_new_data': False,
                'expect_overwrite': True,
            },
            {
                # New data, same source priority, but date is older
                'current_data_priority': 1,
                'new_data_priority': 1,
                'current_data_time_offset_secs': 10,
                'new_data_time_offset_secs': 20,
                'null_current_data': False,
                'null_new_data': False,
                'expect_overwrite': False,
            },
            {
                # New data, higher priority
                'current_data_priority': 3,
                'new_data_priority': 1,
                'current_data_time_offset_secs': 20,
                'new_data_time_offset_secs': 10,
                'null_current_data': False,
                'null_new_data': False,
                'expect_overwrite': True,
            },
            {
                # New data, higher priority, but date is older
                'current_data_priority': 3,
                'new_data_priority': 1,
                'current_data_time_offset_secs': 10,
                'new_data_time_offset_secs': 20,
                'null_current_data': False,
                'null_new_data': False,
                'expect_overwrite': False,
            },
            {
                # New data, lower priority
                'current_data_priority': 1,
                'new_data_priority': 3,
                'current_data_time_offset_secs': 20,
                'new_data_time_offset_secs': 10,
                'null_current_data': False,
                'null_new_data': False,
                'expect_overwrite': False,
            },
            {
                # New data, lower priority, but data is stale
                'current_data_priority': 1,
                'new_data_priority': 3,
                'current_data_time_offset_secs': 120,
                'new_data_time_offset_secs': 10,
                'null_current_data': False,
                'null_new_data': False,
                'expect_overwrite': True,
            },
            {
                # No existing data
                'current_data_priority': 1,
                'new_data_priority': 3,
                'current_data_time_offset_secs': 20,
                'new_data_time_offset_secs': 10,
                'null_current_data': True,
                'null_new_data': False,
                'expect_overwrite': True,
            },
            {
                # No new data
                'current_data_priority': 1,
                'new_data_priority': 3,
                'current_data_time_offset_secs': 20,
                'new_data_time_offset_secs': 10,
                'null_current_data': False,
                'null_new_data': True,
                'expect_overwrite': False,
            },
            {
                # No existing or new data
                'current_data_priority': 1,
                'new_data_priority': 3,
                'current_data_time_offset_secs': 20,
                'new_data_time_offset_secs': 10,
                'null_current_data': True,
                'null_new_data': True,
                'expect_overwrite': False,
            },
        ]
        
        weather_manager = WeatherManager()

        for test_data in test_data_list:

            current_source = DataPointSource(
                id = 'test',
                label = 'Test',
                abbreviation = 'TEST',
                priority = test_data['current_data_priority'],
            )
            new_source = DataPointSource(
                id = 'test',
                label = 'Test',
                abbreviation = 'TEST',
                priority = test_data['new_data_priority'],
            )
            current_data_datetime = ( datetimeproxy.now()
                                      - timedelta( seconds = test_data['current_data_time_offset_secs'] ))
            new_data_datetime = ( datetimeproxy.now()
                                  - timedelta( seconds = test_data['new_data_time_offset_secs'] ))

            current_data = WeatherSyntheticData.get_random_weather_conditions_data(
                now = current_data_datetime,
                source = current_source,
            )
            new_data = WeatherSyntheticData.get_random_weather_conditions_data(
                now = new_data_datetime,
                source = new_source,
            )

            # Force values to different values (ensures random values do not collide: rare, but possible)
            current_data.temperature.quantity_ave = UnitQuantity( 20, 'degF' )
            new_data.temperature.quantity_ave = UnitQuantity( 33, 'degF' )

            if test_data['null_current_data']:
                current_data.temperature = None
            if test_data['null_new_data']:
                new_data.temperature = None
                
            old_value = current_data.temperature
            new_value = new_data.temperature
            
            weather_manager._update_environmental_data(
                current_data = current_data,
                new_data = new_data,
                data_point_source = new_source,
            )

            updated_value = current_data.temperature
            
            if test_data['expect_overwrite']:
                expected_value = new_value
            else:
                expected_value = old_value

            if expected_value is None:
                self.assertIsNone( updated_value )
            else:
                self.assertAlmostEqual( expected_value.quantity.magnitude,
                                        updated_value.quantity.magnitude,
                                        3, test_data )
                self.assertEqual( expected_value.quantity.units,
                                  updated_value.quantity.units,
                                  test_data )
            continue
        return

    def test_daily_history_data_flow(self):
        """Test that daily history data flows correctly from weather manager to template context."""
        weather_manager = WeatherManager()
        
        # Ensure weather manager is initialized
        weather_manager.ensure_initialized()
        
        # Create mock historical data
        test_source = DataPointSource(
            id='test_source',
            label='Test Weather Source',
            abbreviation='TEST',
            priority=1
        )
        
        test_station = Station(
            source=test_source,
            station_id='TEST001'
        )
        
        # Create sample historical data with timezone-aware datetimes
        history_data_list = []
        base_time = datetime(2024, 1, 10, 0, 0, 0, tzinfo=pytz.UTC)
        
        for i in range(3):  # 3 days of history
            interval_start = base_time - timedelta(days=i+1)
            interval_end = base_time - timedelta(days=i)
            
            history_data = WeatherHistoryData(
                temperature=NumericDataPoint(
                    station=test_station,
                    source_datetime=datetimeproxy.now(),
                    quantity_ave=UnitQuantity(20.0 + i, 'degC')
                ),
                precipitation=NumericDataPoint(
                    station=test_station,
                    source_datetime=datetimeproxy.now(),
                    quantity_ave=UnitQuantity(2.5 * i, 'mm')
                )
            )
            
            interval_history = IntervalWeatherHistory(
                interval=TimeInterval(start=interval_start, end=interval_end),
                data=history_data
            )
            
            history_data_list.append(interval_history)
        
        # Use asyncio to test the async update method
        async def test_update():
            # Create mock weather data source
            mock_weather_source = AsyncMock()
            mock_weather_source.data_point_source = test_source
            
            # Update daily history through weather manager
            await weather_manager.update_daily_history(
                weather_data_source=mock_weather_source,
                history_data_list=history_data_list
            )
        
        # Run the async test
        asyncio.run(test_update())
        
        # Verify daily history is populated
        daily_history = weather_manager.get_daily_history()
        
        # Check that we have history data
        self.assertIsNotNone(daily_history)
        self.assertIsNotNone(daily_history.data_list)
        self.assertGreater(len(daily_history.data_list), 0, 
                          "Daily history should contain data after update")
        
        # Verify the structure matches what templates expect
        for daily_history_interval in daily_history.data_list:
            # Check that each item is an IntervalWeatherHistory
            self.assertIsInstance(daily_history_interval, IntervalWeatherHistory)
            
            # Check that it has interval and data attributes (as expected by template)
            self.assertIsNotNone(daily_history_interval.interval)
            self.assertIsNotNone(daily_history_interval.data)
            
            # Check that the data has the expected fields
            if daily_history_interval.data.temperature:
                self.assertIsInstance(daily_history_interval.data.temperature, NumericDataPoint)
                self.assertIsNotNone(daily_history_interval.data.temperature.quantity)
            
            if daily_history_interval.data.precipitation:
                self.assertIsInstance(daily_history_interval.data.precipitation, NumericDataPoint) 
                self.assertIsNotNone(daily_history_interval.data.precipitation.quantity)
    
