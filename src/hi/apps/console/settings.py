from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.apps.attribute.value_ranges import PredefinedValueRanges

from .enums import Theme, DisplayUnits

Label = 'Console'

# Austin, TX
DEFAULT_LATITUDE = 30.268043
DEFAULT_LONGITUDE = -97.742804
DEFAULT_GEO_LOCATION = f'{DEFAULT_LATITUDE:.6}, {DEFAULT_LONGITUDE:.6}'


class ConsoleSetting( SettingEnum ):

    TIMEZONE = SettingDefinition(
        label = 'Timezone',
        description = 'Timezone to use for display',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.TIMEZONE_CHOICES_ID,
        is_editable = True,
        is_required = True,
        initial_value = 'America/Chicago',
    )
    DISPLAY_UNITS = SettingDefinition(
        label = 'Display Units',
        description = 'Units used when displaying',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.UNITS_CHOICES_ID,
        is_editable = True,
        is_required = True,
        initial_value = str( DisplayUnits.default() ),
    )
    GEO_LOCATION = SettingDefinition(
        label = 'Latitude, Longitude',
        description = 'Latitude and longitude. e.g., for weather data',
        value_type = AttributeValueType.TEXT,
        value_range_str = '',
        is_editable = True,
        is_required = True,
        initial_value = DEFAULT_GEO_LOCATION,
    )
    THEME = SettingDefinition(
        label = 'Theme',
        description = 'Overall look and feel of interfaces',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.THEME_CHOICES_ID,
        is_editable = True,
        is_required = True,
        initial_value = str( Theme.default() ),
    )
    CONSOLE_LOCK_PASSWORD = SettingDefinition(
        label = 'Lock Password',
        description = 'Password to use to unlock console',
        value_type = AttributeValueType.SECRET,
        value_range_str = '',
        is_editable = True,
        is_required = False,
        initial_value = '',
    )
    SLEEP_OVERLAY_OPACITY = SettingDefinition(
        label = 'Sleep Overlay Opacity',
        description = 'Opacity to use for sleep mode: 0.0 for none to 1.0 for fully opaque.',
        value_type = AttributeValueType.FLOAT,
        value_range_str = '[ 0.0, 1.0 ]',
        is_editable = True,
        is_required = True,
        initial_value = '0.95',
    )
    AUTO_VIEW_ENABLED = SettingDefinition(
        label = 'Auto View Switching',
        description = 'Enable automatic view switching for alerts',
        value_type = AttributeValueType.BOOLEAN,
        value_range_str = '',
        is_editable = True,
        is_required = True,
        initial_value = 'true',
    )
    AUTO_VIEW_DURATION = SettingDefinition(
        label = 'Auto View Duration (seconds)',
        description = 'How long to show auto-switched view before reverting',
        value_type = AttributeValueType.INTEGER,
        value_range_str = '',
        is_editable = True,
        is_required = True,
        initial_value = '30',
    )
    
