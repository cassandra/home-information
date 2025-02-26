from datetime import timedelta
import logging
from unittest.mock import patch

import hi.apps.common.datetimeproxy as datetimeproxy

from hi.apps.weather.transient_models import DataPointSource
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
                priority = test_data['current_data_priority'],
            )
            new_source = DataPointSource(
                id = 'test',
                label = 'Test',
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
            current_data.temperature.quantity = UnitQuantity( 20, 'degF' )
            new_data.temperature.quantity = UnitQuantity( 33, 'degF' )

            if test_data['null_current_data']:
                current_data.temperature = None
            if test_data['null_new_data']:
                new_data.temperature = None
                
            old_value = current_data.temperature
            new_value = new_data.temperature
            
            weather_manager._update_weather_data(
                current_weather_data = current_data,
                new_weather_data = new_data,
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
    
