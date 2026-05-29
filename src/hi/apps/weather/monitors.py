import asyncio
import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from hi.apps.config.settings_mixins import SettingsMixin
from hi.apps.system.provider_info import ProviderInfo

from .weather_settings_helper import WeatherSettingsHelper
from .weather_source_discovery import WeatherSourceDiscovery
from .weather_source_manager import WeatherSourceManager

logger = logging.getLogger(__name__)


class WeatherMonitor( PeriodicMonitor, SettingsMixin ):

    MONITOR_ID = 'hi.apps.weather.monitor'

    def __init__( self ):
        self._settings_helper = WeatherSettingsHelper()
        # Subclass-owned cache of the configured polling interval.
        # Seeded with the default; ``initialize`` reads the saved value
        # via the async-safe path, and a settings change listener
        # refreshes it whenever the operator edits it on the config
        # page. The framework calls ``get_polling_interval_secs`` each
        # tick and reads this attribute.
        self._polling_interval_secs = (
            WeatherSettingsHelper.DEFAULT_POLLING_INTERVAL_SECONDS
        )
        super().__init__( id = self.MONITOR_ID )
        self._weather_data_source_instance_list = list()
        self._started_datetime = datetimeproxy.now()
        return

    def get_polling_interval_secs(self) -> int:
        return self._polling_interval_secs

    async def initialize(self) -> None:
        # Pick up the operator's saved value before the loop begins.
        # The async helper handles the singleton's first-time DB init
        # safely; subsequent sync access (from the listener below) is
        # safe because that init has already happened here.
        self._polling_interval_secs = (
            await self._settings_helper.get_default_polling_interval_secs_async()
        )
        settings_manager = await self._settings_helper.settings_manager_async()
        if settings_manager is not None:
            settings_manager.register_change_listener( self._on_settings_changed )

        discovered_sources = WeatherSourceDiscovery.discover_weather_data_source_instances()
        self._weather_data_source_instance_list = discovered_sources

        weather_source_manager = WeatherSourceManager()
        weather_source_manager.add_api_health_status_provider_multi(
            api_health_status_provider_sequence = discovered_sources,
        )

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

    def _on_settings_changed(self) -> None:
        """Settings change listener. Sync because
        ``SettingsManager._notify_change_listeners`` calls callbacks
        synchronously; safe to do sync settings access because the
        singleton is already initialized by ``initialize`` above."""
        new_interval = self._settings_helper.get_default_polling_interval_secs()
        if new_interval != self._polling_interval_secs:
            logger.debug(
                f'WeatherMonitor polling interval changed: '
                f'{self._polling_interval_secs}s -> {new_interval}s'
            )
            self._polling_interval_secs = new_interval
        return

    @classmethod
    def get_provider_info(cls) -> ProviderInfo:
        return ProviderInfo(
            provider_id = cls.MONITOR_ID,
            provider_name = 'Weather Monitor',
            description = 'Weather data collection and monitoring',
        )

    async def do_work(self):

        # To help guard against hitting API rate limits, hold off on
        # issuing weather queries until server stays up a minimum amount of
        # time.
        #

        weather_source_manager = WeatherSourceManager()
        uptime = datetimeproxy.now() - self._started_datetime
        warmup_secs = await self._settings_helper.get_startup_warmup_secs_async()
        if uptime.total_seconds() < warmup_secs:
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
