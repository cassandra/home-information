from datetime import datetime, timedelta
import random
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.enums import (
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
)
from hi.apps.weather.transient_models import (
    BooleanDataPoint,
    CommonWeatherData,
    AstronomicalData,
    DataPointSource,
    DataPointList,
    NotablePhenomenon,
    NumericDataPoint,
    TimeIntervalCommonWeatherData,
    StatisticDataPoint,
    StringDataPoint,
    TimeDataPoint,
    WeatherConditionsData,
    WeatherForecastData,
    WeatherHistoryData,
    WeatherOverviewData,
    WeatherStation,
)
from hi.units import UnitQuantity


class WeatherSyntheticData:

    @classmethod
    def get_random_weather_overview_data( cls,
                                          now     : datetime         = None,
                                          source  : DataPointSource  = None  ) -> WeatherOverviewData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        return WeatherOverviewData(
            current_conditions_data = cls.get_random_weather_conditions_data( now = now, source = source ),
            todays_astronomical_data = cls.get_random_daily_astronomical_data( now = now, source = source ),
        )
    
    @classmethod
    def get_random_weather_conditions_data( cls,
                                            now     : datetime         = None,
                                            source  : DataPointSource  = None ) -> WeatherConditionsData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        weather_station = WeatherStation(
            source = source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
            
        weather_conditions_data = WeatherConditionsData(
            temperature = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
            ),
            temperature_min_last_24h = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
            ),
            temperature_max_last_24h = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
            ),
            precipitation_last_hour = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                quantity = UnitQuantity( 1.0 * random.random(), 'inches' ),
            ),
            precipitation_last_3h = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                quantity = UnitQuantity( 2.0 * random.random(), 'inches' ),
            ),
            precipitation_last_6h = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                quantity = UnitQuantity( 3.0 * random.random(), 'inches' ),
            ),
            precipitation_last_24h = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                quantity = UnitQuantity( 4.0 * random.random(), 'inches' ),
            ),
        )
        cls.set_random_notable_phenomenon(
            weather_conditions_data = weather_conditions_data,
            now = now,
            source = source,
        )
        cls.set_random_common_weather_data(
            data_obj = weather_conditions_data,
            now = now,
            source = source,
        )
        return weather_conditions_data

    @classmethod
    def get_random_daily_astronomical_data( cls,
                                            now     : datetime         = None,
                                            source  : DataPointSource  = None  ):
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        weather_station = WeatherStation(
            source = source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        return AstronomicalData(
            interval_start = datetimeproxy.date_to_datetime_day_begin( now.date() ),
            interval_end = datetimeproxy.date_to_datetime_day_end( now.date() ),
            interval_name = 'Today',
            sunrise = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now - timedelta( minutes = random.randint( 0, 360 ))).time(),
            ),
            sunset = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( 0, 360 ))).time(),
            ),
            solar_noon = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            moonrise = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( 90, 480 ))).time(),
            ),
            moonset = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( 480, 600 ))).time(),
            ),
            moon_illumnination = NumericDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                quantity = UnitQuantity( random.randint( 0, 100 ), 'percent' ),
            ),
            moon_is_waxing = BooleanDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = bool( random.random() < 0.5 ),
            ),
            civil_twilight_begin = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            civil_twilight_end = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            nautical_twilight_begin = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            nautical_twilight_end = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            astronomical_twilight_begin = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            astronomical_twilight_end = TimeDataPoint(
                weather_station = weather_station,
                source_datetime = now,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
        )

    @classmethod
    def get_random_hourly_forecast_data_list(
            cls,
            now     : datetime         = None,
            source  : DataPointSource  = None ) -> List[ WeatherForecastData ]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )            
        hourly_forecast_data_list = list()
        for hour_idx in range( 24 ):
            interval_start = now.replace( minute = 0, second = 0, microsecond = 0 )
            interval_start += timedelta( hours = hour_idx + 1 )
            interval_end = interval_start + timedelta( hours = 1 )
            forecast_data = cls.get_random_forecast_data( 
                interval_start = interval_start,
                interval_end = interval_end,
                now = now,
                source = source,
            )
            hourly_forecast_data_list.append( forecast_data )
            continue
        return hourly_forecast_data_list
    
    @classmethod
    def get_random_daily_forecast_data_list(
            cls,
            now     : datetime         = None,
            source  : DataPointSource  = None ) -> List[ WeatherForecastData ]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        daily_forecast_data_list = list()
        for day_idx in range( 10 ):
            interval_start = now.replace( hour = 0, minute = 0, second = 0, microsecond = 1 )
            interval_start += timedelta( hours = 24 * day_idx )
            interval_end = interval_start + timedelta( hours = 24 )
            forecast_data = cls.get_random_forecast_data( 
                interval_start = interval_start,
                interval_end = interval_end,
                now = now,
                source = source,
            )
            daily_forecast_data_list.append( forecast_data )
            continue
        return daily_forecast_data_list

    @classmethod
    def get_random_forecast_data( cls,
                                  interval_start  : datetime,
                                  interval_end    : datetime,
                                  now             : datetime         = None,
                                  source          : DataPointSource  = None ) -> WeatherForecastData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        forecast_data = WeatherForecastData(
            interval_start = interval_start,
            interval_end = interval_end,
        )
        cls.set_random_time_interval_data(
            data_obj = forecast_data,
            now = now,
            source = source,
        )
        return forecast_data

    @classmethod
    def get_random_daily_history_data_list( cls,
                                            now     : datetime         = None,
                                            source  : DataPointSource  = None ) -> List[ WeatherHistoryData ]:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        daily_history_data_list = list()
        for day_idx in range( 10 ):
            interval_start = now.replace( hour = 0, minute = 0, second = 0, microsecond = 1 )
            interval_start -= timedelta( hours = 24 * ( day_idx + 1 ))
            interval_end = interval_start + timedelta( hours = 24 )
            history_data = cls.get_random_history_data( 
                interval_start = interval_start,
                interval_end = interval_end,
                now = now,
                source = source,
            )
            daily_history_data_list.append( history_data )
            continue
        return daily_history_data_list
    
    @classmethod
    def get_random_history_data( cls,
                                 interval_start  : datetime,
                                 interval_end    : datetime,
                                 now             : datetime         = None,
                                 source          : DataPointSource  = None ) -> WeatherHistoryData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        history_data = WeatherHistoryData(
            interval_start = interval_start,
            interval_end = interval_end,
        )
        cls.set_random_time_interval_data(
            data_obj = history_data,
            now = now,
            source = source,
        )
        return history_data

    @classmethod
    def set_random_common_weather_data( cls,
                                        data_obj  : CommonWeatherData,
                                        now       : datetime         = None,
                                        source    : DataPointSource  = None ):
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        weather_station = WeatherStation(
            source = source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        data_obj.cloud_cover = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 0, 100 ), 'percent' ),
        )
        data_obj.cloud_ceiling = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 300, 5000 ), 'm' ),
        )
        data_obj.windspeed = StatisticDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity_min = UnitQuantity( random.randint( 0, 15 ), 'mph' ),
            quantity_ave = UnitQuantity( random.randint( 15, 30 ), 'mph' ),
            quantity_max = UnitQuantity( random.randint( 30, 80 ), 'mph' ),
        )
        data_obj.wind_direction = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 0, 359 ), 'deg' ),
        )
        data_obj.relative_humidity = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 0, 100 ), 'percent' ),
        )
        data_obj.dew_point = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 0, 100 ), 'degF' ),
        )
        data_obj.barometric_pressure = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 950, 1100 ), 'inHg' ),
        )
        data_obj.sea_level_pressure = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 950, 1100 ), 'inHg' ),
        )
        data_obj.heat_index = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 0, 120 ), 'degF' ),
        )
        data_obj.wind_chill = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( -20, 90 ), 'degF' ),
        )
        data_obj.visibility = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.randint( 0, 10 ), 'miles' ),
        )
        data_obj.description_short = StringDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            value = 'A lot of weather today.',
        )
        data_obj.description_long = StringDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            value = 'A lot of weather today blah blah blah blah blah blah blah blah blah blah blah blah.',
        )
        return

    @classmethod
    def set_random_time_interval_data( cls,
                                       data_obj  : TimeIntervalCommonWeatherData,
                                       now       : datetime                        = None,
                                       source    : DataPointSource                 = None ):
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        weather_station = WeatherStation(
            source = source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        data_obj.temperature = StatisticDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity_min = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
            quantity_ave = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
            quantity_max = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
        )
        data_obj.precipitation_amount = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( 4.0 * random.random(), 'inches' ),
        )
        data_obj.precipitation_probability = NumericDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity = UnitQuantity( random.random(), 'probability' ),
        )
        data_obj.windspeed = StatisticDataPoint(
            weather_station = weather_station,
            source_datetime = now,
            quantity_min = UnitQuantity( random.randint( 0, 15 ), 'mph' ),
            quantity_ave = UnitQuantity( random.randint( 15, 30 ), 'mph' ),
            quantity_max = UnitQuantity( random.randint( 30, 80 ), 'mph' ),
        )
        cls.set_random_common_weather_data(
            data_obj = data_obj,
            now = now,
            source = source,
        )
        return

    @classmethod
    def set_random_notable_phenomenon( cls,
                                       weather_conditions_data  : WeatherConditionsData,
                                       now                      : datetime                = None,
                                       source                   : DataPointSource         = None  ):
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        weather_station = WeatherStation(
            source = source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        notable_phenomenon_list = list()
        for idx in range( random.randint( 0, 2 ) ):
            notable_phenomenon = NotablePhenomenon(
                weather_phenomenon = random.choice( list( WeatherPhenomenon )),
                weather_phenomenon_modifier = random.choice( list( WeatherPhenomenonModifier )),
                weather_phenomenon_intensity = random.choice( list( WeatherPhenomenonIntensity )),
                in_vicinity = bool( random.random() < 0.5 ),
            )
            notable_phenomenon_list.append( notable_phenomenon )
            continue
        weather_conditions_data.notable_phenomenon_data = DataPointList(
            weather_station = weather_station,
            source_datetime = now,
            list_value = notable_phenomenon_list,
        )
        return
