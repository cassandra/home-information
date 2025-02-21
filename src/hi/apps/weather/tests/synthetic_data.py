from datetime import time
import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.transient_models import (
    DailyAstronomicalData,
    TimeDataPoint,
    WeatherConditionsData,
    WeatherDataPoint,
    WeatherOverviewData,
)
from hi.units import UnitQuantity


class WeatherSyntheticData:

    now = datetimeproxy.now()

    WeatherConditionsData_001 = WeatherConditionsData(
        temperature  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 22, 'degF' ),
        ),
        temperature_min_last_24h  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 18, 'degF' ),
        ),
        temperature_max_last_24h  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 32, 'degF' ),
        ),
        cloud_cover  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 66, 'percent' ),
        ),
        windspeed_low  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 5, 'mph' ),
        ),
        windpeed_average  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 8, 'mph' ),
        ),
        windspeed_max  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 10, 'mph' ),
        ),
        wind_direction  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 135, 'deg' ),
        ),
        relative_humidity  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 62, 'percent' ),
        ),
        precipitation_last_hour  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 0.5, 'inches' ),
        ),
        precipitation_last_3h  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 0.62, 'inches' ),
        ),
        precipitation_last_6h  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 0.63, 'inches' ),
        ),
        precipitation_last_24h  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 0.83, 'inches' ),
        ),
        dew_point  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 62, 'degF' ),
        ),
        barometric_pressure  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 1006, 'inHg' ),
        ),
        sea_level_pressure  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 1024, 'inHg' ),
        ),
        heat_index  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 56, 'degF' ),
        ),
        wind_chill  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 15, 'degF' ),
        ),
        visibility  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = UnitQuantity( 2, 'meters' ),
            quantity = UnitQuantity( 8, 'miles' ),
        ),
    )

    DailyAstronomicalData_001 = DailyAstronomicalData(
        day = now.date(),
        sunrise = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 6, 42, 34 ),
        ),
        sunset = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 19, 53, 9 ),
        ),
        solar_noon = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 12, 7, 34 ),
        ),
        moonrise = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 17, 6, 34 ),
        ),
        moonset = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 4, 56, 34 ),
        ),
        moon_illumnination  = WeatherDataPoint(
            source = 'test',
            source_datetime = now,
            elevation = None,
            quantity = UnitQuantity( 50.9, 'percent' ),
        ),
        moon_is_waxing = True,
        civil_twilight_begin = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 19, 53, 34 ),
        ),
        civil_twilight_end = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 5, 45, 34 ),
        ),
        nautical_twilight_begin = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 20, 13, 34 ),
        ),
        nautical_twilight_end = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 5, 20, 34 ),
        ),
        astronomical_twilight_begin = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 21, 2, 34 ),
        ),
        astronomical_twilight_end = TimeDataPoint(
            source = 'test',
            source_datetime = now,
            value = time( 5, 2, 34 ),
        ),
    )

    WeatherOverviewData_001 = WeatherOverviewData(
        current_conditions_data = WeatherConditionsData_001,
        todays_astronomical_data = DailyAstronomicalData_001,
    )
