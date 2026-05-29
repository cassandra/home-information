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
        source_key_prefix = source.id.upper().replace( '-', '_' )

        enabled_key = f"{source_key_prefix}_ENABLED"
        settings_dict[enabled_key] = SettingDefinition(
            label=f'Enable {source.label}',
            description=f'Enable the {source.label} weather data source.',
            value_type=AttributeValueType.BOOLEAN,
            value_range=None,
            is_editable=True,
            is_required=True,
            initial_value=source.get_default_enabled_state(),
        )

        # Create base URL setting for each source so the upstream API
        # endpoint is configurable (point at a simulator, a mirror,
        # etc.). Default is the source's canonical URL.
        base_url_key = f"{source_key_prefix}_BASE_URL"
        canonical_base_url = getattr( source, 'BASE_URL', '' )
        settings_dict[base_url_key] = SettingDefinition(
            label=f'{source.label} Base URL',
            description=(
                f'Base URL for {source.label} HTTP requests. '
                f'Usually: {canonical_base_url}'
            ),
            value_type=AttributeValueType.TEXT,
            value_range=None,
            is_editable=True,
            is_required=False,
            initial_value=canonical_base_url,
        )

        if source.requires_api_key():
            api_key_key = f"{source_key_prefix}_API_KEY"
            settings_dict[api_key_key] = SettingDefinition(
                label=f'{source.label} API Key',
                description=f'API key for {source.label} weather service (required if is enabled).',
                value_type=AttributeValueType.SECRET,
                value_range=None,
                is_editable=True,
                is_required=False,
                initial_value='',
            )

    settings_dict['DEFAULT_POLLING_INTERVAL_SECONDS'] = SettingDefinition(
        label='Minimum Polling Interval (seconds)',
        description=(
            'Minimum time between weather data updates. Some weather '
            'services may update less frequently to honor their own '
            'API rate limits.'
        ),
        value_type=AttributeValueType.INTEGER,
        value_range=[ 5, 86400 ],
        is_editable=True,
        is_required=True,
        initial_value=600,
    )

    settings_dict['STARTUP_WARMUP_SECONDS'] = SettingDefinition(
        label='Startup Warmup (Seconds)',
        description=(
            'Delay before the weather monitor issues its first API '
            'calls after server startup. Guards against accidental '
            'rate-limit hits during restart loops. 0 disables warmup.'
        ),
        value_type=AttributeValueType.INTEGER,
        value_range=[ 0, 300 ],
        is_editable=True,
        is_required=True,
        initial_value=30,
    )

    settings_dict['WEATHER_CACHE_ENABLED'] = SettingDefinition(
        label='Enable Weather Data Caching',
        description='Enable caching of weather data to reduce API calls and improve performance.',
        value_type=AttributeValueType.BOOLEAN,
        value_range=None,
        is_editable=True,
        is_required=True,
        initial_value=True,
    )

    settings_dict['WEATHER_ALERTS_ENABLED'] = SettingDefinition(
        label='Enable Weather Alerts',
        description='Enable processing of weather alerts from data sources and creation of system alarms.',
        value_type=AttributeValueType.BOOLEAN,
        value_range=None,
        is_editable=True,
        is_required=True,
        initial_value=True,
    )
    
    return settings_dict


_dynamic_settings = _create_dynamic_weather_settings()
WeatherSetting = SettingEnum('WeatherSetting', _dynamic_settings)
