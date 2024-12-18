from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.apps.attribute.value_ranges import PredefinedValueRanges

from .audio_file import AudioFile
from .enums import Theme

Label = 'Console'


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
    CONSOLE_LOCK_PASSWORD = SettingDefinition(
        label = 'Lock Password',
        description = 'Password to use to unlock console',
        value_type = AttributeValueType.SECRET,
        value_range_str = '',
        is_editable = True,
        is_required = False,
        initial_value = '',
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
    CONSOLE_INFO_AUDIO_FILE = SettingDefinition(
        label = 'Info Alert Sound',
        description = 'The sound to play when an INFO level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.INFO,
    )
    CONSOLE_WARNING_AUDIO_FILE = SettingDefinition(
        label = 'Warning Alert Sound',
        description = 'The sound to play when an WARNING level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.WARNING,
    )
    CONSOLE_CRITICAL_AUDIO_FILE = SettingDefinition(
        label = 'Critical Alert Sound',
        description = 'The sound to play when an CRITICAL level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.CRITICAL,
    )
    
