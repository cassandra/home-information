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
    DailyAstronomicalData,
    DataPointSource,
    ListDataPoint,
    NotablePhenomenon,
    NumericDataPoint,
    PeriodWeatherData,
    TimeDataPoint,
    WeatherConditionsData,
    WeatherForecastData,
    WeatherHistoryData,
    WeatherOverviewData,
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
        weather_conditions_data = WeatherConditionsData(
            temperature = NumericDataPoint(
                source = source,
                source_datetime = now,
                elevation = UnitQuantity( 2, 'meters' ),
                quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
            ),
            temperature_min_last_24h = NumericDataPoint(
                source = source,
                source_datetime = now,
                elevation = UnitQuantity( 2, 'meters' ),
                quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
            ),
            temperature_max_last_24h = NumericDataPoint(
                source = source,
                source_datetime = now,
                elevation = UnitQuantity( 2, 'meters' ),
                quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
            ),
            precipitation_last_hour = NumericDataPoint(
                source = source,
                source_datetime = now,
                elevation = UnitQuantity( 2, 'meters' ),
                quantity = UnitQuantity( 1.0 * random.random(), 'inches' ),
            ),
            precipitation_last_3h = NumericDataPoint(
                source = source,
                source_datetime = now,
                elevation = UnitQuantity( 2, 'meters' ),
                quantity = UnitQuantity( 2.0 * random.random(), 'inches' ),
            ),
            precipitation_last_6h = NumericDataPoint(
                source = source,
                source_datetime = now,
                elevation = UnitQuantity( 2, 'meters' ),
                quantity = UnitQuantity( 3.0 * random.random(), 'inches' ),
            ),
            precipitation_last_24h = NumericDataPoint(
                source = source,
                source_datetime = now,
                elevation = UnitQuantity( 2, 'meters' ),
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
        elevation = UnitQuantity( 2, 'meters' )
        return DailyAstronomicalData(
            day = now.date(),
            sunrise = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now - timedelta( minutes = random.randint( 0, 360 ))).time(),
            ),
            sunset = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( 0, 360 ))).time(),
            ),
            solar_noon = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            moonrise = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( 90, 480 ))).time(),
            ),
            moonset = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( 480, 600 ))).time(),
            ),
            moon_illumnination = NumericDataPoint(
                source = source,
                source_datetime = now,
                elevation = None,
                quantity = UnitQuantity( random.randint( 0, 100 ), 'percent' ),
            ),
            moon_is_waxing = BooleanDataPoint(
                source = source,
                source_datetime = now,
                elevation = None,
                value = bool( random.random() < 0.5 ),
            ),
            civil_twilight_begin = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            civil_twilight_end = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            nautical_twilight_begin = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            nautical_twilight_end = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            astronomical_twilight_begin = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
                value = ( now + timedelta( minutes = random.randint( -90, 90 ))).time(),
            ),
            astronomical_twilight_end = TimeDataPoint(
                source = source,
                source_datetime = now,
                elevation = elevation,
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
            period_start = now.replace( minute = 0, second = 0, microsecond = 0 )
            period_start += timedelta( hours = hour_idx + 1 )
            period_end = period_start + timedelta( hours = 1 )
            forecast_data = cls.get_random_forecast_data( 
                period_start = period_start,
                period_end = period_end,
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
            period_start = now.replace( hour = 0, minute = 0, second = 0, microsecond = 1 )
            period_start += timedelta( hours = 24 * day_idx )
            period_end = period_start + timedelta( hours = 24 )
            forecast_data = cls.get_random_forecast_data( 
                period_start = period_start,
                period_end = period_end,
                now = now,
                source = source,
            )
            daily_forecast_data_list.append( forecast_data )
            continue
        return daily_forecast_data_list

    @classmethod
    def get_random_forecast_data( cls,
                                  period_start  : datetime,
                                  period_end    : datetime,
                                  now           : datetime         = None,
                                  source        : DataPointSource  = None ) -> WeatherForecastData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        forecast_data = WeatherForecastData(
            period_start = period_start,
            period_end = period_end,
        )
        cls.set_random_periodic_data(
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
            period_start = now.replace( hour = 0, minute = 0, second = 0, microsecond = 1 )
            period_start -= timedelta( hours = 24 * ( day_idx + 1 ))
            period_end = period_start + timedelta( hours = 24 )
            history_data = cls.get_random_history_data( 
                period_start = period_start,
                period_end = period_end,
                now = now,
                source = source,
            )
            daily_history_data_list.append( history_data )
            continue
        return daily_history_data_list
    
    @classmethod
    def get_random_history_data( cls,
                                 period_start  : datetime,
                                 period_end    : datetime,
                                 now           : datetime         = None,
                                 source        : DataPointSource  = None ) -> WeatherHistoryData:
        if not now:
            now = datetimeproxy.now()
        if not source:
            source = DataPointSource(
                id = 'test',
                label = 'Test',
                priority = 1,
            )
        history_data = WeatherHistoryData(
            period_start = period_start,
            period_end = period_end,
        )
        cls.set_random_periodic_data(
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
        data_obj.cloud_cover = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 100 ), 'percent' ),
        )
        data_obj.cloud_ceiling = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 300, 5000 ), 'm' ),
        )
        data_obj.windspeed_min = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 20 ), 'mph' ),
        )
        data_obj.windspeed_ave = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 40 ), 'mph' ),
        )
        data_obj.windspeed_max = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 80 ), 'mph' ),
        )
        data_obj.wind_direction = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 359 ), 'deg' ),
        )
        data_obj.relative_humidity = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 100 ), 'percent' ),
        )
        data_obj.dew_point = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 100 ), 'degF' ),
        )
        data_obj.barometric_pressure = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 950, 1100 ), 'inHg' ),
        )
        data_obj.sea_level_pressure = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 950, 1100 ), 'inHg' ),
        )
        data_obj.heat_index = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 120 ), 'degF' ),
        )
        data_obj.wind_chill = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( -20, 90 ), 'degF' ),
        )
        data_obj.visibility = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( 0, 10 ), 'miles' ),
        )
        return

    @classmethod
    def set_random_periodic_data( cls,
                                  data_obj  : PeriodWeatherData,
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
        data_obj.temperature_min = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
        )
        data_obj.temperature_ave = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
        )
        data_obj.temperature_max = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.randint( -5, 115 ), 'degF' ),
        )
        data_obj.precipitation = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 4.0 * random.random(), 'inches' ),
        )
        data_obj.precipitation_probability = NumericDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( random.random(), 'probability' ),
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
        weather_conditions_data.notable_phenomenon_data = ListDataPoint(
            source = source,
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            list_value = notable_phenomenon_list,
            )
        return
