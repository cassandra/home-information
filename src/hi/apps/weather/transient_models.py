from dataclasses import dataclass
from datetime import date, datetime, time

from hi.units import UnitQuantity

from .enums import (
    AlertCategory,
    AlertCertainty,
    AlertSeverity,
    AlertStatus,
    AlertUrgency,
    MoonPhase,
    SkyCondition,
    WeatherSource,
)


@dataclass
class WeatherDataPoint:

    source           : WeatherSource
    source_datetime  : datetime
    elevation        : UnitQuantity
    quantity         : UnitQuantity

    
@dataclass
class TimeDataPoint:
    source           : WeatherSource
    source_datetime  : datetime
    value            : time

 
@dataclass
class WeatherConditionsData:
    temperature                : WeatherDataPoint
    temperature_min_last_24h   : WeatherDataPoint
    temperature_max_last_24h   : WeatherDataPoint
    cloud_cover                : WeatherDataPoint
    windspeed_low              : WeatherDataPoint
    windpeed_average           : WeatherDataPoint
    windspeed_max              : WeatherDataPoint  # a.k.a., "wind gust"
    wind_direction             : WeatherDataPoint  # 0 to 360
    relative_humidity          : WeatherDataPoint
    precipitation_last_hour    : WeatherDataPoint
    precipitation_last_3h      : WeatherDataPoint
    precipitation_last_6h      : WeatherDataPoint
    precipitation_last_24h     : WeatherDataPoint
    barometric_pressure        : WeatherDataPoint
    visibility                 : WeatherDataPoint
    dew_point                  : WeatherDataPoint
    heat_index                 : WeatherDataPoint
    wind_chill                 : WeatherDataPoint
    sea_level_pressure         : WeatherDataPoint

    @property
    def sky_condition( self ) -> SkyCondition:
        if not self.cloud_cover:
            return None
        return SkyCondition.from_cloud_cover(
            cloud_cover_percent = self.cloud_cover.quantity.magnitude,
        )
    
    @property
    def windspeed(self):
        if self.windpeed_average:
            return self.windpeed_average
        if self.windpeed_max:
            return self.windpeed_max
        if self.windpeed_min:
            return self.windpeed_min
        return None

    @property
    def has_precipitation(self):
        return bool( self.precipitation_last_hour
                     or self.precipitation_last_3h
                     or self.precipitation_last_6h
                     or self.precipitation_last_24h )

    
@dataclass
class WeatherForecastData:
    period_start               : datetime
    period_end                 : datetime
    temperature_min            : WeatherDataPoint
    temperature_ave            : WeatherDataPoint
    temperature_max            : WeatherDataPoint
    relative_humidity          : WeatherDataPoint
    wind_speed_low             : WeatherDataPoint
    wind_speed_average         : WeatherDataPoint
    wind_speed_max             : WeatherDataPoint  # a.k.a., "wind gust"
    wind_direction             : WeatherDataPoint  # 0 to 360
    cloud_cover                : WeatherDataPoint
    precipitation_quantity     : WeatherDataPoint
    precipitation_probability  : WeatherDataPoint
    dew_point                  : WeatherDataPoint
    barometric_pressure        : WeatherDataPoint
    visibility                 : WeatherDataPoint
    dew_point                  : WeatherDataPoint
    heat_index                 : WeatherDataPoint
    wind_chill                 : WeatherDataPoint
    sea_level_pressure         : WeatherDataPoint

    
@dataclass
class WeatherHistoryData:
    period_start               : datetime
    period_end                 : datetime
    temperature_min            : WeatherDataPoint
    temperature_ave            : WeatherDataPoint
    temperature_max            : WeatherDataPoint
    relative_humidity          : WeatherDataPoint
    wind_speed_low             : WeatherDataPoint
    wind_speed_average         : WeatherDataPoint
    wind_speed_max             : WeatherDataPoint  # a.k.a., "wind gust"
    wind_direction             : WeatherDataPoint  # 0 to 360
    cloud_cover                : WeatherDataPoint
    precipitation_quantity     : WeatherDataPoint
    dew_point                  : WeatherDataPoint
    barometric_pressure        : WeatherDataPoint
    sea_level_pressure         : WeatherDataPoint
    heat_index                 : WeatherDataPoint
    wind_chill                 : WeatherDataPoint
    visibility                 : WeatherDataPoint

    
@dataclass
class DailyAstronomicalData:
    pass
    day                          : date
    sunrise                      : TimeDataPoint
    sunset                       : TimeDataPoint
    solar_noon                   : TimeDataPoint
    moonrise                     : TimeDataPoint
    moonset                      : TimeDataPoint
    moon_illumnination           : WeatherDataPoint  # Percent
    moon_is_waxing               : bool
    civil_twilight_begin         : TimeDataPoint
    civil_twilight_end           : TimeDataPoint
    nautical_twilight_begin      : TimeDataPoint
    nautical_twilight_end        : TimeDataPoint
    astronomical_twilight_begin  : TimeDataPoint
    astronomical_twilight_end    : TimeDataPoint

    @property
    def moon_phase(self) -> MoonPhase:
        if not self.moon_illumnination:
            return None
        return MoonPhase.from_illumination(
            illumination_percent = self.moon_illumnination.quantity.magnitude,
            is_waxing = self.moon_is_waxing,
        )

    @property
    def days_until_full_moon(self) -> int:
        if not self.moon_is_waxing:
            return round( 14.77 + self.days_until_new_moon() )
        return round( 14.77 * (( 100.0 - self.moon_illumnination.quantity.magnitude ) / 100.0 ))
    
    @property
    def days_until_new_moon(self):
        if self.moon_is_waxing:
            return round( 14.77 + self.days_until_full_moon() )
        return round( 14.77 * ( self.moon_illumnination.quantity.magnitude / 100.0 ))

    
@dataclass
class WeatherOverviewData:

    current_conditions_data   : WeatherConditionsData
    todays_astronomical_data  : DailyAstronomicalData


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
