import asyncio
import logging
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from hi.apps.alert.alert_mixins import AlertMixin
from hi.apps.config.settings_mixins import SettingsMixin

from .weather_data_source import WeatherDataSource
from .weather_settings_helper import WeatherSettingsHelper
from .weather_source_discovery import WeatherSourceDiscovery

logger = logging.getLogger(__name__)


class WeatherMonitor( PeriodicMonitor, AlertMixin, SettingsMixin ):

    WEATHER_POLLING_INTERVAL_SECS = 5
    STARTUP_SAFETY_SECS = 10
    
    def __init__( self ):
        super().__init__(
            id = 'weather-monitor',
            interval_secs = self.WEATHER_POLLING_INTERVAL_SECS,
        )
        self._weather_data_source_instance_list = list()
        self._started_datetime = datetimeproxy.now()
        self._settings_helper = WeatherSettingsHelper()
        return
    
    async def initialize(self) -> None:
        discovered_sources = WeatherSourceDiscovery.discover_weather_data_source_instances()
        
        # Log discovered sources and their enabled status
        for source in discovered_sources:
            enabled_status = "enabled" if await self._settings_helper.is_weather_source_enabled_async(source.id) else "disabled"
            logger.info( f'Discovered weather source: {source.label} ({source.id}, priority {source.priority}) - {enabled_status}' )
            continue
            
        self._weather_data_source_instance_list = discovered_sources
        return
    
    async def do_work(self):

        # To help guard against hitting API rate limits, hold off on
        # issuing weather queries until server stays up a minimum amount of
        # time.
        #
        uptime = datetimeproxy.now() - self._started_datetime
        if uptime.total_seconds() < self.STARTUP_SAFETY_SECS:
            logger.debug( 'Startup safety period. Skipping weather data fetch.' )
            return
        
        task_list = list()
        for weather_data_source in self._weather_data_source_instance_list:
            # Only fetch from enabled weather sources
            if await self._settings_helper.is_weather_source_enabled_async(weather_data_source.id):
                task = asyncio.create_task( weather_data_source.fetch() )
                task_list.append( task )
            else:
                logger.debug( f'Weather source {weather_data_source.id} is disabled, skipping' )
            continue

        if task_list:
            await asyncio.gather( *task_list )
        else:
            logger.debug( 'No enabled weather sources found' )
        return

