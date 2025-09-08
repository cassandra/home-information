import asyncio
from dataclasses import fields
import logging
import threading
from typing import Dict, List

from django.http import HttpRequest
from django.template.loader import get_template

from hi.apps.alert.alert_mixins import AlertMixin
from hi.apps.common.singleton import Singleton
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.console.console_helper import ConsoleSettingsHelper

from hi.constants import DIVID

from .constants import WeatherConstants
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
    IntervalWeatherForecast,
    IntervalWeatherHistory,
    IntervalAstronomical,
    WeatherAlert,
)
from .interval_data_manager import IntervalDataManager
from .weather_alert_alarm_mapper import WeatherAlertAlarmMapper
from .daily_weather_tracker import DailyWeatherTracker
from .weather_settings_helper import WeatherSettingsHelper

logger = logging.getLogger(__name__)


class WeatherManager( Singleton, SettingsMixin, AlertMixin ):

    # Age of a weather DataPoint at which a lower priority source is
    # allowed to overwrite a higher priority source's (now stale) data.
    #
    STALE_DATA_POINT_AGE_SECONDS = 60 * 60

    TRACE = False  # For debugging
    
    def __init_singleton__(self):

        self._current_conditions_data = WeatherConditionsData()
        self._todays_astronomical_data = AstronomicalData()
        self._hourly_forecast = HourlyForecast()
        self._daily_forecast = DailyForecast()
        self._daily_history = DailyHistory()
        self._daily_astronomical_data = DailyAstronomicalData()
        self._weather_alerts = []  # List[WeatherAlert]
        
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
        self._weather_alert_alarm_mapper = WeatherAlertAlarmMapper()
        self._daily_weather_tracker = DailyWeatherTracker()
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
            # Populate any missing daily weather data with fallback values (defensive)
            try:
                location_key = self._get_location_key()
                self._daily_weather_tracker.populate_daily_fallbacks(
                    weather_conditions_data=self._current_conditions_data,
                    location_key=location_key
                )
            except Exception as e:
                logger.warning(f"Error populating daily weather fallbacks: {e}")
            
            return self._current_conditions_data
    
    def get_todays_astronomical_data(self) -> AstronomicalData:
        with self._data_sync_lock:
            return self._todays_astronomical_data
    
    def get_weather_overview_data(self) -> WeatherOverviewData:
        return WeatherOverviewData(
            current_conditions_data = self.get_current_conditions_data(),
            todays_astronomical_data = self.get_daily_astronomical_data,
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
    
    def get_weather_alerts(self) -> List[WeatherAlert]:
        with self._data_sync_lock:
            return self._weather_alerts
    
    async def update_current_conditions( self,
                                         data_point_source        : DataPointSource,
                                         weather_conditions_data  : WeatherConditionsData ):
        async with self._data_async_lock:
            self._update_environmental_data(
                current_data = self._current_conditions_data,
                new_data = weather_conditions_data,
                data_point_source = data_point_source,
            )
            
            # Record weather conditions for daily tracking (defensive - don't let this break main processing)
            try:
                location_key = self._get_location_key()
                self._daily_weather_tracker.record_weather_conditions(
                    weather_conditions_data=weather_conditions_data,
                    location_key=location_key
                )
            except Exception as e:
                logger.warning(f"Error recording daily weather tracking data: {e}")
        return

    async def update_todays_astronomical_data( self,
                                               data_point_source  : DataPointSource,
                                               astronomical_data  : AstronomicalData ):
        async with self._data_async_lock:
            self._update_environmental_data(
                current_data = self._todays_astronomical_data,
                new_data = astronomical_data,
                data_point_source = data_point_source,
            )
        return
            
    async def update_hourly_forecast( self,
                                      data_point_source   : DataPointSource,
                                      forecast_data_list  : List[IntervalWeatherForecast] ):
        """Update hourly forecast data using IntervalDataManager for interval reconciliation."""
        async with self._data_async_lock:
            logger.debug( f'Adding hourly forecast : {data_point_source.id} [{len(forecast_data_list)}]' )
            self._hourly_forecast_manager.add_data(
                data_point_source = data_point_source,
                new_interval_data_list = forecast_data_list
            )
            
            # Update canonical forecast data from aggregated intervals
            self._update_hourly_forecast_from_manager()
        return

    async def update_daily_forecast( self,
                                     data_point_source   : DataPointSource,
                                     forecast_data_list  : List[IntervalWeatherForecast] ):
        """Update daily forecast data using IntervalDataManager for interval reconciliation."""
        async with self._data_async_lock:
            logger.debug( f'Adding daily forecast: {data_point_source.id} [{len(forecast_data_list)}]' )
            self._daily_forecast_manager.add_data(
                data_point_source = data_point_source,
                new_interval_data_list = forecast_data_list
            )
            
            # Update canonical forecast data from aggregated intervals
            self._update_daily_forecast_from_manager()
        return

    async def update_daily_history( self,
                                    data_point_source  : DataPointSource,
                                    history_data_list  : List[IntervalWeatherHistory] ):
        """Update daily history data using IntervalDataManager for interval reconciliation.""" 
        async with self._data_async_lock:
            logger.debug( f'Adding daily history: {data_point_source.id} [{len(history_data_list)}]' )
            self._daily_history_manager.add_data(
                data_point_source = data_point_source,
                new_interval_data_list = history_data_list
            )
            
            # Update canonical history data from aggregated intervals
            self._update_daily_history_from_manager()
        return

    async def update_astronomical_data( self,
                                        data_point_source       : DataPointSource,
                                        astronomical_data_list  : List[IntervalAstronomical] ):
        """Update astronomical data using IntervalDataManager for interval reconciliation."""
        async with self._data_async_lock:
            logger.debug( f'Adding astronomical: {data_point_source.id}'
                          f' [{len(astronomical_data_list)} items]' )
            self._daily_astronomical_manager.add_data(
                data_point_source = data_point_source,
                new_interval_data_list = astronomical_data_list
            )
            # Update canonical astronomical data from aggregated intervals
            self._update_daily_astronomical_from_manager()
        return

    async def update_weather_alerts( self,
                                     data_point_source  : DataPointSource,
                                     weather_alerts     : List[WeatherAlert] ):
        """Update weather alerts from data sources and create system alarms for qualifying alerts."""
        # Check if weather alerts processing is enabled
        weather_settings_helper = WeatherSettingsHelper()
        if not weather_settings_helper.is_weather_alerts_enabled():
            logger.debug(f'Weather alerts processing disabled, ignoring'
                         f' {len(weather_alerts)} alerts from {data_point_source.id}')
            return
            
        async with self._data_async_lock:
            logger.debug( f'Received weather alerts from {data_point_source.id}:'
                          f' {len(weather_alerts)} alerts' )
            
            # For now, simply replace all alerts with the new ones from this source
            # TODO: Future enhancement could merge alerts from multiple sources
            self._weather_alerts = weather_alerts
            
            # Log alerts for development visibility
            for alert in weather_alerts:
                logger.info( f'Weather Alert: {alert.event_type.label}'
                             f' ({alert.event}) - {alert.severity.label} - {alert.headline}' )
            
            # Create system alarms from weather alerts
            try:
                alarms = self._weather_alert_alarm_mapper.create_alarms_from_weather_alerts(weather_alerts)
                
                # Add each alarm to the alert manager
                alert_manager = await self.alert_manager_async()
                if alert_manager:
                    for alarm in alarms:
                        await alert_manager.add_alarm(alarm)
                        logger.info(f'Added weather alarm to system: {alarm.signature}')
                else:
                    logger.warning('Alert manager not available, weather alarms not created')
                    
            except Exception as e:
                logger.exception(f'Error creating system alarms from weather alerts: {e}')
        return

    def _update_environmental_data( self,
                                    current_data       : EnvironmentalData,
                                    new_data           : EnvironmentalData,
                                    data_point_source  : DataPointSource ):
        """ Generic updating method for all subclass of EnvironmentalData """
        
        if self.TRACE:
            logger.debug( f'Updating {current_data.__class__} data from: {data_point_source.id}' )
        
        for field in fields( current_data ):
            field_name = field.name
            
            current_datapoint = getattr( current_data, field_name )
            new_datapoint = getattr( new_data, field_name )

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
                setattr( current_data, field_name, new_datapoint )
                continue
                    
            # Same and higher priority sources can overwrite as long as data is fresher.
            # (N.B. lower priority sources have larger integer values)
            current_priority = current_datapoint.source.priority
            new_priority = new_datapoint.source.priority
            if new_priority <= current_priority:
                if new_datapoint.source_datetime > current_datapoint.source_datetime:
                    if self.TRACE:
                        logger.debug( f'Overwrite with fresher data: {field_name} = {new_datapoint}' )
                    setattr( current_data, field_name, new_datapoint )
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
                logger.debug( f'Overwriting stale data:'
                              f' {field_name} = {new_datapoint} [age={current_datapoint_age}]' )

            setattr( current_data, field_name, new_datapoint )
            continue
        return

    # Removed useless conversion methods - interval types already extend IntervalEnvironmentalData

    # Helper methods for updating canonical data from IntervalDataManager
    
    def _update_hourly_forecast_from_manager(self):
        """Update canonical hourly forecast from aggregated interval data."""
        forecast_data_list = []
        for aggregated_data in self._hourly_forecast_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                # Create IntervalWeatherForecast with both interval and data
                interval_forecast = IntervalWeatherForecast(
                    interval=aggregated_data.interval_data.interval,
                    data=aggregated_data.interval_data.data
                )
                forecast_data_list.append(interval_forecast)
            continue
        
        self._hourly_forecast.data_list = forecast_data_list
        return

    def _update_daily_forecast_from_manager(self):
        """Update canonical daily forecast from aggregated interval data."""
        forecast_data_list = []
        for aggregated_data in self._daily_forecast_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                # Create IntervalWeatherForecast with both interval and data
                interval_forecast = IntervalWeatherForecast(
                    interval=aggregated_data.interval_data.interval,
                    data=aggregated_data.interval_data.data
                )
                forecast_data_list.append(interval_forecast)
            continue
        
        self._daily_forecast.data_list = forecast_data_list
        return

    def _update_daily_history_from_manager(self):
        """Update canonical daily history from aggregated interval data."""
        history_data_list = []
        for aggregated_data in self._daily_history_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                # Create IntervalWeatherHistory with both interval and data
                interval_history = IntervalWeatherHistory(
                    interval=aggregated_data.interval_data.interval,
                    data=aggregated_data.interval_data.data
                )
                history_data_list.append(interval_history)
            continue
        
        self._daily_history.data_list = history_data_list
        logger.debug(f'Updated daily history: {len(history_data_list)} items in data_list')
        return

    def _update_daily_astronomical_from_manager(self):
        """Update canonical daily astronomical data from aggregated interval data."""
        astronomical_data_list = []
        for aggregated_data in self._daily_astronomical_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:

                interval_astronomical = IntervalAstronomical(
                    interval=aggregated_data.interval_data.interval,
                    data=aggregated_data.interval_data.data
                )
                astronomical_data_list.append(interval_astronomical)
            continue
        
        self._daily_astronomical_data.data_list = astronomical_data_list
        return

    def get_status_id_replace_map( self, request : HttpRequest ) -> Dict[ str, str ]:

        weather_overview_data = self.get_weather_overview_data()
        context = { 'weather_overview_data': weather_overview_data }
        template = get_template( WeatherConstants.WEATHER_OVERVIEW_TEMPLATE_NAME )
        weather_overview_html_str = template.render( context, request = request )
        
        weather_alert_list = self.get_weather_alerts()
        alerts_context = { 
            'weather_alert_list': weather_alert_list
        }
        alerts_template = get_template( 'weather/panes/weather_alerts.html' )
        weather_alerts_html_str = alerts_template.render( alerts_context, request = request )
        
        return {
            DIVID['WEATHER_OVERVIEW']: weather_overview_html_str,
            DIVID['WEATHER_ALERTS']: weather_alerts_html_str,
        }
    
    def _get_location_key(self):
        """
        Generate a location key for the daily weather tracker.
            
        Returns:
            String key representing the geographic location
        """
        console_helper = ConsoleSettingsHelper()
        geo_location = console_helper.get_geographic_location()
        
        if geo_location:
            # Create location key from lat/lon rounded to 3 decimal places
            return f"{geo_location.latitude:.3f},{geo_location.longitude:.3f}"
        
        # Ultimate fallback
        return "default"

    
