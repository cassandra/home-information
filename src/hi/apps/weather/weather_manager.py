import asyncio
from dataclasses import fields
import logging
import threading
from typing import get_origin, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin

from .transient_models import (
    AstronomicalData,
    DailyAstronomicalData,
    DailyForecast,
    DataPoint,
    DataPointSource,
    HourlyForecast,
    WeatherConditionsData,
    WeatherForecastData,
    WeatherHistoryData,
    EnvironmentalData,
    DailyHistory,
    WeatherOverviewData,
    IntervalEnvironmentalData,
    IntervalWeatherForecast,
    IntervalWeatherHistory,
)
from .weather_data_source import WeatherDataSource
from .interval_data_manager import IntervalDataManager

logger = logging.getLogger(__name__)


class WeatherManager( Singleton, SettingsMixin ):

    # Age of a weather DataPoint at which a lower priority source is
    # allowed to overwrite a higher priority source's (now stale) data.
    #
    STALE_DATA_POINT_AGE_SECONDS = 60 * 60

    TRACE = True  # For debugging
    
    def __init_singleton__(self):

        self._current_conditions_data = WeatherConditionsData()
        self._todays_astronomical_data = AstronomicalData()
        self._hourly_forecast = HourlyForecast()
        self._daily_forecast = DailyForecast()
        self._daily_history = DailyHistory()
        self._daily_astronomical_data = DailyAstronomicalData()
        
        # IntervalDataManager instances for handling API data reconciliation
        self._hourly_forecast_manager = IntervalDataManager(
            interval_hours=1,           # 1-hour intervals
            max_interval_count=48,      # 48 hours of forecast
            is_order_ascending=True,    # Future forecasts
            data_class=WeatherForecastData
        )
        self._daily_forecast_manager = IntervalDataManager(
            interval_hours=24,          # 24-hour intervals  
            max_interval_count=10,      # 10 days of forecast
            is_order_ascending=True,    # Future forecasts
            data_class=WeatherForecastData
        )
        self._daily_history_manager = IntervalDataManager(
            interval_hours=24,          # 24-hour intervals
            max_interval_count=30,      # 30 days of history
            is_order_ascending=False,   # Past history
            data_class=WeatherHistoryData
        )
        self._daily_astronomical_manager = IntervalDataManager(
            interval_hours=24,          # 24-hour intervals
            max_interval_count=10,      # 10 days of astronomical data
            is_order_ascending=True,    # Future astronomical data
            data_class=AstronomicalData
        )
        
        self._data_sync_lock = threading.Lock()
        self._data_async_lock = asyncio.Lock() 
        self._was_initialized = False
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        try:
            self._initialize()
        except Exception as e:
            logger.exception( 'Problem trying to initialize weather', e )
        self._was_initialized = True
        return

    def _initialize( self ):
        # Initialize all interval data managers
        self._hourly_forecast_manager.ensure_initialized()
        self._daily_forecast_manager.ensure_initialized()
        self._daily_history_manager.ensure_initialized()
        self._daily_astronomical_manager.ensure_initialized()
        return
    
    def get_current_conditions_data(self) -> WeatherConditionsData:
        with self._data_sync_lock:
            return self._current_conditions_data
    
    def get_todays_astronomical_data(self) -> AstronomicalData:
        with self._data_sync_lock:
            return self._todays_astronomical_data
    
    def get_weather_overview_data(self) -> WeatherOverviewData:
        return WeatherOverviewData(
            current_conditions_data = self._current_conditions_data,
            todays_astronomical_data = self._todays_astronomical_data,
        )
    
    def get_hourly_forecast(self) -> HourlyForecast:
        with self._data_sync_lock:
            return self._hourly_forecast
    
    def get_daily_forecast(self) -> DailyForecast:
        with self._data_sync_lock:
            return self._daily_forecast
    
    def get_daily_history(self) -> DailyHistory:
        with self._data_sync_lock:
            return self._daily_history

    def get_daily_astronomical_data(self) -> DailyAstronomicalData:
        with self._data_sync_lock:
            return self._daily_astronomical_data
    
    async def update_current_conditions( self,
                                         weather_data_source      : WeatherDataSource,
                                         weather_conditions_data  : WeatherConditionsData ):
        async with self._data_async_lock:
            self._update_weather_data(
                current_weather_data = self._current_conditions_data,
                new_weather_data = weather_conditions_data,
                data_point_source = weather_data_source.data_point_source,
            )
        return

    async def update_hourly_forecast( self,
                                      weather_data_source : WeatherDataSource,
                                      forecast_data_list  : List[IntervalWeatherForecast] ):
        """Update hourly forecast data using IntervalDataManager for interval reconciliation."""
        async with self._data_async_lock:
            # Convert IntervalWeatherForecast to IntervalEnvironmentalData format
            interval_data_list = self._convert_interval_forecast_to_interval_data(forecast_data_list)
            
            # Add to interval manager for aggregation
            self._hourly_forecast_manager.add_data(
                data_point_source = weather_data_source.data_point_source,
                new_interval_data_list = interval_data_list
            )
            
            # Update canonical forecast data from aggregated intervals
            self._update_hourly_forecast_from_manager()
        return

    async def update_daily_forecast( self,
                                     weather_data_source : WeatherDataSource,
                                     forecast_data_list  : List[IntervalWeatherForecast] ):
        """Update daily forecast data using IntervalDataManager for interval reconciliation."""
        async with self._data_async_lock:
            # Convert IntervalWeatherForecast to IntervalEnvironmentalData format
            interval_data_list = self._convert_interval_forecast_to_interval_data(forecast_data_list)
            
            # Add to interval manager for aggregation
            self._daily_forecast_manager.add_data(
                data_point_source = weather_data_source.data_point_source,
                new_interval_data_list = interval_data_list
            )
            
            # Update canonical forecast data from aggregated intervals
            self._update_daily_forecast_from_manager()
        return

    async def update_daily_history( self,
                                    weather_data_source : WeatherDataSource,
                                    history_data_list   : List[IntervalWeatherHistory] ):
        """Update daily history data using IntervalDataManager for interval reconciliation.""" 
        async with self._data_async_lock:
            # Convert IntervalWeatherHistory to IntervalEnvironmentalData format
            interval_data_list = self._convert_interval_history_to_interval_data(history_data_list)
            
            # Add to interval manager for aggregation
            self._daily_history_manager.add_data(
                data_point_source = weather_data_source.data_point_source,
                new_interval_data_list = interval_data_list
            )
            
            # Update canonical history data from aggregated intervals
            self._update_daily_history_from_manager()
        return

    async def update_astronomical_data( self,
                                        weather_data_source : WeatherDataSource,
                                        astronomical_data_list : List[AstronomicalData] ):
        """Update astronomical data using IntervalDataManager for interval reconciliation."""
        async with self._data_async_lock:
            # Convert astronomical data to IntervalEnvironmentalData format  
            interval_data_list = self._convert_astronomical_to_interval_data(astronomical_data_list)
            
            # Add to interval manager for aggregation
            self._daily_astronomical_manager.add_data(
                data_point_source = weather_data_source.data_point_source,
                new_interval_data_list = interval_data_list
            )
            
            # Update canonical astronomical data from aggregated intervals
            self._update_daily_astronomical_from_manager()
        return

    def _update_weather_data( self,
                              current_weather_data : EnvironmentalData,
                              new_weather_data     : EnvironmentalData,
                              data_point_source    : DataPointSource ):

        if self.TRACE:
            logger.debug( f'Updating weather data from: {data_point_source.id}' )
        
        now = datetimeproxy.now()
        for field in fields( current_weather_data ):
            field_name = field.name
            
            current_datapoint = getattr( current_weather_data, field_name )
            new_datapoint = getattr( new_weather_data, field_name )

            # Skip fields that are not DataPoint fields (but allow None datapoints to be processed)
            if current_datapoint is not None and not isinstance( current_datapoint, DataPoint ):
                continue

            # Skip data not present in source's data 
            if new_datapoint is None:
                continue

            # Always fill in blank data
            if current_datapoint is None:
                if self.TRACE:
                    logger.debug( f'Setting first data: {field_name} = {new_datapoint}' )
                setattr( current_weather_data, field_name, new_datapoint )
                continue
                    
            # Same and higher priority sources can overwrite as long as data is fresher.
            # (N.B. lower priority sources have larger integer values)
            current_priority = current_datapoint.source.priority
            new_priority = new_datapoint.source.priority
            if new_priority <= current_priority:
                if new_datapoint.source_datetime > current_datapoint.source_datetime:
                    if self.TRACE:
                        logger.debug( f'Overwrite with fresher data: {field_name} = {new_datapoint}' )
                    setattr( current_weather_data, field_name, new_datapoint )
                else:
                    if self.TRACE:
                        logger.debug( f'Skipping older data: {field_name} = {new_datapoint}' )
                continue
            
            # Lower priority sources can only overwrite if current data is stale and new data is newer.
            if new_datapoint.source_datetime <= current_datapoint.source_datetime:
                if self.TRACE:
                    logger.debug( f'Skipping old, lower priority data: {field_name} = {new_datapoint}' )
                continue

            current_datapoint_age = new_datapoint.source_datetime - current_datapoint.source_datetime
            if current_datapoint_age.total_seconds() < self.STALE_DATA_POINT_AGE_SECONDS:
                if self.TRACE:
                    logger.debug( f'Skipping lower priority data: {field_name} = {new_datapoint}' )
                continue

            if self.TRACE:
                logger.debug( f'Overwriting stale data: {field_name} = {new_datapoint} [age={current_datapoint_age}]' )

            setattr( current_weather_data, field_name, new_datapoint )
            continue
        return

    # Helper methods for converting API data to IntervalEnvironmentalData format
    
    def _convert_interval_forecast_to_interval_data(self, forecast_data_list: List[IntervalWeatherForecast]) -> List[IntervalEnvironmentalData]:
        """Convert IntervalWeatherForecast list to IntervalEnvironmentalData format."""
        interval_data_list = []
        for interval_forecast in forecast_data_list:
            if interval_forecast.interval and interval_forecast.data:
                interval_data = IntervalEnvironmentalData(
                    interval=interval_forecast.interval,
                    data=interval_forecast.data
                )
                interval_data_list.append(interval_data)
            continue
        return interval_data_list

    def _convert_interval_history_to_interval_data(self, history_data_list: List[IntervalWeatherHistory]) -> List[IntervalEnvironmentalData]:
        """Convert IntervalWeatherHistory list to IntervalEnvironmentalData format."""
        interval_data_list = []
        for interval_history in history_data_list:
            if interval_history.interval and interval_history.data:
                interval_data = IntervalEnvironmentalData(
                    interval=interval_history.interval,
                    data=interval_history.data
                )
                interval_data_list.append(interval_data)
            continue
        return interval_data_list

    def _convert_astronomical_to_interval_data(self, astronomical_data_list: List[AstronomicalData]) -> List[IntervalEnvironmentalData]:
        """Convert AstronomicalData list to IntervalEnvironmentalData format."""
        interval_data_list = []
        for astronomical_data in astronomical_data_list:
            # For astronomical data, create 24-hour intervals based on the date
            # We need to infer the date from the data points
            if astronomical_data.sunrise and astronomical_data.sunrise.source_datetime:
                date = astronomical_data.sunrise.source_datetime.date()
                from datetime import datetime, time
                from .transient_models import TimeInterval
                
                interval_start = datetime.combine(date, time.min)
                interval_end = datetime.combine(date, time.max)
                
                interval = TimeInterval(
                    start=interval_start,
                    end=interval_end
                )
                interval_data = IntervalEnvironmentalData(
                    interval=interval,
                    data=astronomical_data
                )
                interval_data_list.append(interval_data)
            continue
        return interval_data_list

    # Helper methods for updating canonical data from IntervalDataManager
    
    def _update_hourly_forecast_from_manager(self):
        """Update canonical hourly forecast from aggregated interval data."""
        forecast_data_list = []
        for aggregated_data in self._hourly_forecast_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                forecast_data_list.append(aggregated_data.interval_data.data)
            continue
        
        self._hourly_forecast.data_list = forecast_data_list
        return

    def _update_daily_forecast_from_manager(self):
        """Update canonical daily forecast from aggregated interval data."""
        forecast_data_list = []
        for aggregated_data in self._daily_forecast_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                forecast_data_list.append(aggregated_data.interval_data.data)
            continue
        
        self._daily_forecast.data_list = forecast_data_list
        return

    def _update_daily_history_from_manager(self):
        """Update canonical daily history from aggregated interval data."""
        history_data_list = []
        for aggregated_data in self._daily_history_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                history_data_list.append(aggregated_data.interval_data.data)
            continue
        
        self._daily_history.data_list = history_data_list
        return

    def _update_daily_astronomical_from_manager(self):
        """Update canonical daily astronomical data from aggregated interval data."""
        astronomical_data_list = []
        for aggregated_data in self._daily_astronomical_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                astronomical_data_list.append(aggregated_data.interval_data.data)
            continue
        
        self._daily_astronomical_data.data_list = astronomical_data_list
        return

    
