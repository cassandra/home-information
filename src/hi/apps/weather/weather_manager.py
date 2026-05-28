import asyncio
from dataclasses import fields
import logging
import threading
from typing import Dict, List

from django.http import HttpRequest
from django.template.loader import get_template

from hi.apps.alert.alert_mixins import AlertMixin
from hi.apps.common import datetimeproxy
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
    WeatherPaneStatus,
    WeatherStats,
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

        self._hourly_forecast_manager = IntervalDataManager(
            interval_hours=1,
            max_interval_count=48,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        self._daily_forecast_manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=10,
            is_order_ascending=True,
            data_class=WeatherForecastData
        )
        self._daily_history_manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=30,
            is_order_ascending=False,
            data_class=WeatherHistoryData
        )
        self._daily_astronomical_manager = IntervalDataManager(
            interval_hours=24,
            max_interval_count=10,
            is_order_ascending=True,
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
            current_conditions_data = self.get_current_conditions_data(),
            todays_weather_stats = self.get_weather_stats_today(),
            todays_astronomical_data = self.get_todays_astronomical_data(),
        )

    def get_weather_pane_status(self) -> WeatherPaneStatus:
        """Status line content for the current-conditions pane,
        computed from (data freshness x weather monitor health). The
        pane always renders something at the bottom: in the healthy
        path, the existing ``At HH:MM from <SOURCE>`` timestamp;
        otherwise this method's result drives the swap to a
        captioned/iconified line."""
        # Lazy imports keep the transient-models import graph quiet
        # (these modules also import from weather indirectly).
        from hi.apps.monitor.monitor_manager import AppMonitorManager
        from .monitors import WeatherMonitor

        conditions = self.get_current_conditions_data()
        if conditions.temperature is None:
            data_state = 'none'
        else:
            age_secs = (
                datetimeproxy.now() - conditions.temperature.source_datetime
            ).total_seconds()
            if age_secs > WeatherConstants.CONDITIONS_STALE_THRESHOLD_SECS:
                data_state = 'stale'
            else:
                data_state = 'fresh'

        health_status = None
        try:
            provider = AppMonitorManager().get_health_status_by_monitor_id(
                WeatherMonitor.MONITOR_ID,
            )
            health_status = provider.health_status
        except KeyError:
            # Monitor isn't registered. Treat the same as the defensive
            # "none x healthy" cell below -- caller will surface the
            # fallback caption.
            pass

        is_healthy = ( health_status is not None and health_status.is_healthy )

        if data_state == 'fresh':
            # The pane's existing timestamp line is sufficient.
            return WeatherPaneStatus()

        if data_state == 'stale' and is_healthy:
            # Keep the timestamp line; just tint it.
            return WeatherPaneStatus( is_timestamp_stale = True )

        if data_state == 'none' and is_healthy:
            # Reachable in practice: the weather monitor reports
            # aggregate health across multiple endpoints, so it can
            # land HEALTHY when only some of the underlying endpoints
            # succeed. The pane shows a neutral fallback instead of
            # going blank.
            return WeatherPaneStatus( caption_text = 'Waiting for data' )

        # Non-healthy: surface the monitor's own message.
        caption_text = None
        if health_status is not None:
            caption_text = health_status.last_message or health_status.status_display
        if not caption_text:
            caption_text = 'Weather data unavailable'
        return WeatherPaneStatus(
            caption_text = caption_text,
            health_status = health_status,
            is_timestamp_stale = ( data_state == 'stale' ),
        )

    def get_weather_stats_today(self) -> WeatherStats:
        location_key = self._get_location_key()
        return self._daily_weather_tracker.get_weather_stats_today(location_key)
    
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
    
    def get_active_weather_alerts(self) -> List[WeatherAlert]:
        """Stored alerts whose ``expires`` is still in the future (or
        unset). Filtering on read means a self-expiring alert drops
        from the UI on the next read, without waiting for the slower
        weather-source poll to overwrite the stored list.

        If a caller ever needs the unfiltered set, add an explicit
        ``get_all_weather_alerts`` rather than relaxing this method.
        """
        now = datetimeproxy.now()
        with self._data_sync_lock:
            return [
                alert for alert in self._weather_alerts
                if alert.expires is None or alert.expires > now
            ]
    
    async def update_current_conditions( self,
                                         data_point_source        : DataPointSource,
                                         weather_conditions_data  : WeatherConditionsData ):
        async with self._data_async_lock:
            self._update_environmental_data(
                current_data = self._current_conditions_data,
                new_data = weather_conditions_data,
                data_point_source = data_point_source,
            )

            # Defensive: daily tracking failures must not break main processing
            try:
                location_key = self._get_location_key()
                self._daily_weather_tracker.record_weather_conditions(
                    weather_conditions_data=self._current_conditions_data,
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
        async with self._data_async_lock:
            logger.debug( f'Adding hourly forecast : {data_point_source.id} [{len(forecast_data_list)}]' )
            self._hourly_forecast_manager.add_data(
                data_point_source = data_point_source,
                new_interval_data_list = forecast_data_list
            )

            self._update_hourly_forecast_from_manager()
        return

    async def update_daily_forecast( self,
                                     data_point_source   : DataPointSource,
                                     forecast_data_list  : List[IntervalWeatherForecast] ):
        async with self._data_async_lock:
            logger.debug( f'Adding daily forecast: {data_point_source.id} [{len(forecast_data_list)}]' )
            self._daily_forecast_manager.add_data(
                data_point_source = data_point_source,
                new_interval_data_list = forecast_data_list
            )

            self._update_daily_forecast_from_manager()
        return

    async def update_daily_history( self,
                                    data_point_source  : DataPointSource,
                                    history_data_list  : List[IntervalWeatherHistory] ):
        async with self._data_async_lock:
            logger.debug( f'Adding daily history: {data_point_source.id} [{len(history_data_list)}]' )
            self._daily_history_manager.add_data(
                data_point_source = data_point_source,
                new_interval_data_list = history_data_list
            )

            self._update_daily_history_from_manager()
        return

    async def update_astronomical_data( self,
                                        data_point_source       : DataPointSource,
                                        astronomical_data_list  : List[IntervalAstronomical] ):
        async with self._data_async_lock:
            logger.debug( f'Adding astronomical: {data_point_source.id}'
                          f' [{len(astronomical_data_list)} items]' )
            self._daily_astronomical_manager.add_data(
                data_point_source = data_point_source,
                new_interval_data_list = astronomical_data_list
            )
            self._update_daily_astronomical_from_manager()
        return

    async def update_weather_alerts( self,
                                     data_point_source  : DataPointSource,
                                     weather_alerts     : List[WeatherAlert] ):
        weather_settings_helper = WeatherSettingsHelper()
        if not await weather_settings_helper.is_weather_alerts_enabled_async():
            logger.debug(f'Weather alerts processing disabled, ignoring'
                         f' {len(weather_alerts)} alerts from {data_point_source.id}')
            return

        async with self._data_async_lock:
            logger.debug( f'Received weather alerts from {data_point_source.id}:'
                          f' {len(weather_alerts)} alerts' )

            # Replace all alerts with the new set from this source.
            # TODO: merge alerts when multiple sources are in play.
            self._weather_alerts = weather_alerts

            for alert in weather_alerts:
                logger.info( f'Weather Alert: {alert.event_type.label}'
                             f' ({alert.event}) - {alert.severity.label} - {alert.headline}' )

            try:
                alarms = self._weather_alert_alarm_mapper.create_alarms_from_weather_alerts(weather_alerts)

                alert_manager = await self.alert_manager_async()
                if alert_manager:
                    for alarm in alarms:
                        await alert_manager.upsert_alarm_async(alarm)
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

            # Skip non-DataPoint fields (None is allowed and falls through below)
            if current_datapoint is not None and not isinstance( current_datapoint, DataPoint ):
                continue

            if new_datapoint is None:
                continue

            if current_datapoint is None:
                if self.TRACE:
                    logger.debug( f'Setting first data: {field_name} = {new_datapoint}' )
                setattr( current_data, field_name, new_datapoint )
                continue

            # Same or higher priority sources can overwrite as long as data is fresher.
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

    def _update_hourly_forecast_from_manager(self):
        forecast_data_list = []
        for aggregated_data in self._hourly_forecast_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                interval_forecast = IntervalWeatherForecast(
                    interval=aggregated_data.interval_data.interval,
                    data=aggregated_data.interval_data.data
                )
                forecast_data_list.append(interval_forecast)
            continue

        self._hourly_forecast.data_list = forecast_data_list
        return

    def _update_daily_forecast_from_manager(self):
        forecast_data_list = []
        for aggregated_data in self._daily_forecast_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
                interval_forecast = IntervalWeatherForecast(
                    interval=aggregated_data.interval_data.interval,
                    data=aggregated_data.interval_data.data
                )
                forecast_data_list.append(interval_forecast)
            continue

        self._daily_forecast.data_list = forecast_data_list
        return

    def _update_daily_history_from_manager(self):
        history_data_list = []
        for aggregated_data in self._daily_history_manager._aggregated_interval_data_list:
            if aggregated_data.interval_data.data:
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
        context = {
            'weather_overview_data': weather_overview_data,
            'weather_pane_status': self.get_weather_pane_status(),
        }
        template = get_template( WeatherConstants.WEATHER_OVERVIEW_TEMPLATE_NAME )
        weather_overview_html_str = template.render( context, request = request )

        return {
            DIVID['WEATHER_OVERVIEW']: weather_overview_html_str,
        }
    
    def _get_location_key(self):
        console_helper = ConsoleSettingsHelper()
        geo_location = console_helper.get_geographic_location()

        if geo_location:
            # Lat/lon rounded to 3 decimal places (~110m precision).
            return f"{geo_location.latitude:.3f},{geo_location.longitude:.3f}"

        return "default"

    
