import logging
from typing import Dict, List, Optional

from hi.apps.config.settings_mixins import SettingsMixin
from .settings import WeatherSetting

logger = logging.getLogger(__name__)


class WeatherSettingsHelper( SettingsMixin ):

    @staticmethod
    def _source_setting_prefix( source_id: str ) -> str:
        return source_id.upper().replace( '-', '_' )

    def _get_weather_source_enabled_value(self, source_id: str, settings_manager):
        enabled_setting_name = f"{self._source_setting_prefix(source_id)}_ENABLED"

        try:
            setting_enum = getattr(WeatherSetting, enabled_setting_name)
        except AttributeError:
            logger.warning(f'No enabled setting found for weather source: {source_id}')
            return False

        value = settings_manager.get_setting_value(setting_enum)
        if value is None:
            return False
        # Handle string boolean values from database
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def is_weather_source_enabled(self, source_id: str) -> bool:
        return self._get_weather_source_enabled_value(source_id, self.settings_manager())
    
    async def is_weather_source_enabled_async(self, source_id: str) -> bool:
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return False
        return self._get_weather_source_enabled_value(source_id, settings_manager)
    
    def get_weather_source_base_url(self, source_id: str) -> Optional[str]:
        """Configured base URL for this source. Returns ``None`` if the
        setting is unset / empty so the caller can fall back to the
        source's canonical default."""
        setting_name = f"{self._source_setting_prefix(source_id)}_BASE_URL"
        try:
            setting_enum = getattr(WeatherSetting, setting_name)
        except AttributeError:
            return None
        value = self.settings_manager().get_setting_value(setting_enum)
        if value is None:
            return None
        value_str = str(value).strip()
        return value_str if value_str else None

    def get_weather_source_api_key(self, source_id: str) -> str:
        api_key_setting_name = f"{self._source_setting_prefix(source_id)}_API_KEY"
        try:
            setting_enum = getattr(WeatherSetting, api_key_setting_name)
        except AttributeError:
            logger.debug(f'No API key setting for weather source: {source_id}')
            return ''

        value = self.settings_manager().get_setting_value(setting_enum)
        return str(value) if value is not None else ''
    
    def get_enabled_weather_sources(self) -> List[str]:
        enabled_sources = []

        from .weather_source_discovery import WeatherSourceDiscovery
        discovered_sources = WeatherSourceDiscovery.discover_weather_data_source_instances()

        for source in discovered_sources:
            if self.is_weather_source_enabled(source.id):
                enabled_sources.append(source.id)

        return enabled_sources
    
    DEFAULT_POLLING_INTERVAL_SECONDS = 600
    DEFAULT_STARTUP_WARMUP_SECONDS = 30

    def _coerce_int_setting( self, value, default : int, label : str ) -> int:
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            logger.warning(
                f'Invalid {label} value: {value}, using default {default} seconds'
            )
            return default

    def get_default_polling_interval_secs(self) -> int:
        value = self.settings_manager().get_setting_value(
            WeatherSetting.DEFAULT_POLLING_INTERVAL_SECONDS )
        return self._coerce_int_setting(
            value, self.DEFAULT_POLLING_INTERVAL_SECONDS, 'polling interval' )

    async def get_default_polling_interval_secs_async(self) -> int:
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return self.DEFAULT_POLLING_INTERVAL_SECONDS
        value = settings_manager.get_setting_value(
            WeatherSetting.DEFAULT_POLLING_INTERVAL_SECONDS )
        return self._coerce_int_setting(
            value, self.DEFAULT_POLLING_INTERVAL_SECONDS, 'polling interval' )

    def get_startup_warmup_secs(self) -> int:
        value = self.settings_manager().get_setting_value(
            WeatherSetting.STARTUP_WARMUP_SECONDS )
        return self._coerce_int_setting(
            value, self.DEFAULT_STARTUP_WARMUP_SECONDS, 'startup warmup' )

    async def get_startup_warmup_secs_async(self) -> int:
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return self.DEFAULT_STARTUP_WARMUP_SECONDS
        value = settings_manager.get_setting_value(
            WeatherSetting.STARTUP_WARMUP_SECONDS )
        return self._coerce_int_setting(
            value, self.DEFAULT_STARTUP_WARMUP_SECONDS, 'startup warmup' )
    
    def is_weather_cache_enabled(self) -> bool:
        return self._get_weather_cache_enabled_value(self.settings_manager())
    
    def _get_weather_cache_enabled_value(self, settings_manager):
        value = settings_manager.get_setting_value(WeatherSetting.WEATHER_CACHE_ENABLED)
        if value is None:
            return True
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    async def is_weather_cache_enabled_async(self) -> bool:
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return True
        return self._get_weather_cache_enabled_value(settings_manager)

    def _get_weather_alerts_enabled_value(self, settings_manager):
        value = settings_manager.get_setting_value(WeatherSetting.WEATHER_ALERTS_ENABLED)
        if value is None:
            return True
        # Handle string boolean values from database
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def is_weather_alerts_enabled(self) -> bool:
        return self._get_weather_alerts_enabled_value(self.settings_manager())

    async def is_weather_alerts_enabled_async(self) -> bool:
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return True
        return self._get_weather_alerts_enabled_value(settings_manager)

    def get_weather_source_config(self, source_id: str) -> Dict[str, any]:
        return {
            'enabled': self.is_weather_source_enabled(source_id),
            'api_key': self.get_weather_source_api_key(source_id),
            'polling_interval_secs': self.get_default_polling_interval_secs(),
            'cache_enabled': self.is_weather_cache_enabled(),
        }
    
