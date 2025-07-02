from dataclasses import dataclass, fields
from datetime import timedelta
import logging
from typing import get_origin, Dict, List, Type

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.units import UnitQuantity

from .transient_models import (
    BooleanDataPoint,
    DataPoint,
    DataPointSource,
    NumericDataPoint,
    StatisticDataPoint,
    StringDataPoint,
    TimeDataPoint,
    TimeInterval,
    TimeIntervalWeatherData,
    WeatherData,
)

logger = logging.getLogger(__name__)



class IntervalDataPoints:
    data_interval_map  : Dict[ TimeInterval, DataPoint ]
    
    
  



class SourceFieldData:
    source_map     : Dict[ DataPointSource, IntervalDataPoints ]
    
    
    

@dataclass
class AggregatedIntervalWeatherData:

    interval_data  : TimeIntervalWeatherData
    source_data    : Dict[ str, SourceFieldData ]
    data_class     : Type[ WeatherData ]
    
    def add_source_data( self,
                         data_point_source     : DataPointSource,
                         source_interval_data  : TimeIntervalWeatherData ):
        assert isinstance( source_interval_data.data, self.data_class )
        assert self.interval_data.interval.overlaps( source_interval_data.interval )

        # How old source data has to be for lower priority sources to
        # override higher priority sources.
        #
        self.DATA_AGE_STALE_SECS = 2 * 60 * 60
        
        # Collate by the individual data point fields so we can more easily
        # aggregate source and interval data on a per-field basis.
        
        source_interval = source_interval_data.interval
        source_data = source_interval_data.data
        
        for a_field in fields( source_data ):
            field_name = a_field.name
            field_type = a_field.type
            field_base_type = get_origin(field_type) or field_type  

            if not issubclass( field_base_type, DataPoint ):
                continue

            source_data_point = getattr( source_data, field_name )
            self.source_data[field_name][data_point_source][source_interval] = source_data_point
            continue
        return
                  
    def reaggregate_source_data( self ):
        if not self.source_data:
            return
        
        for field_name, source_map in self.source_data.items():

            data_point_source = self.get_best_data_point_source( source_map )
            interval_data_point_map = source_map[data_point_source]

            if not interval_data_point_map:
                setattr( self.interval_data.data, field_name, None )
                continue

            if len(interval_data_point_map) == 1:
                new_data_point = next( iter( interval_data_point_map.values() ))
                setattr( self.interval_data.data, field_name, new_data_point )
                continue
            
            data_point = getattr( self.interval_data.data, field_name )

            if isinstance( data_point, NumericDataPoint ):
                new_data_point = self.aggregate_numeric_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            elif isinstance( data_point, BooleanDataPoint ):
                new_data_point = self.aggregate_boolean_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            elif isinstance( data_point, TimeDataPoint ):
                new_data_point = self.aggregate_time_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            elif isinstance( data_point, StringDataPoint ):
                new_data_point = self.aggregate_string_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            elif isinstance( data_point, StatisticDataPoint ):
                new_data_point = self.aggregate_statistic_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            
            setattr( self.interval_data.data, field_name, new_data_point )
            continue
        return

    def get_best_data_point_source(
            self,
            source_map : Dict[ DataPointSource, Dict[ TimeInterval, DataPoint ]] ) -> DataPointSource:

        data_point_source_list = list( source_map.keys() )
        data_point_source_list.sort( key = lambda item: item.priority )

        # First, try the highest priority source whose data is not "stale".
        now = datetimeproxy.now()
        stale_data_tuple_list = list()
        for data_point_source in data_point_source_list:
            interval_map = source_map[data_point_source]
            max_source_datetime = max([ x.source_datetime for x in interval_map.values() ])
            source_data_age = now - max_source_datetime
            if source_data_age.total_seconds() < self.DATA_AGE_STALE_SECS:
                return data_point_source
            stale_data_tuple_list.append( ( data_point_source, source_data_age ) )
            continue

        # Else, if all data is stale, return freshest data.
        stale_data_tuple_list.sort( key = lambda item: item[1], reverse = True )
        return stale_data_tuple_list[0]

    def aggregate_numeric_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> NumericDataPoint:
        assert bool( interval_data_point_map )

        total_weighted_quantity = None
        total_overlap_duration = 0.0
        
        for time_interval, source_data_point in interval_data_point_map.items():
            assert isinstance( source_data_point, NumericDataPoint )
            if total_weighted_quantity is None:
                total_weighted_quantity = UnitQuantity( 0, source_data_point.quantity.units )
            
            overlap_seconds = self.interval_data.interval.overlap_seconds( time_interval )
            total_weighted_quantity += overlap_seconds * source_data_point.quantity
            total_overlap_duration += overlap_seconds
            continue

        if total_weighted_quantity is None:
            return None
        aggregated_quanity = total_weighted_quantity / total_overlap_duration.total_seconds()

        return NumericDataPoint(
            weather_station = None,
            source_datetime = None,
            quantity = aggregated_quanity,
        )
        
    def aggregate_boolean_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> BooleanDataPoint:
        assert bool( interval_data_point_map )
        
        total_true_duration = 0.0
        total_false_duration = 0.0
            
        for time_interval, source_data_point in interval_data_point_map.items():
            assert isinstance( source_data_point, BooleanDataPoint )
            
            overlap_seconds = self.interval_data.interval.overlap_seconds( time_interval )
            if source_data_point.value:
                total_true_duration += overlap_seconds
            else:
                total_false_duration == overlap_seconds
            continue

        if total_true_duration > total_false_duration:
            aggregated_value = True
        else:
            aggregated_value = False
        return BooleanDataPoint(
            weather_station = None,
            source_datetime = None,
            value = aggregated_value,
        )

    def aggregate_time_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> TimeDataPoint:
        assert bool( interval_data_point_map )

        max_value = None
        max_value_duration = 0.0
            
        for time_interval, source_data_point in interval_data_point_map.items():
            assert isinstance( source_data_point, TimeDataPoint )
            
            overlap_seconds = self.interval_data.interval.overlap_seconds( time_interval )
            if overlap_seconds > max_value_duration:
                max_value = source_data_point.value
                max_value_duration = overlap_seconds
            continue

        return TimeDataPoint(
            weather_station = None,
            source_datetime = None,
            value = max_value,
        )

    def aggregate_string_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> StringDataPoint:
        assert bool( interval_data_point_map )

        max_value = None
        max_value_duration = 0.0
            
        for time_interval, source_data_point in interval_data_point_map.items():
            assert isinstance( source_data_point, TimeDataPoint )
            
            overlap_seconds = self.interval_data.interval.overlap_seconds( time_interval )
            if overlap_seconds > max_value_duration:
                max_value = source_data_point.value
                max_value_duration = overlap_seconds
            continue

        return StringDataPoint(
            weather_station = None,
            source_datetime = None,
            value = max_value,
        )

    def aggregate_statistic_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> StatisticDataPoint:
        assert bool( interval_data_point_map )

        min_quantity = None
        max_quantity = None
        total_weighted_quantity = None
        total_overlap_duration = 0.0
        
        for time_interval, source_data_point in interval_data_point_map.items():
            assert isinstance( source_data_point, StatisticDataPoint )
            if ( min_quantity is None) or ( source_data_point.quantity_min < min_quantity ):
                min_quantity = source_data_point.quantity_min
            if ( max_quantity is None) or ( source_data_point.quantity_max > max_quantity ):
                max_quantity = source_data_point.quantity_max
                
            if total_weighted_quantity is None:
                total_weighted_quantity = UnitQuantity( 0, source_data_point.quantity.units )
            
            overlap_seconds = self.interval_data.interval.overlap_seconds( time_interval )
            total_weighted_quantity += overlap_seconds * source_data_point.quantity
            total_overlap_duration += overlap_seconds
            continue

        if total_weighted_quantity is None:
            return None
        
        aggregated_quanity = total_weighted_quantity / total_overlap_duration.total_seconds()

        return StatisticDataPoint(
            weather_station = None,
            source_datetime = None,
            quantity_min = min_quantity,
            quantity_ave = aggregated_quanity,
            quantity_max = max_quantity,
        )

    @classmethod
    def from_time_interval( cls, time_interval : TimeInterval ):
        interval_data = TimeIntervalWeatherData(
            interval = time_interval,
        )
        return AggregatedIntervalWeatherData(
            interval_data = interval_data,
            source_data = dict(),
        )


class AggregatedWeatherData:

    INTERVAL_MATCH_OVERLAP_THRESHOLD = 0.4
    INTERVAL_NEW_FRACTION_THRESHOLD = 0.6
    
    def __init__( self,
                  interval_hours      : int,
                  max_interval_count  : int,
                  is_order_ascending  : bool ):
        self._interval_hours = interval_hours
        self._max_interval_count = max_interval_count
        self._is_order_ascending = is_order_ascending 
        self._aggregated_interval_data_list = list()
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        try:
            self._initialize()
        except Exception as e:
            logger.exception( 'Problem trying to initialize time interval data', e )
        self._was_initialized = True
        return
   
    def _initialize(self):
        self._update_intervals()
        return

    def add_data( self,
                  data_point_source       : DataPointSource,
                  new_interval_data_list  : List[ TimeIntervalWeatherData ] ):

        self._add_source_data_to_interval_data(
            data_point_source = data_point_source,
            new_interval_data_list = new_interval_data_list,
        )
        for aggregated_interval_data in self._aggregated_interval_data_list:
            aggregated_interval_data.reaggregate_source_data()
            continue
        return
        
    def _add_source_data_to_interval_data( self,
                                           data_point_source          : DataPointSource,
                                           source_interval_data_list  : List[ TimeIntervalWeatherData ] ):
        """ Distribute source interval data into the existing aggregate intervals it overlaps with. """
        
        for source_interval_data in source_interval_data_list:
            for aggregated_interval_data in self._aggregated_interval_data_list:
                existing_interval = aggregated_interval_data.interval_data.interval
                overlaps = existing_interval.overlaps( source_interval_data.interval )
                if overlaps:
                    aggregated_interval_data.add_source_data(
                        data_point_source = data_point_source,
                        source_interval_data = source_interval_data,
                    )
                continue
            continue
        return
        
    def _update_intervals( self ):
        """ Adjust the intervals based on current time (truncating old, adding new) """
        
        existing_aggregated_interval_data_map = dict()
        for aggregated_interval_data in self._aggregated_interval_data_list:
            time_interval = aggregated_interval_data.interval_data.interval
            existing_aggregated_interval_data_map[time_interval] = aggregated_interval_data
            continue

        new_aggregated_interval_data_list = list()
        new_time_interval_list = self._get_calculated_intervals()

        for new_time_interval in new_time_interval_list:
            if new_time_interval in existing_aggregated_interval_data_map:
                aggregated_interval_data = existing_aggregated_interval_data_map[new_time_interval]
            else:
                aggregated_interval_data = AggregatedIntervalWeatherData.from_time_interval(
                    time_interval = new_time_interval,
                )
            new_aggregated_interval_data_list.append( aggregated_interval_data )
            continue

        self._aggregated_interval_data_list = new_aggregated_interval_data_list
        return
        
    def _get_calculated_intervals( self ):
        """ Create the intervals needed for the current time. """
        
        now = datetimeproxy.now()
        
        rounded_start = now.replace(
            minute = 0, second = 0, microsecond = 0
        ) - timedelta( hours = now.hour % self._interval_hours )
        
        if ( now == rounded_start ) and not self._is_order_ascending:
            rounded_start -= timedelta( hours = self._interval_hours )  

        time_interval_list = list()

        for idx in range( self._max_interval_count ):
            if self._is_order_ascending:
                interval_start = rounded_start + timedelta( hours = idx * self._interval_hours )
                interval_end = rounded_start + timedelta( hours = ( idx + 1 ) * self._interval_hours )
            else:
                interval_start = rounded_start - timedelta( hours = idx * self._interval_hours )
                interval_end = rounded_start - timedelta( hours = ( idx + 1 ) * self._interval_hours )

            time_interval = TimeInterval(
                start = interval_start,
                end = interval_end,
            )
            time_interval_list.append( time_interval )
            continue

        return time_interval_list

        


    
