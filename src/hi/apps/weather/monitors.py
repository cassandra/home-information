import asyncio
import importlib
import inspect
import logging
import os
from pathlib import Path
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from hi.apps.alert.alert_mixins import AlertMixin

from .weather_data_source import WeatherDataSource

logger = logging.getLogger(__name__)


class WeatherMonitor( PeriodicMonitor, AlertMixin ):

    WEATHER_POLLING_INTERVAL_SECS = 5
    STARTUP_SAFETY_SECS = 10
    
    def __init__( self ):
        super().__init__(
            id = 'weather-monitor',
            interval_secs = self.WEATHER_POLLING_INTERVAL_SECS,
        )
        self._weather_data_source_instance_list = list()
        self._started_datetime = datetimeproxy.now()
        return
    
    async def initialize(self) -> None:
        self._weather_data_source_instance_list = self.discover_weather_data_source_instances()
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
        
        logger.debug( 'Checking for weather data.' )
        task_list = list()
        for weather_data_source in self._weather_data_source_instance_list:
            task = asyncio.create_task( weather_data_source.fetch() )
            task_list.append( task )
            continue

        await asyncio.gather( *task_list )
        return

    def discover_weather_data_source_instances(self) -> List[ WeatherDataSource ]:

        sources_dir = os.path.join( Path( __file__ ).parent, 'weather_sources' )
        logger.debug( f'Discovering weather sources in: {sources_dir}' )

        discovered_source_instance_list = list()
        for file in os.listdir( sources_dir ):
            if not file.endswith(".py") or file == "__init__.py":
                continue
            module_name = f"hi.apps.weather.weather_sources.{file[:-3]}"
            module = importlib.import_module( module_name )

            for name, obj in inspect.getmembers( module, inspect.isclass ):
                if issubclass( obj, WeatherDataSource ) and obj is not WeatherDataSource:
                    discovered_source_instance = obj()
                    discovered_source_instance_list.append( discovered_source_instance )
                continue
            continue
        
        discovered_source_instance_list.sort( key = lambda item : item.priority )
        return discovered_source_instance_list       
