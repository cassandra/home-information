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
)


@dataclass
class DataSource:
    id     : str
    label  : str

    
@dataclass
class NumericDataPoint:

    source           : DataSource
    source_datetime  : datetime
    elevation        : UnitQuantity
    quantity         : UnitQuantity

    
@dataclass
class BooleanDataPoint:
    source           : DataSource
    source_datetime  : datetime
    elevation        : UnitQuantity
    value            : time

    
@dataclass
class TimeDataPoint:
    source           : DataSource
    source_datetime  : datetime
    value            : time


@dataclass
class CommonWeatherData:

    cloud_cover                : NumericDataPoint  = None
    windspeed_min              : NumericDataPoint  = None
    windspeed_ave              : NumericDataPoint  = None
    windspeed_max              : NumericDataPoint  = None  # a.k.a., "wind gust"
    wind_direction             : NumericDataPoint  = None  # 0 to 360
    relative_humidity          : NumericDataPoint  = None
    visibility                 : NumericDataPoint  = None
    dew_point                  : NumericDataPoint  = None
    heat_index                 : NumericDataPoint  = None
    wind_chill                 : NumericDataPoint  = None
    barometric_pressure        : NumericDataPoint  = None
    sea_level_pressure         : NumericDataPoint  = None

    @property
    def windspeed(self):
        if self.windspeed_ave:
            return self.windspeed_ave
        if self.windspeed_max:
            return self.windspeed_max
        if self.windspeed_min:
            return self.windspeed_min
        return None

    
@dataclass
class WeatherConditionsData( CommonWeatherData ):
    temperature                : NumericDataPoint  = None
    temperature_min_last_24h   : NumericDataPoint  = None
    temperature_max_last_24h   : NumericDataPoint  = None
    precipitation_last_hour    : NumericDataPoint  = None
    precipitation_last_3h      : NumericDataPoint  = None
    precipitation_last_6h      : NumericDataPoint  = None
    precipitation_last_24h     : NumericDataPoint  = None

    @property
    def sky_condition( self ) -> SkyCondition:
        if not self.cloud_cover:
            return None
        return SkyCondition.from_cloud_cover(
            cloud_cover_percent = self.cloud_cover.quantity.magnitude,
        )
    
    @property
    def has_precipitation(self):
        return bool( self.precipitation_last_hour
                     or self.precipitation_last_3h
                     or self.precipitation_last_6h
                     or self.precipitation_last_24h )

    
@dataclass
class PeriodWeatherData( CommonWeatherData ):
    period_start               : datetime          = None
    period_end                 : datetime          = None
    temperature_min            : NumericDataPoint  = None
    temperature_ave            : NumericDataPoint  = None
    temperature_max            : NumericDataPoint  = None
    precipitation              : NumericDataPoint  = None

    @property
    def sky_condition( self ) -> SkyCondition:
        if not self.cloud_cover:
            return None
        return SkyCondition.from_cloud_cover(
            cloud_cover_percent = self.cloud_cover.quantity.magnitude,
        )

    @property
    def temperature(self):
        if self.temperature_ave:
            return self.temperature_ave
        if self.temperature_max:
            return self.temperature_max
        if self.temperature_min:
            return self.temperature_min
        return None
    

@dataclass
class WeatherForecastData( PeriodWeatherData ):
    precipitation_probability  : NumericDataPoint  = None

    
@dataclass
class WeatherHistoryData( PeriodWeatherData ):
    pass

    
@dataclass
class DailyAstronomicalData:
    day                          : date
    sunrise                      : TimeDataPoint
    sunset                       : TimeDataPoint
    solar_noon                   : TimeDataPoint
    moonrise                     : TimeDataPoint
    moonset                      : TimeDataPoint
    moon_illumnination           : NumericDataPoint  # Percent
    moon_is_waxing               : BooleanDataPoint
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
            is_waxing = self.moon_is_waxing.value,
        )

    @property
    def days_until_full_moon(self) -> int:
        if not self.moon_is_waxing.value:
            return round( 14.77 + self.days_until_new_moon() )
        return round( 14.77 * (( 100.0 - self.moon_illumnination.quantity.magnitude ) / 100.0 ))
    
    @property
    def days_until_new_moon(self):
        if self.moon_is_waxing.value:
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
