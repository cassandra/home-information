from dataclasses import dataclass, field, fields
from datetime import datetime, time, timedelta
from typing import Generic, List, TypeVar, get_origin

from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

from .enums import (
    AlertCategory,
    AlertCertainty,
    AlertSeverity,
    AlertStatus,
    AlertUrgency,
    MoonPhase,
    SkyCondition,
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
)


@dataclass( frozen = True )
class DataPointSource:
    id        : str
    label     : str
    priority  : int  # Lower numbers are higher priority

    def __hash__(self):
        return hash( self.id )

    def __eq__(self, other):
        if not isinstance( other, WeatherStation ):
            return False
        return bool( self.id == other.id )

    
@dataclass( frozen = True )
class WeatherStation:
    source            : DataPointSource
    station_id        : str                 = None
    name              : str                 = None
    geo_location      : GeographicLocation  = None
    station_url       : str                 = None
    observations_url  : str                 = None
    forecast_url      : str                 = None

    @property
    def elevation(self) -> UnitQuantity:
        if self.geo_location:
            return self.geo_location.elevation
        return None

    @property
    def key(self):
        return f'{self.source}:{self.station_id}'
    
    def __hash__(self):
        return hash( ( self.source, self.station_id ) )

    def __eq__(self, other):
        if not isinstance( other, WeatherStation ):
            return False
        return ( self.source == other.source ) and ( self.station_id == other.station_id )

    
@dataclass
class DataPoint:
    """ Base class for all weather data point types. """
    weather_station  : WeatherStation
    source_datetime  : datetime
    elevation        : UnitQuantity

    def __post_init( self ):
        if ( self.elevation is None ) and self.weather_station:
            self.elevation = self.weather_station.elevation
        return
    
    @property
    def source(self) -> DataPointSource:
        if not self.weather_station:
            return None
        return self.weather_station.source
        
    
@dataclass
class NumericDataPoint( DataPoint ):
    quantity         : UnitQuantity

    
@dataclass
class BooleanDataPoint( DataPoint ):
    value            : bool

    
@dataclass
class TimeDataPoint( DataPoint ):
    value            : time

    
@dataclass
class StringDataPoint( DataPoint ):
    value            : str

    
@dataclass
class StatisticDataPoint( DataPoint ):
    quantity_min   : UnitQuantity
    quantity_ave   : UnitQuantity
    quantity_max   : UnitQuantity

    @property
    def quantity(self) -> UnitQuantity:
        if self.quantity_ave is not None:
            return self.quantity_ave
        if self.quantity_min is not None and self.quantity_max is not None:
            return ( self.quantity_min + self.quantity_max ) / 2.0
        if self.quantity_max is not None:
            return self.quantity_max
        if self.quantity_min is not None:
            return self.quantity_min
        return None

    
T = TypeVar("T")  # Define a generic type placeholder


@dataclass
class DataPointList( DataPoint, Generic[T] ):
    list_value       : List[ T ]


@dataclass
class WeatherData:
    """ Base class for all weather data that consists of a series of DataPoint fields """ 

    @property
    def weather_stations(self) -> List[ WeatherStation ]:
        weather_station_map = dict()
        for a_field in fields( self ):
            field_name = a_field.name
            field_type = a_field.type
            field_base_type = get_origin( field_type ) or field_type  

            if not issubclass( field_base_type, DataPoint ):
                continue
            datapoint = getattr( self, field_name )
            if not datapoint:
                continue
            weather_station_map[datapoint.weather_station.key] = datapoint.weather_station
            continue
        return list( weather_station_map.values() ) 


@dataclass
class CommonWeatherData( WeatherData ):
    """ For those data points shared between current conditions and forecasts. """
    
    description_short          : StringDataPoint     = None
    description_long           : StringDataPoint     = None
    is_daytime                 : BooleanDataPoint    = None
    cloud_cover                : NumericDataPoint    = None  # Percent
    cloud_ceiling              : NumericDataPoint    = None
    windspeed                  : StatisticDataPoint  = None  # max = "wind gust"
    wind_direction             : NumericDataPoint    = None  # 0 to 360
    relative_humidity          : NumericDataPoint    = None
    visibility                 : NumericDataPoint    = None
    dew_point                  : NumericDataPoint    = None
    heat_index                 : NumericDataPoint    = None
    wind_chill                 : NumericDataPoint    = None
    barometric_pressure        : NumericDataPoint    = None
    sea_level_pressure         : NumericDataPoint    = None

    @property
    def sky_condition( self ) -> SkyCondition:
        if self.cloud_cover is None:
            return None
        return SkyCondition.from_cloud_cover(
            cloud_cover_percent = self.cloud_cover.quantity.magnitude,
        )

    
@dataclass
class NotablePhenomenon:
    weather_phenomenon            : WeatherPhenomenon
    weather_phenomenon_modifier   : WeatherPhenomenonModifier
    weather_phenomenon_intensity  : WeatherPhenomenonIntensity
    in_vicinity                   : bool

    def __str__(self):
        if self.in_vicinity:
            result = f'Nearby: {self.weather_phenomenon.label}'
        else:
            result = self.weather_phenomenon.label
        if ( self.weather_phenomenon_modifier
             and ( self.weather_phenomenon_modifier != WeatherPhenomenonModifier.NONE )):
            result += f', {self.weather_phenomenon_modifier.label}'
        result += f' ({self.weather_phenomenon_intensity.label})'
        return result

            
@dataclass
class WeatherConditionsData( CommonWeatherData ):
    temperature                : NumericDataPoint                    = None
    temperature_min_last_24h   : NumericDataPoint                    = None
    temperature_max_last_24h   : NumericDataPoint                    = None
    precipitation_last_hour    : NumericDataPoint                    = None
    precipitation_last_3h      : NumericDataPoint                    = None
    precipitation_last_6h      : NumericDataPoint                    = None
    precipitation_last_24h     : NumericDataPoint                    = None
    notable_phenomenon_data    : DataPointList[ NotablePhenomenon ]  = None
    
    @property
    def has_precipitation(self):
        return bool( self.precipitation_last_hour is not None
                     or self.precipitation_last_3h is not None
                     or self.precipitation_last_6h is not None
                     or self.precipitation_last_24h is not None )

    
@dataclass
class TimeInterval:
    interval_start             : datetime          = None
    interval_end               : datetime          = None
    interval_name              : StringDataPoint   = None

    @property
    def interval_period(self) -> timedelta:
        return self.interval_end - self.interval_start





# ========================================
### ZZZ START: New Data Stuctures




    

@dataclass
class WeatherForecastData( CommonWeatherData ):
    zzz

@dataclass
class WeatherHistoryData( CommonWeatherData ):
    zzz

@dataclass
class AstronomicalData( WeatherData ):
    zzz

@dataclass( frozen = True )
class TimeInterval:
    start   : datetime          = None
    end     : datetime          = None
    name    : StringDataPoint   = None

    def __post_init__(self):
        # Invariant is start time always less that end time.
        assert self.start < self.end
        return
    
    def __lt__( self, other ):
        if not isinstance( other, TimeInterval ):
            return NotImplemented
        return self.start < other.start

    def __eq__(self, other):
        if not isinstance( other, TimeInterval ):
            return NotImplemented
        return ( self.start == other.start ) and ( self.end == other.end )

    def __hash__(self):
        return hash((self.start, self.end))
    
    def overlaps( self, other : 'TimeInterval' ) -> bool:
        if other.end <= self.start:
            return False
        if other.start >= self.end:
            return False
        return True
    
    def overlap_seconds( self, other : 'TimeInterval' ) -> float:
        overlap_start = max( self.start, other.start )
        overlap_end = min( self.end, other.end )
        return = ( overlap_end - overlap_start ).total_seconds()
        
    @property
    def interval_period(self) -> timedelta:
        return self.interval_end - self.interval_start
    
@dataclass
class TimeIntervalWeatherData ( WeatherData ):
    interval        : TimeInterval      = None
    data            : WeatherData       = None

@dataclass
class IntervalWeatherForecast( TimeIntervalWeatherData ):
    data            : WeatherForecastData       = None

@dataclass
class IntervalWeatherHistory( TimeIntervalWeatherData ):
    data            : WeatherHistoryData       = None

@dataclass
class IntervalAstronomical( TimeIntervalWeatherData ):
    data            : AstronomicalData       = None



    
### ZZZ END: New Data Stuctures
# ========================================






    


    
    
@dataclass
class TimeIntervalCommonWeatherData( TimeInterval, CommonWeatherData ):
    """
    For those data points shared by forecast and historical data (which are
    defined for a specific interval of time).
    """
    temperature                : StatisticDataPoint  = None
    precipitation_amount       : NumericDataPoint    = None
    

@dataclass
class WeatherForecastData( TimeIntervalCommonWeatherData ):
    precipitation_probability  : NumericDataPoint  = None

    
@dataclass
class WeatherHistoryData( TimeIntervalCommonWeatherData ):
    pass
    
    
@dataclass
class AstronomicalData( TimeInterval, WeatherData ):
    sunrise                      : TimeDataPoint     = None
    sunset                       : TimeDataPoint     = None
    solar_noon                   : TimeDataPoint     = None
    moonrise                     : TimeDataPoint     = None
    moonset                      : TimeDataPoint     = None
    moon_illumnination           : NumericDataPoint  = None  # Percent
    moon_is_waxing               : BooleanDataPoint  = None
    civil_twilight_begin         : TimeDataPoint     = None
    civil_twilight_end           : TimeDataPoint     = None
    nautical_twilight_begin      : TimeDataPoint     = None
    nautical_twilight_end        : TimeDataPoint     = None
    astronomical_twilight_begin  : TimeDataPoint     = None
    astronomical_twilight_end    : TimeDataPoint     = None

    @property
    def moon_phase(self) -> MoonPhase:
        if self.moon_illumnination is None:
            return None
        return MoonPhase.from_illumination(
            illumination_percent = self.moon_illumnination.quantity.magnitude,
            is_waxing = self.moon_is_waxing.value,
        )

    @property
    def days_until_full_moon(self) -> int:
        if self.moon_phase == MoonPhase.FULL_MOON:
            return 0
        if not self.moon_is_waxing.value:
            return round( 14.77 + self.days_until_new_moon )
        return round( 14.77 * (( 100.0 - self.moon_illumnination.quantity.magnitude ) / 100.0 ))
    
    @property
    def days_until_new_moon(self):
        if self.moon_phase == MoonPhase.NEW_MOON:
            return 0
        if self.moon_is_waxing.value:
            return round( 14.77 + self.days_until_full_moon )
        return round( 14.77 * ( self.moon_illumnination.quantity.magnitude / 100.0 ))

    
@dataclass
class WeatherOverviewData:

    current_conditions_data   : WeatherConditionsData
    todays_astronomical_data  : AstronomicalData

    
@dataclass
class HourlyForecast:
    data_list    : List[ WeatherForecastData ]  = field( default_factory = list )
    

@dataclass
class DailyForecast:
    data_list    : List[ WeatherForecastData ]  = field( default_factory = list )

    
@dataclass
class DailyHistory:
    data_list    : List[ WeatherHistoryData ]  = field( default_factory = list )

    
@dataclass
class DailyAstronomicalData:
    data_list    : List[ AstronomicalData ]  = field( default_factory = list )


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
