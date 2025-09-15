import logging
from typing import Dict, List

from hi.apps.config.settings_mixins import SettingsMixin
from .settings import WeatherSetting

logger = logging.getLogger(__name__)


class WeatherSettingsHelper( SettingsMixin ):
    """Helper class to access weather-related settings."""
    
    def _get_weather_source_enabled_value(self, source_id: str, settings_manager):
        """Private helper to get weather source enabled value with any settings manager."""
        # Dynamically find the setting enum for this source
        enabled_setting_name = f"{source_id.upper()}_ENABLED"
        
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
        """Check if a specific weather source is enabled."""
        return self._get_weather_source_enabled_value(source_id, self.settings_manager())
    
    async def is_weather_source_enabled_async(self, source_id: str) -> bool:
        """Check if a specific weather source is enabled (async version)."""
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return False
        return self._get_weather_source_enabled_value(source_id, settings_manager)
    
    def get_weather_source_api_key(self, source_id: str) -> str:
        """Get the API key for a specific weather source."""
        # Dynamically find the API key setting for this source
        api_key_setting_name = f"{source_id.upper()}_API_KEY"
        
        try:
            setting_enum = getattr(WeatherSetting, api_key_setting_name)
        except AttributeError:
            logger.debug(f'No API key setting for weather source: {source_id}')
            return ''
            
        value = self.settings_manager().get_setting_value(setting_enum)
        return str(value) if value is not None else ''
    
    def get_enabled_weather_sources(self) -> List[str]:
        """Get list of enabled weather source IDs."""
        enabled_sources = []
        
        # Dynamically discover all weather sources and check if they're enabled
        from .weather_source_discovery import WeatherSourceDiscovery
        discovered_sources = WeatherSourceDiscovery.discover_weather_data_source_instances()
        
        for source in discovered_sources:
            if self.is_weather_source_enabled(source.id):
                enabled_sources.append(source.id)
                
        return enabled_sources
    
    def get_default_polling_interval_minutes(self) -> int:
        """Get the default polling interval in minutes."""
        value = self.settings_manager().get_setting_value(WeatherSetting.DEFAULT_POLLING_INTERVAL_MINUTES)
        try:
            return int(value) if value is not None else 10
        except (ValueError, TypeError):
            logger.warning(f'Invalid polling interval value: {value}, using default 10 minutes')
            return 10
    
    def is_weather_cache_enabled(self) -> bool:
        """Check if weather data caching is enabled."""
        value = self.settings_manager().get_setting_value(WeatherSetting.WEATHER_CACHE_ENABLED)
        if value is None:
            return True
        # Handle string boolean values from database
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def _get_weather_alerts_enabled_value(self, settings_manager):
        """Private helper to get weather alerts enabled value with any settings manager."""
        value = settings_manager.get_setting_value(WeatherSetting.WEATHER_ALERTS_ENABLED)
        if value is None:
            return True
        # Handle string boolean values from database
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def is_weather_alerts_enabled(self) -> bool:
        """Check if weather alerts processing is enabled."""
        return self._get_weather_alerts_enabled_value(self.settings_manager())

    async def is_weather_alerts_enabled_async(self) -> bool:
        """Check if weather alerts processing is enabled (async version)."""
        settings_manager = await self.settings_manager_async()
        if not settings_manager:
            return True
        return self._get_weather_alerts_enabled_value(settings_manager)
    
    def get_weather_source_config(self, source_id: str) -> Dict[str, any]:
        """Get complete configuration for a weather source."""
        return {
            'enabled': self.is_weather_source_enabled(source_id),
            'api_key': self.get_weather_source_api_key(source_id),
            'polling_interval_minutes': self.get_default_polling_interval_minutes(),
            'cache_enabled': self.is_weather_cache_enabled(),
        }
    
