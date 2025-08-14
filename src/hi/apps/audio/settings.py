from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.apps.attribute.value_ranges import PredefinedValueRanges

from .audio_file import AudioFile

Label = 'Audio'


class AudioSetting(SettingEnum):
    """
    Audio settings for alert notifications.
    
    Provides separate sound configuration for event alerts vs weather alerts
    at each alarm level (INFO, WARNING, CRITICAL).
    """
    
    # General Event Alert Level Sound Settings
    EVENT_INFO_AUDIO_FILE = SettingDefinition(
        label = 'Event Info Alert Sound',
        description = 'The sound to play when an event INFO level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.INFO,
    )
    EVENT_WARNING_AUDIO_FILE = SettingDefinition(
        label = 'Event Warning Alert Sound',
        description = 'The sound to play when an event WARNING level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.WARNING,
    )
    EVENT_CRITICAL_AUDIO_FILE = SettingDefinition(
        label = 'Event Critical Alert Sound',
        description = 'The sound to play when an event CRITICAL level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.CRITICAL,
    )
    
    # Weather Alert Sound Settings
    WEATHER_INFO_AUDIO_FILE = SettingDefinition(
        label = 'Weather Info Alert Sound',
        description = 'The sound to play when a weather INFO level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.CHIME,
    )
    WEATHER_WARNING_AUDIO_FILE = SettingDefinition(
        label = 'Weather Warning Alert Sound',
        description = 'The sound to play when a weather WARNING level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.WEATHER_ALERT,
    )
    WEATHER_CRITICAL_AUDIO_FILE = SettingDefinition(
        label = 'Weather Critical Alert Sound',
        description = 'The sound to play when a weather CRITICAL level alert arrives.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.WEATHER_ALERT,
    )
    
    # Special Weather Event Audio Settings
    WEATHER_TORNADO_AUDIO_FILE = SettingDefinition(
        label = 'Tornado Alert Sound',
        description = 'The sound to play when a tornado alert arrives (any level).',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.TORNADO_SIREN,
    )
    
    # Console System Status Audio Settings
    CONSOLE_WARNING_AUDIO_FILE = SettingDefinition(
        label = 'Console Warning Sound',
        description = 'The sound to play when server connection is lost.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.BUZZER,
    )
    CONSOLE_INFO_AUDIO_FILE = SettingDefinition(
        label = 'Console Info Sound',
        description = 'The sound to play when server connection is restored.',
        value_type = AttributeValueType.ENUM,
        value_range_str = PredefinedValueRanges.AUDIO_FILE_CHOICES_ID,
        is_editable = True,
        is_required = False,
        initial_value = AudioFile.STORE_DOOR_CHIME,
    )
