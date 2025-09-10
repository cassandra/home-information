from dataclasses import dataclass, field, fields
from datetime import datetime, time, timedelta
from typing import Dict, Generic, List, Optional, Set, TypeVar

from pint.errors import OffsetUnitCalculusError

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
    WeatherEventType,
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
)


@dataclass( kw_only = True, frozen = True )
class DataPointSource:
    id           : str
    label        : str
    abbreviation : str
    priority     : int  # The lower the number, the higher the priority

    def __hash__(self):
        return hash( self.id )

    def __eq__(self, other):
        if not isinstance( other, DataPointSource ):
            return False
        return bool( self.id == other.id )

    
@dataclass( kw_only = True, frozen = True )
class Station:
    source            : DataPointSource
    station_id        : str                 | None = None
    name              : str                 | None = None
    geo_location      : GeographicLocation  | None = None
    station_url       : str                 | None = None
    observations_url  : str                 | None = None
    forecast_url      : str                 | None = None

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
        if not isinstance( other, Station ):
            return False
        return ( self.source == other.source ) and ( self.station_id == other.station_id )

    
@dataclass( kw_only = True )
class DataPoint:
    """ Base class for all weather data point types. """
    station          : Station
    source_datetime  : datetime

    def __str__(self):
        return f'{self.value_str} [{self.source_datetime}]'

    @property
    def value_str(self):
        # Use the default dataclass representation to avoid recursion
        return super().__str__()
    
    @property
    def elevation(self) -> UnitQuantity:
        if self.station:
            return self.station.elevation
        return None
    
    @property
    def source(self) -> DataPointSource:
        if not self.station:
            return None
        return self.station.source
        
    
T = TypeVar("T")  # Define a generic type placeholder


@dataclass( kw_only = True )
class DataPointList( DataPoint, Generic[T] ):
    list_value       : List[ T ]


@dataclass( kw_only = True )
class BooleanDataPoint( DataPoint ):
    value            : bool

    @property
    def value_str(self):
        return str(self.value)

    
@dataclass( kw_only = True )
class TimeDataPoint( DataPoint ):
    value            : time

    @property
    def value_str(self):
        return str(self.value)

    
@dataclass( kw_only = True )
class StringDataPoint( DataPoint ):
    value            : str

    @property
    def value_str(self):
        return self.value

    
@dataclass( kw_only = True )
class NumericDataPoint( DataPoint ):
    quantity_ave   : UnitQuantity  | None = None 
    quantity_min   : UnitQuantity  | None = None
    quantity_max   : UnitQuantity  | None = None

    @property
    def value_str(self):
        return f'[ {self.quantity_min}, {self.quantity_ave}, {self.quantity_max} ]' 

    def __post_init__(self):
        if self.quantity_ave is not None:
            if self.quantity_min is None:
                self.quantity_min = self.quantity_ave
            if self.quantity_max is None:
                self.quantity_max = self.quantity_ave
        elif self.quantity_min is not None and self.quantity_max is not None:
            if self.quantity_ave is None:
                # For offset units (like Celsius), convert to absolute units for arithmetic
                try:
                    self.quantity_ave = ( self.quantity_min + self.quantity_max ) / 2.0
                except OffsetUnitCalculusError:
                    # Handle offset unit arithmetic by converting to absolute units
                    # Convert to absolute units (e.g., Celsius -> Kelvin), average, then convert back
                    min_abs = self.quantity_min.to_base_units()
                    max_abs = self.quantity_max.to_base_units() 
                    ave_abs = (min_abs + max_abs) / 2.0
                    self.quantity_ave = ave_abs.to(self.quantity_min.units)
        elif self.quantity_min is not None:
            if self.quantity_ave is None:
                self.quantity_ave = self.quantity_min
            if self.quantity_max is None:
                self.quantity_max = self.quantity_min
        elif self.quantity_max is not None:
            if self.quantity_ave is None:
                self.quantity_ave = self.quantity_max
            if self.quantity_min is None:
                self.quantity_min = self.quantity_max
        else:
            raise ValueError('At least one constructor value required.')
        return
    
    @property
    def quantity(self) -> UnitQuantity:
        if self.quantity_ave is not None:
            return self.quantity_ave
        if self.quantity_min is not None and self.quantity_max is not None:
            return ( self.quantity_min + self.quantity_max ) / 2.0
        if self.quantity_max is not None:
            return self.quantity_max
        return self.quantity_min
    
    
@dataclass( kw_only = True )
class EnvironmentalData:
    """ Base class for all weather data that consists of a series of DataPoint fields """ 

    @property
    def stations(self) -> List[ Station ]:
        station_map = dict()
        for a_field in fields( self ):
            field_name = a_field.name
            datapoint = getattr( self, field_name )
            
            # Check if the actual value is a DataPoint instance (not the type annotation)
            if not isinstance( datapoint, DataPoint ):
                continue
            if not datapoint.station:
                continue
            station_map[datapoint.station.key] = datapoint.station
            continue
        return list( station_map.values() )

    @property 
    def data_source_counts(self) -> Dict[DataPointSource, int]:
        """Get counts of DataPoint fields by data source."""
        source_counts = dict()
        for a_field in fields( self ):
            field_name = a_field.name
            datapoint = getattr( self, field_name )
            
            # Check if the actual value is a DataPoint instance (not the type annotation)
            if not isinstance( datapoint, DataPoint ):
                continue
            if not datapoint.source:
                continue
                
            source = datapoint.source
            source_counts[source] = source_counts.get(source, 0) + 1
            continue
        return source_counts

    @property
    def data_sources(self) -> Set[DataPointSource]:
        """Get all data sources that have at least one DataPoint field."""
        return set(self.data_source_counts.keys()) 


@dataclass( kw_only = True )
class CommonWeatherData( EnvironmentalData ):
    """ For those data points shared between current conditions and forecasts. """
    
    description_short          : StringDataPoint     | None = None
    description_long           : StringDataPoint     | None = None
    is_daytime                 : BooleanDataPoint    | None = None
    temperature                : NumericDataPoint    | None = None
    precipitation              : NumericDataPoint    | None = None
    cloud_cover                : NumericDataPoint    | None = None  # Percent
    cloud_ceiling              : NumericDataPoint    | None = None
    windspeed                  : NumericDataPoint    | None = None  # max = "wind gust"
    wind_direction             : NumericDataPoint    | None = None  # 0 to 360
    relative_humidity          : NumericDataPoint    | None = None
    visibility                 : NumericDataPoint    | None = None
    dew_point                  : NumericDataPoint    | None = None
    heat_index                 : NumericDataPoint    | None = None
    wind_chill                 : NumericDataPoint    | None = None
    barometric_pressure        : NumericDataPoint    | None = None
    sea_level_pressure         : NumericDataPoint    | None = None

    @property
    def sky_condition( self ) -> SkyCondition:
        if self.cloud_cover is None:
            return None
        return SkyCondition.from_cloud_cover(
            cloud_cover_percent = self.cloud_cover.quantity.magnitude,
        )

    
@dataclass( kw_only = True )
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

            
@dataclass( kw_only = True )
class WeatherConditionsData( CommonWeatherData ):
    temperature_min_last_24h   : NumericDataPoint                    | None = None
    temperature_max_last_24h   : NumericDataPoint                    | None = None
    temperature_min_today      : NumericDataPoint                    | None = None
    temperature_max_today      : NumericDataPoint                    | None = None
    precipitation_last_hour    : NumericDataPoint                    | None = None
    precipitation_last_3h      : NumericDataPoint                    | None = None
    precipitation_last_6h      : NumericDataPoint                    | None = None
    precipitation_last_24h     : NumericDataPoint                    | None = None
    notable_phenomenon_data    : DataPointList[ NotablePhenomenon ]  | None = None
    
    @property
    def has_precipitation(self):
        return bool( self.precipitation_last_hour is not None
                     or self.precipitation_last_3h is not None
                     or self.precipitation_last_6h is not None
                     or self.precipitation_last_24h is not None )

    
@dataclass( kw_only = True )
class WeatherForecastData( CommonWeatherData ):
    precipitation_probability  : NumericDataPoint  | None = None

    
@dataclass( kw_only = True )
class WeatherHistoryData( CommonWeatherData ):
    pass

    
@dataclass( kw_only = True )
class AstronomicalData( EnvironmentalData ):
    sunrise                      : TimeDataPoint     | None = None
    sunset                       : TimeDataPoint     | None = None
    solar_noon                   : TimeDataPoint     | None = None
    moonrise                     : TimeDataPoint     | None = None
    moonset                      : TimeDataPoint     | None = None
    moon_illumnination           : NumericDataPoint  | None = None  # Percent
    moon_is_waxing               : BooleanDataPoint  | None = None
    civil_twilight_begin         : TimeDataPoint     | None = None
    civil_twilight_end           : TimeDataPoint     | None = None
    nautical_twilight_begin      : TimeDataPoint     | None = None
    nautical_twilight_end        : TimeDataPoint     | None = None
    astronomical_twilight_begin  : TimeDataPoint     | None = None
    astronomical_twilight_end    : TimeDataPoint     | None = None

    @property
    def moon_phase(self) -> MoonPhase:
        if self.moon_illumnination is None or self.moon_is_waxing is None:
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

    
@dataclass( kw_only = True, frozen = True )
class TimeInterval:
    start   : datetime          | None = None
    end     : datetime          | None = None
    name    : StringDataPoint   | None = None

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
        return ( overlap_end - overlap_start ).total_seconds()
        
    @property
    def interval_period(self) -> timedelta:
        return self.end - self.start

    
@dataclass( kw_only = True )
class IntervalEnvironmentalData ( EnvironmentalData ):
    interval        : TimeInterval       | None = None
    data            : EnvironmentalData  | None = None

    
@dataclass( kw_only = True )
class IntervalWeatherForecast( IntervalEnvironmentalData ):
    data            : WeatherForecastData       | None = None

    
@dataclass( kw_only = True )
class IntervalWeatherHistory( IntervalEnvironmentalData ):
    data            : WeatherHistoryData       | None = None

    
@dataclass( kw_only = True )
class IntervalAstronomical( IntervalEnvironmentalData ):
    data            : AstronomicalData       | None = None

    
@dataclass( kw_only = True )
class WeatherStats:
    temperature_min: Optional[NumericDataPoint] = None
    temperature_max: Optional[NumericDataPoint] = None

    @property
    def temperature(self) -> NumericDataPoint:
        if self.temperature_min and self.temperature_max:
            return NumericDataPoint(
                station = self.temperature_min.station,
                source_datetime = self.temperature_min.source_datetime,
                quantity_min = self.temperature_min.quantity,
                quantity_max = self.temperature_max.quantity,
            )
        return None
    

@dataclass( kw_only = True )
class WeatherOverviewData:

    current_conditions_data   : WeatherConditionsData
    todays_weather_stats      : WeatherStats          = None
    todays_astronomical_data  : AstronomicalData      = None

    
@dataclass( kw_only = True )
class HourlyForecast:
    data_list    : List[ IntervalWeatherForecast ]  = field( default_factory = list )
    

@dataclass( kw_only = True )
class DailyForecast:
    data_list    : List[ IntervalWeatherForecast ]  = field( default_factory = list )

    
@dataclass( kw_only = True )
class DailyHistory:
    data_list    : List[ IntervalWeatherHistory ]  = field( default_factory = list )

    
@dataclass( kw_only = True )
class DailyAstronomicalData:
    data_list    : List[ IntervalAstronomical ]  = field( default_factory = list )


@dataclass( kw_only = True )
class WeatherAlert:

    event_type      : WeatherEventType
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

    def css_class(self):
        """Return Bootstrap alert CSS class for this alert's severity."""
        return self.severity.css_class()
