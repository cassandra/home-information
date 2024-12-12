from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType

from .audio_file import AudioFile
from .enums import Theme

Label = 'Console'


class ConsoleSetting( SettingEnum ):

    TIMEZONE = SettingDefinition(
        label = 'Timezone',
        description = 'Timezone to use for display',
        value_type = AttributeValueType.ENUM,
        value_range_str = 'hi.timezone',
        is_editable = True,
        is_required = True,
        initial_value = 'America/Chicago',
    )
    THEME = SettingDefinition(
        label = 'Theme',
        description = 'Overall look and feel of interfaces',
        value_type = AttributeValueType.ENUM,
        value_range_str = 'hi.theme',
        is_editable = True,
        is_required = True,
        initial_value = str( Theme.default() ),
    )
    CONSOLE_INFO_AUDIO_FILE = SettingDefinition(
        label = 'Info Alert Sound',
        description = 'The sound to play when an INFO level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = 'hi.audio.file',
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.INFO,
    )
    CONSOLE_WARNING_AUDIO_FILE = SettingDefinition(
        label = 'Warning Alert Sound',
        description = 'The sound to play when an WARNING level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = 'hi.audio.file',
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.WARNING,
    )
    CONSOLE_CRITICAL_AUDIO_FILE = SettingDefinition(
        label = 'Critical Alert Sound',
        description = 'The sound to play when an CRITICAL level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = 'hi.audio.file',
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.CRITICAL,
    )
    
