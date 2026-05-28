from dataclasses import dataclass, fields
import logging
from typing import Dict, Type

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.units import UnitQuantity

from .transient_models import (
    BooleanDataPoint,
    DataPoint,
    DataPointSource,
    NumericDataPoint,
    StringDataPoint,
    TimeDataPoint,
    TimeInterval,
    IntervalEnvironmentalData,
    EnvironmentalData,
)
from .interval_models import SourceFieldData

logger = logging.getLogger(__name__)


@dataclass
class AggregatedWeatherData:

    # How old source data has to be for lower priority sources to
    # override higher priority sources (in seconds)
    DATA_AGE_STALE_SECS = 2 * 60 * 60  # 2 hours
    
    interval_data  : IntervalEnvironmentalData
    source_data    : Dict[ str, SourceFieldData ]
    data_class     : Type[ EnvironmentalData ]
    
    def add_source_data( self,
                         data_point_source     : DataPointSource,
                         source_interval_data  : IntervalEnvironmentalData ):
        assert isinstance( source_interval_data.data, self.data_class )
        assert self.interval_data.interval.overlaps( source_interval_data.interval )

        # Collate by the individual data point fields so we can more easily
        # aggregate source and interval data on a per-field basis.

        source_interval = source_interval_data.interval
        source_data = source_interval_data.data

        from .model_helpers import is_datapoint_field

        for a_field in fields( source_data ):
            field_name = a_field.name

            if not is_datapoint_field(a_field.type):
                continue

            source_data_point = getattr( source_data, field_name )

            if source_data_point is not None:
                self.source_data[field_name][data_point_source][source_interval] = source_data_point
            continue
        return
                  
    def reaggregate_source_data( self ):
        if not self.source_data:
            return
        
        for field_name, source_map in self.source_data.items():

            data_point_source = self.get_best_data_point_source( source_map )
            if data_point_source is None:
                setattr( self.interval_data.data, field_name, None )
                continue
                
            interval_data_point_map = source_map[data_point_source]

            interval_data_point_map = {k: v for k, v in interval_data_point_map.items() if v is not None}

            if not interval_data_point_map:
                setattr( self.interval_data.data, field_name, None )
                continue

            if len(interval_data_point_map) == 1:
                new_data_point = next( iter( interval_data_point_map.values() ))
                setattr( self.interval_data.data, field_name, new_data_point )
                continue

            sample_data_point = next(iter(interval_data_point_map.values()))
                        
            if isinstance( sample_data_point, NumericDataPoint ):
                new_data_point = self.aggregate_numeric_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            elif isinstance( sample_data_point, BooleanDataPoint ):
                new_data_point = self.aggregate_boolean_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            elif isinstance( sample_data_point, TimeDataPoint ):
                new_data_point = self.aggregate_time_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            elif isinstance( sample_data_point, StringDataPoint ):
                new_data_point = self.aggregate_string_data_points(
                    interval_data_point_map = interval_data_point_map,
                )
            else:
                logger.warning(f"Unknown DataPoint type for field '{field_name}': {type(sample_data_point)}")
                continue
            
            setattr( self.interval_data.data, field_name, new_data_point )
            continue
        return

    def get_best_data_point_source(
            self,
            source_map : Dict[ DataPointSource, Dict[ TimeInterval, DataPoint ]] ) -> DataPointSource | None:
        if not source_map:
            return None

        data_point_source_list = list( source_map.keys() )
        data_point_source_list.sort( key = lambda item: item.priority )

        # First, try the highest priority source whose data is not "stale".
        now = datetimeproxy.now()
        stale_data_tuple_list = list()
        for data_point_source in data_point_source_list:
            interval_map = source_map[data_point_source]

            if not interval_map:
                continue

            valid_data_points = [dp for dp in interval_map.values() if dp is not None]
            if not valid_data_points:
                continue

            max_source_datetime = max(dp.source_datetime for dp in valid_data_points)
            source_data_age = now - max_source_datetime
            if source_data_age.total_seconds() < self.DATA_AGE_STALE_SECS:
                return data_point_source
            stale_data_tuple_list.append( ( data_point_source, source_data_age ) )
            continue

        # If all data is stale, return freshest data.
        if stale_data_tuple_list:
            stale_data_tuple_list.sort( key = lambda item: item[1], reverse = True )
            return stale_data_tuple_list[0][0]

        return None
        
    def aggregate_boolean_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> BooleanDataPoint:
        """ Aggregate boolean data points using duration-weighted majority voting. """
        assert bool( interval_data_point_map )
        
        total_true_duration = 0.0
        total_false_duration = 0.0
            
        for time_interval, source_data_point in interval_data_point_map.items():
            assert isinstance( source_data_point, BooleanDataPoint )
            
            overlap_seconds = self.interval_data.interval.overlap_seconds( time_interval )
            if source_data_point.value:
                total_true_duration += overlap_seconds
            else:
                total_false_duration += overlap_seconds
            continue

        if total_true_duration > total_false_duration:
            aggregated_value = True
        else:
            aggregated_value = False
        return BooleanDataPoint(
            station = None,
            source_datetime = None,
            value = aggregated_value,
        )

    def aggregate_time_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> TimeDataPoint:
        """ Aggregate time data points using longest duration selection. """
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
            station = None,
            source_datetime = None,
            value = max_value,
        )

    def aggregate_string_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> StringDataPoint:
        """ Aggregate string data points using longest duration selection. """
        assert bool( interval_data_point_map )

        max_value = None
        max_value_duration = 0.0
            
        for time_interval, source_data_point in interval_data_point_map.items():
            assert isinstance( source_data_point, StringDataPoint )
            
            overlap_seconds = self.interval_data.interval.overlap_seconds( time_interval )
            if overlap_seconds > max_value_duration:
                max_value = source_data_point.value
                max_value_duration = overlap_seconds
            continue

        return StringDataPoint(
            station = None,
            source_datetime = None,
            value = max_value,
        )

    def aggregate_numeric_data_points(
            self,
            interval_data_point_map : Dict[ TimeInterval, DataPoint ] ) -> NumericDataPoint:
        """ Aggregate numeric data points using time-weighted averaging. """
        assert bool( interval_data_point_map )

        min_quantity = None
        max_quantity = None
        total_weighted_quantity = None
        total_overlap_duration = 0.0
        quantity_units = None
        
        for time_interval, source_data_point in interval_data_point_map.items():
            assert isinstance( source_data_point, NumericDataPoint )
            if source_data_point.quantity_min is not None:
                if ( min_quantity is None) or ( source_data_point.quantity_min < min_quantity ):
                    min_quantity = source_data_point.quantity_min
            if source_data_point.quantity_max is not None:
                if ( max_quantity is None) or ( source_data_point.quantity_max > max_quantity ):
                    max_quantity = source_data_point.quantity_max
                
            overlap_seconds = self.interval_data.interval.overlap_seconds( time_interval )
            
            if total_weighted_quantity is None:
                total_weighted_quantity = overlap_seconds * source_data_point.quantity.magnitude
                total_overlap_duration = overlap_seconds
                quantity_units = source_data_point.quantity.units
            else:
                total_weighted_quantity += overlap_seconds * source_data_point.quantity.magnitude
                total_overlap_duration += overlap_seconds
            continue

        if total_weighted_quantity is None:
            return None
        
        aggregated_magnitude = total_weighted_quantity / total_overlap_duration
        aggregated_quanity = UnitQuantity(aggregated_magnitude, quantity_units)

        return NumericDataPoint(
            station = None,
            source_datetime = None,
            quantity_min = min_quantity,
            quantity_ave = aggregated_quanity,
            quantity_max = max_quantity,
        )

    @classmethod
    def from_time_interval( cls, time_interval : TimeInterval, data_class : Type[ EnvironmentalData ] ):
        from .interval_models import SourceFieldData
        from dataclasses import fields

        from .model_helpers import is_datapoint_field

        source_data = {}
        data_instance = data_class()
        for field in fields(data_instance):
            if is_datapoint_field(field.type):
                source_data[field.name] = SourceFieldData()
            
        interval_data = IntervalEnvironmentalData(
            interval = time_interval,
            data = data_instance,
        )
        return AggregatedWeatherData(
            interval_data = interval_data,
            source_data = source_data,
            data_class = data_class,
        )
