from typing import Dict

from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType

Label = 'Weather'


def _create_dynamic_weather_settings() -> Dict[str, SettingDefinition]:
    """Dynamically create settings based on discovered weather sources."""
    from .weather_source_discovery import WeatherSourceDiscovery
    
    settings_dict = {}
    discovered_sources = WeatherSourceDiscovery.discover_weather_data_source_instances()
    
    for source in discovered_sources:
        # Create enabled/disabled setting for each source
        enabled_key = f"{source.id.upper()}_ENABLED"
        settings_dict[enabled_key] = SettingDefinition(
            label=f'Enable {source.label}',
            description=f'Enable the {source.label} weather data source.',
            value_type=AttributeValueType.BOOLEAN,
            value_range_str='',
            is_editable=True,
            is_required=True,
            initial_value=source.get_default_enabled_state(),
        )
        
        # Create API key setting if source requires it
        if source.requires_api_key():
            api_key_key = f"{source.id.upper()}_API_KEY"
            settings_dict[api_key_key] = SettingDefinition(
                label=f'{source.label} API Key',
                description=f'API key for {source.label} weather service (required if {source.label} is enabled).',
                value_type=AttributeValueType.SECRET,
                value_range_str='',
                is_editable=True,
                is_required=False,
                initial_value='',
            )
    
    # Add general weather settings
    settings_dict['DEFAULT_POLLING_INTERVAL_MINUTES'] = SettingDefinition(
        label='Default Polling Interval (Minutes)',
        description='Default interval in minutes for polling weather data from enabled sources.',
        value_type=AttributeValueType.INTEGER,
        value_range_str='5-1440',  # 5 minutes to 24 hours
        is_editable=True,
        is_required=True,
        initial_value=10,
    )
    
    settings_dict['WEATHER_CACHE_ENABLED'] = SettingDefinition(
        label='Enable Weather Data Caching',
        description='Enable caching of weather data to reduce API calls and improve performance.',
        value_type=AttributeValueType.BOOLEAN,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value=True,
    )
    
    settings_dict['WEATHER_ALERTS_ENABLED'] = SettingDefinition(
        label='Enable Weather Alerts',
        description='Enable processing of weather alerts from data sources and creation of system alarms.',
        value_type=AttributeValueType.BOOLEAN,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value=True,
    )
    
    return settings_dict


# Dynamically create the WeatherSetting enum
_dynamic_settings = _create_dynamic_weather_settings()
WeatherSetting = SettingEnum('WeatherSetting', _dynamic_settings)
