import asyncio
from dataclasses import fields
import logging
import threading
from typing import List, get_origin

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin

from .transient_models import (
    DailyAstronomicalData,
    DataPoint,
    DataPointSource,
    WeatherConditionsData,
    WeatherData,
    WeatherForecastData,
    WeatherHistoryData,
    WeatherOverviewData,
)
from .weather_data_source import WeatherDataSource

logger = logging.getLogger(__name__)


class WeatherManager( Singleton, SettingsMixin ):

    # Age of a weather DataPoint at which a lower priority source is
    # allowed to overwrite a higher priority source's (now stale) data.
    #
    STALE_DATA_POINT_AGE_SECONDS = 30 * 60

    def __init_singleton__(self):

        self._current_conditions_data = WeatherConditionsData()
        self._todays_astronomical_data = DailyAstronomicalData()
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
        return
    
    def get_current_conditions_data(self) -> WeatherConditionsData:
        with self._data_sync_lock:
            return self._current_conditions_data
    
    def get_todays_astronomical_data(self) -> DailyAstronomicalData:
        with self._data_sync_lock:
            return self._todays_astronomical_data
    
    def get_weather_overview_data(self) -> WeatherOverviewData:
        return WeatherOverviewData(
            current_conditions_data = self._current_conditions_data,
            todays_astronomical_data = self._todays_astronomical_data,
        )
    
    def get_hourly_forecast_data_list(self) -> List[ WeatherForecastData ]:
        with self._data_sync_lock:
            return []
    
    def get_daily_forecast_data_list(self) -> List[ WeatherForecastData ]:
        with self._data_sync_lock:
            return []
    
    def get_daily_history_data_list(self) -> List[ WeatherHistoryData ]:
        with self._data_sync_lock:
            return []

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

    def _update_weather_data( self,
                              current_weather_data : WeatherData,
                              new_weather_data     : WeatherData,
                              data_point_source    : DataPointSource ):

        now = datetimeproxy.now()
        for field in fields( current_weather_data ):
            field_name = field.name
            field_type = field.type
            field_base_type = get_origin(field_type) or field_type  

            if not issubclass( field_base_type, DataPoint ):
                continue
            
            current_datapoint = getattr( current_weather_data, field_name )
            new_datapoint = getattr( new_weather_data, field_name )

            # Skip data not present in source's data 
            if new_datapoint is None:
                continue

            # Always fill in blank data
            if current_datapoint is None:
                setattr( current_weather_data, field_name, new_datapoint )
                continue

            # Higher and same priority sources can always overwrite (if newer data).
            current_priority = current_datapoint.source.priority
            new_priority = new_datapoint.source.priority
            if new_priority <= current_priority:
                if new_datapoint.source_datetime > current_datapoint.source_datetime:
                    setattr( current_weather_data, field_name, new_datapoint )
                continue

            # Lower priority sources can only overwrite if data is stale.
            current_datapoint_age = now - current_datapoint.source_datetime
            if current_datapoint_age.total_seconds() < self.STALE_DATA_POINT_AGE_SECONDS:
                continue

            setattr( current_weather_data, field_name, new_datapoint )
            continue
        return
    
