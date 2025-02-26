import logging

from hi.apps.weather.transient_models import (
    BooleanDataPoint,
    DailyAstronomicalData,
    NumericDataPoint,
    WeatherStation,
)
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestWeatherTransientModels( BaseTestCase ):

    def test_DailyAstronomicalData__days_until_full_moon(self):
        test_data_list = [
            { 'percent': 0.0, 'is_waxing'  : True , 'expect': 15 },
            { 'percent': 2.9, 'is_waxing'  : True , 'expect': 14 },
            { 'percent': 3.0, 'is_waxing'  : True , 'expect': 14 },
            { 'percent': 3.1, 'is_waxing' : True , 'expect': 14 },
            { 'percent': 25.1, 'is_waxing': True , 'expect': 11 },
            { 'percent': 46.9, 'is_waxing': True , 'expect': 8 },
            { 'percent': 47.0, 'is_waxing' : True , 'expect': 8 },
            { 'percent': 50.0, 'is_waxing' : True , 'expect': 7 },
            { 'percent': 53.0, 'is_waxing' : True , 'expect': 7 },
            { 'percent': 53.1, 'is_waxing' : True , 'expect': 7 },
            { 'percent': 75.1, 'is_waxing' : True , 'expect': 4 },
            { 'percent': 96.9, 'is_waxing' : True , 'expect': 0 },
            { 'percent': 97.0, 'is_waxing' : True , 'expect': 0 },
            { 'percent': 100.0, 'is_waxing': True, 'expect': 0 },
            { 'percent': 100.0, 'is_waxing': False, 'expect': 0 },
            { 'percent': 97.0, 'is_waxing': False, 'expect': 0 },
            { 'percent': 96.9, 'is_waxing' : False, 'expect': 29 },
            { 'percent': 75.1, 'is_waxing' : False, 'expect': 26 },
            { 'percent': 53.1, 'is_waxing' : False, 'expect': 23 },
            { 'percent': 53.0, 'is_waxing': False, 'expect': 23 },
            { 'percent': 50.0, 'is_waxing': False, 'expect': 22 },
            { 'percent': 47.0, 'is_waxing' : False, 'expect': 22 },
            { 'percent': 46.9, 'is_waxing': False, 'expect': 22 },
            { 'percent': 25.1, 'is_waxing': False, 'expect': 19 },
            { 'percent': 3.1, 'is_waxing': False, 'expect': 15 },
            { 'percent': 3.0, 'is_waxing': False, 'expect': 15 },
            { 'percent': 1.0, 'is_waxing': False, 'expect': 15 },
            { 'percent': 0.0, 'is_waxing': False, 'expect': 15 },
        ]

        weather_station = WeatherStation(
            source = 'test',
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        
        for test_data in test_data_list:
            daily_astronommical_data = DailyAstronomicalData(
                day = None,
                moon_illumnination = NumericDataPoint(
                    weather_station = weather_station,
                    source_datetime = None,
                    elevation = None,
                    quantity = UnitQuantity( test_data.get('percent'), 'percent' ),
                ),
                moon_is_waxing = BooleanDataPoint(
                    weather_station = weather_station,
                    source_datetime = None,
                    elevation = None,
                    value = test_data.get('is_waxing'),
                ),
            )
            self.assertAlmostEqual( test_data['expect'],
                                    daily_astronommical_data.days_until_full_moon,
                                    2,
                                    test_data )
            continue
        return

    def test_DailyAstronomicalData__days_until_new_moon(self):
        test_data_list = [
            { 'percent': 0.0, 'is_waxing'  : True , 'expect': 0 },
            { 'percent': 2.9, 'is_waxing'  : True , 'expect': 0 },
            { 'percent': 3.0, 'is_waxing'  : True , 'expect': 0 },
            { 'percent': 3.1, 'is_waxing' : True , 'expect': 29 },
            { 'percent': 25.1, 'is_waxing': True , 'expect': 26 },
            { 'percent': 46.9, 'is_waxing': True , 'expect': 23 },
            { 'percent': 47.0, 'is_waxing' : True , 'expect': 23 },
            { 'percent': 50.0, 'is_waxing' : True , 'expect': 22 },
            { 'percent': 53.0, 'is_waxing' : True , 'expect': 22 },
            { 'percent': 53.1, 'is_waxing' : True , 'expect': 22 },
            { 'percent': 75.1, 'is_waxing' : True , 'expect': 19 },
            { 'percent': 96.9, 'is_waxing' : True , 'expect': 15 },
            { 'percent': 97.0, 'is_waxing' : True , 'expect': 15 },
            { 'percent': 100.0, 'is_waxing': True, 'expect': 15 },
            { 'percent': 100.0, 'is_waxing': False, 'expect': 15 },
            { 'percent': 97.0, 'is_waxing': False, 'expect': 14 },
            { 'percent': 96.9, 'is_waxing' : False, 'expect': 14 },
            { 'percent': 75.1, 'is_waxing' : False, 'expect': 11 },
            { 'percent': 53.1, 'is_waxing' : False, 'expect': 8 },
            { 'percent': 53.0, 'is_waxing': False, 'expect': 8 },
            { 'percent': 50.0, 'is_waxing': False, 'expect': 7 },
            { 'percent': 47.0, 'is_waxing' : False, 'expect': 7 },
            { 'percent': 46.9, 'is_waxing': False, 'expect': 7 },
            { 'percent': 25.1, 'is_waxing': False, 'expect': 4 },
            { 'percent': 3.1, 'is_waxing': False, 'expect': 0 },
            { 'percent': 3.0, 'is_waxing': False, 'expect': 0 },
            { 'percent': 1.0, 'is_waxing': False, 'expect': 0 },
            { 'percent': 0.0, 'is_waxing': False, 'expect': 0 },
        ]

        weather_station = WeatherStation(
            source = 'test',
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        
        for test_data in test_data_list:
            daily_astronommical_data = DailyAstronomicalData(
                day = None,
                moon_illumnination = NumericDataPoint(
                    weather_station = weather_station,
                    source_datetime = None,
                    elevation = None,
                    quantity = UnitQuantity( test_data.get('percent'), 'percent' ),
                ),
                moon_is_waxing = BooleanDataPoint(
                    weather_station = weather_station,
                    source_datetime = None,
                    elevation = None,
                    value = test_data.get('is_waxing'),
                ),
            )
            self.assertAlmostEqual( test_data['expect'],
                                    daily_astronommical_data.days_until_new_moon,
                                    2,
                                    test_data )
            continue
        return
