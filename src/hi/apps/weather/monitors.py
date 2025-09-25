import asyncio
import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from hi.apps.alert.alert_mixins import AlertMixin
from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.system.provider_info import ProviderInfo

from .weather_settings_helper import WeatherSettingsHelper
from .weather_source_discovery import WeatherSourceDiscovery
from .weather_source_manager import WeatherSourceManager

logger = logging.getLogger(__name__)


class WeatherMonitor( PeriodicMonitor, AlertMixin, SettingsMixin ):

    MONITOR_ID = 'hi.apps.weather.monitor'
    WEATHER_POLLING_INTERVAL_SECS = 150
    STARTUP_SAFETY_SECS = 30
    
    def __init__( self ):
        super().__init__(
            id = self.MONITOR_ID,
            interval_secs = self.WEATHER_POLLING_INTERVAL_SECS,
        )
        self._weather_data_source_instance_list = list()
        self._started_datetime = datetimeproxy.now()
        self._settings_helper = WeatherSettingsHelper()
        return
    
    async def initialize(self) -> None:
        discovered_sources = WeatherSourceDiscovery.discover_weather_data_source_instances()
        self._weather_data_source_instance_list = discovered_sources

        weather_source_manager = WeatherSourceManager()
        weather_source_manager.add_api_health_status_provider_multi(
            api_health_status_provider_sequence = discovered_sources,
        )

        # During startup safety/warmup, consider everything healthy.
        for weather_data_source in self._weather_data_source_instance_list:
            is_enabled = await self._settings_helper.is_weather_source_enabled_async(
                weather_data_source.id
            )
            if is_enabled:
                weather_data_source.record_healthy()
            else:
                weather_data_source.record_disabled()
            continue
        return
    
    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'Weather Monitor',
            description = 'Weather data collection and monitoring',
            expected_heartbeat_interval_secs = cls.WEATHER_POLLING_INTERVAL_SECS,
        )

    async def do_work(self):

        # To help guard against hitting API rate limits, hold off on
        # issuing weather queries until server stays up a minimum amount of
        # time.
        #

        weather_source_manager = WeatherSourceManager()
        uptime = datetimeproxy.now() - self._started_datetime
        if uptime.total_seconds() < self.STARTUP_SAFETY_SECS:
            message = 'Startup safety period. Waiting to fetch.'
            logger.debug( message )
            self.record_warning( message )
            weather_source_manager.record_warning( message )
            return

        disabled_count = 0
        
        task_list = list()
        for weather_data_source in self._weather_data_source_instance_list:
            is_enabled = await self._settings_helper.is_weather_source_enabled_async(
                weather_data_source.id
            )
            if is_enabled:
                task = asyncio.create_task( weather_data_source.fetch() )
                task_list.append( task )
            else:
                weather_data_source.record_disabled()
                disabled_count += 1
                logger.debug( f'Weather source {weather_data_source.id} is disabled, skipping' )
            continue

        if task_list:
            await asyncio.gather( *task_list )
            message = f'Used {len(task_list)} weather sources, {disabled_count} disabled.'
            self.record_healthy( message )
            weather_source_manager.record_healthy( message )
        else:
            message = 'No enabled weather sources found'
            logger.debug( message )
            self.record_warning( message )
            weather_source_manager.record_warning( message )
        return

