from dataclasses import dataclass
from datetime import date, datetime, time

from hi.units import UnitQuantity

from .enums import (
    AlertCategory,
    AlertCertainty,
    AlertSeverity,
    AlertStatus,
    AlertUrgency,
    WeatherSource,
)


@dataclass
class WeatherDataPoint:

    source           : WeatherSource
    source_datetime  : datetime
    elevation        : UnitQuantity
    quantity         : UnitQuantity

    
@dataclass
class FloatWeatherDataPoint( WeatherDataPoint ):
    value            : float

 
@dataclass
class TimeWeatherDataPoint( WeatherDataPoint ):
    value            : time

 
@dataclass
class WeatherConditionsData:
    temperature                : FloatWeatherDataPoint
    """
    temperature_min_last_24h   : FloatWeatherDataPoint
    temperature_max_last_24h   : FloatWeatherDataPoint
    relative_humidity          : FloatWeatherDataPoint
    windspeed_low              : FloatWeatherDataPoint
    windpeed_average           : FloatWeatherDataPoint
    windspeed_max              : FloatWeatherDataPoint  # a.k.a., "wind gust"
    wind_direction             : FloatWeatherDataPoint  # 0 to 360
    cloud_cover                : FloatWeatherDataPoint
    precipitation_last_hour    : FloatWeatherDataPoint
    precipitation_last_3h      : FloatWeatherDataPoint
    precipitation_last_6h      : FloatWeatherDataPoint
    precipitation_last_24h     : FloatWeatherDataPoint
    dew_point                  : FloatWeatherDataPoint
    barometric_pressure        : FloatWeatherDataPoint
    sea_level_pressure         : FloatWeatherDataPoint
    heat_index                 : FloatWeatherDataPoint
    wind_chill                 : FloatWeatherDataPoint
    visibility                 : FloatWeatherDataPoint
    """
    
@dataclass
class WeatherForecastData:
    period_start               : datetime
    period_end                 : datetime
    temperature_min            : FloatWeatherDataPoint
    temperature_ave            : FloatWeatherDataPoint
    temperature_max            : FloatWeatherDataPoint
    relative_humidity          : FloatWeatherDataPoint
    wind_speed_low             : FloatWeatherDataPoint
    wind_speed_average         : FloatWeatherDataPoint
    wind_speed_max             : FloatWeatherDataPoint  # a.k.a., "wind gust"
    wind_direction             : FloatWeatherDataPoint  # 0 to 360
    cloud_cover                : FloatWeatherDataPoint
    precipitation_quantity     : FloatWeatherDataPoint
    precipitation_probability  : FloatWeatherDataPoint
    dew_point                  : FloatWeatherDataPoint
    barometric_pressure        : FloatWeatherDataPoint
    sea_level_pressure         : FloatWeatherDataPoint
    heat_index                 : FloatWeatherDataPoint
    wind_chill                 : FloatWeatherDataPoint
    visibility                 : FloatWeatherDataPoint

    
@dataclass
class WeatherHistoryData:
    period_start               : datetime
    period_end                 : datetime
    temperature_min            : FloatWeatherDataPoint
    temperature_ave            : FloatWeatherDataPoint
    temperature_max            : FloatWeatherDataPoint
    relative_humidity          : FloatWeatherDataPoint
    wind_speed_low             : FloatWeatherDataPoint
    wind_speed_average         : FloatWeatherDataPoint
    wind_speed_max             : FloatWeatherDataPoint  # a.k.a., "wind gust"
    wind_direction             : FloatWeatherDataPoint  # 0 to 360
    cloud_cover                : FloatWeatherDataPoint
    precipitation_quantity     : FloatWeatherDataPoint
    dew_point                  : FloatWeatherDataPoint
    barometric_pressure        : FloatWeatherDataPoint
    sea_level_pressure         : FloatWeatherDataPoint
    heat_index                 : FloatWeatherDataPoint
    wind_chill                 : FloatWeatherDataPoint
    visibility                 : FloatWeatherDataPoint

    
@dataclass
class DailyAstronomicalData:
    pass
    """
    day                          : date
    sunrise                      : TimeWeatherDataPoint
    sunset                       : TimeWeatherDataPoint
    solar_noon                   : TimeWeatherDataPoint
    moonrise                     : TimeWeatherDataPoint
    moonset                      : TimeWeatherDataPoint
    moon_illumnination           : FloatWeatherDataPoint  # 0.0 [new moon] to 1.0 [full moon]
    civil_twilight_begin         : TimeWeatherDataPoint
    civil_twilight_end           : TimeWeatherDataPoint
    nautical_twilight_begin      : TimeWeatherDataPoint
    nautical_twilight_end        : TimeWeatherDataPoint
    astronomical_twilight_begin  : TimeWeatherDataPoint
    astronomical_twilight_end    : TimeWeatherDataPoint
    """

@dataclass
class WeatherOverviewData:

    conditions_current  : WeatherConditionsData
    astronomical_today  : DailyAstronomicalData


@dataclass
class WeatherAlert:

    event           : str
    status          : AlertStatus
    category        : AlertCategory
    headline        : str
    description     : str
    instruction     : str
    affected_areas  : str
    effective       : datetime
    onset           : datetime  # optional
    expires         : datetime
    ends            : datetime  # If diff from expires
    severity        : AlertSeverity
    certainty       : AlertCertainty
    urgency         : AlertUrgency
