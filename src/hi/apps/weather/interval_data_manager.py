from datetime import timedelta
import logging
from typing import List
import pytz

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.console.console_helper import ConsoleSettingsHelper

from .transient_models import (
    DataPointSource,
    TimeInterval,
    IntervalEnvironmentalData,
)
from .aggregated_weather_data import AggregatedWeatherData

logger = logging.getLogger(__name__)


class IntervalDataManager:

    INTERVAL_MATCH_OVERLAP_THRESHOLD = 0.4
    INTERVAL_NEW_FRACTION_THRESHOLD = 0.6

    TRACE = True  # For debugging
    
    def __init__( self,
                  interval_hours      : int,
                  max_interval_count  : int,
                  is_order_ascending  : bool,
                  data_class          : type ):
        self._interval_hours = interval_hours
        self._max_interval_count = max_interval_count
        self._is_order_ascending = is_order_ascending 
        self._data_class = data_class
        self._aggregated_interval_data_list = list()
        self._was_initialized = False
        
        # For daily intervals (24-hour), use local timezone boundaries
        # For hourly intervals (1-hour), continue using UTC boundaries
        self._use_local_timezone = (interval_hours == 24)
        if self._use_local_timezone:
            self._console_helper = ConsoleSettingsHelper()
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
                  new_interval_data_list  : List[ IntervalEnvironmentalData ] ):

        # Update intervals first to handle time passage (remove old, add new intervals)
        self._update_intervals()
        
        self._add_source_data_to_interval_data(
            data_point_source = data_point_source,
            source_interval_data_list = new_interval_data_list,
        )
        for aggregated_interval_data in self._aggregated_interval_data_list:
            aggregated_interval_data.reaggregate_source_data()
            continue
        return
        
    def _add_source_data_to_interval_data( self,
                                           data_point_source          : DataPointSource,
                                           source_interval_data_list  : List[ IntervalEnvironmentalData ] ):
        """ Distribute source interval data into the existing aggregate intervals it overlaps with. """

        if self.TRACE:
            logger.debug( f'Adding interval data from: {data_point_source.id} [{len(source_interval_data_list)} intervals]' )
            
        for source_interval_data in source_interval_data_list:
            for aggregated_interval_data in self._aggregated_interval_data_list:
                existing_interval = aggregated_interval_data.interval_data.interval
                overlaps = existing_interval.overlaps( source_interval_data.interval )
                if overlaps:
                    logger.debug( f'Overlapping intervals: src={source_interval_data.interval}, existing={existing_interval}' )
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
                aggregated_interval_data = AggregatedWeatherData.from_time_interval(
                    time_interval = new_time_interval,
                    data_class = self._data_class,
                )
            new_aggregated_interval_data_list.append( aggregated_interval_data )
            continue

        self._aggregated_interval_data_list = new_aggregated_interval_data_list
        return
        
    def _get_calculated_intervals( self ):
        """ Create the intervals needed for the current time. """
        
        if self._use_local_timezone:
            # For daily intervals, use local timezone boundaries
            return self._get_calculated_intervals_local_timezone()
        else:
            # For hourly intervals, use UTC boundaries
            return self._get_calculated_intervals_utc()
    
    def _get_calculated_intervals_utc( self ):
        """ Create UTC-based intervals (for hourly forecasts). """
        
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
                interval_end = rounded_start - timedelta( hours = idx * self._interval_hours )
                interval_start = rounded_start - timedelta( hours = ( idx + 1 ) * self._interval_hours )

            time_interval = TimeInterval(
                start = interval_start,
                end = interval_end,
            )
            time_interval_list.append( time_interval )
            continue

        return time_interval_list
    
    def _get_calculated_intervals_local_timezone( self ):
        """ Create local timezone-based intervals (for daily forecasts). """
        
        # Get current time in local timezone
        user_timezone = self._console_helper.get_tz_name()
        local_tz = pytz.timezone(user_timezone)
        utc_now = datetimeproxy.now()
        local_now = utc_now.astimezone(local_tz)
        
        if self.TRACE:
            logger.debug(f'Creating daily intervals for timezone: {user_timezone}')
            logger.debug(f'UTC now: {utc_now}')
            logger.debug(f'Local now: {local_now}')
        
        # For daily intervals, start from the beginning of the current day in local timezone
        local_day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # For historical data (descending), start from yesterday
        if not self._is_order_ascending:
            local_day_start = local_day_start  # Keep today's start for calculation reference
        
        time_interval_list = list()

        for idx in range( self._max_interval_count ):
            if self._is_order_ascending:
                # Future dates: today, tomorrow, etc.
                local_interval_start = local_day_start + timedelta(days=idx)
                local_interval_end = local_day_start + timedelta(days=idx + 1)
            else:
                # Past dates: yesterday, day before yesterday, etc.
                # idx=0 should be yesterday, idx=1 should be day before yesterday, etc.
                local_interval_start = local_day_start - timedelta(days=idx + 1)
                local_interval_end = local_day_start - timedelta(days=idx)

            # Convert local timezone boundaries back to UTC for internal storage
            utc_interval_start = local_interval_start.astimezone(pytz.UTC)
            utc_interval_end = local_interval_end.astimezone(pytz.UTC)
            
            time_interval = TimeInterval(
                start = utc_interval_start,
                end = utc_interval_end,
            )
            time_interval_list.append( time_interval )
            continue

        if self.TRACE:
            logger.debug(f'Created {len(time_interval_list)} daily intervals')
            for i, interval in enumerate(time_interval_list):
                local_start = interval.start.astimezone(local_tz)
                local_end = interval.end.astimezone(local_tz)
                logger.debug(f'  Interval {i}: {local_start.date()} to {local_end.date()} (local)')

        return time_interval_list

        


    
