from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType

Label = 'Security'


class SecuritySetting( SettingEnum ):

    SECURITY_DAY_START = SettingDefinition(
        label = 'Security Day Start',
        description = 'Determines what time of day to switch to the "Day" security posture.',
        value_type = AttributeValueType.ENUM,
        value_range_str = 'hi.datetime.time-of-day',
        is_editable = True,
        is_required = True,
        initial_value = '08:00',
    )
    
    SECURITY_NIGHT_START = SettingDefinition(
        label = 'Security Night Start',
        description = 'Determines what time of day to switch to the "Night" security posture.',
        value_type = AttributeValueType.ENUM,
        value_range_str = 'hi.datetime.time-of-day',
        is_editable = True,
        is_required = True,
        initial_value = '23:00',
    )
    
    SECURITY_AWAY_DELAY_MINS = SettingDefinition(
        label = 'Away Delay Time (mins)',
        description = 'Amount of time to ignore alarms when switching to "Away" security posture.',
        value_type = AttributeValueType.INTEGER,
        value_range_str = '',
        is_editable = True,
        is_required = True,
        initial_value = '5',
    )
    
    SECURITY_SNOOZE_DELAY_MINS = SettingDefinition(
        label = 'Snooze Delay Time (mins)',
        description = 'Amount of time to ignore alarms when "Snooze" option is chosen.',
        value_type = AttributeValueType.INTEGER,
        value_range_str = '',
        is_editable = True,
        is_required = True,
        initial_value = '5',
    )
    
