from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum
from hi.apps.common.utils import get_absolute_static_path


class ConfigPageType(LabeledEnum):
    """
    Defines those features that appear on the main config (admin) home
    page and links to their content.  Each tab in the config pane will
    have an enum entry.
    """
    
    def __init__( self,
                  label        : str,
                  description  : str,
                  url_name     : str ):
        super().__init__( label, description )
        self.url_name = url_name
        return

    SETTINGS      = ('Settings'     , ''   , 'config_settings' )
    EVENTS        = ('Events'       , ''   , 'event_definitions' )
    INTEGRATIONS  = ('Integrations' , ''   , 'integrations_home' )

    def default(self):
        return ConfigPageType.SETTINGS


class AudioFile(LabeledEnum):
    # Predefined sounds in statically served files.

    BICYCLE_BELL       = ( 'Bicycle Bell'      , '' , 'bicycle-bell.wav' )
    BOING_SPRING       = ( 'Boing Spring'      , '' , 'boing-spring.wav' )
    BUZZER             = ( 'Buzzer'            , '' , 'buzzer.wav' )
    CHIME              = ( 'Chime'             , '' , 'chime.wav' )
    CRITICAL           = ( 'Critical'          , '' , 'critical.wav' )
    FINAL_REVEAL_BELL  = ( 'Final Reveal Bell' , '' , 'final-reveal-bell.wav' )
    INDUSTRIAL_ALARM   = ( 'Industrial Alarm'  , '' , 'industrial-alarm.wav' )
    INFO               = ( 'Info'              , '' , 'info.wav' )
    STORE_DOOR_CHIME   = ( 'Store Door Chime'  , '' , 'store-door-chime.wav' )
    TORNADO_SIREN      = ( 'Tornado Siren'     , '' , 'tornado-siren.wav' )
    WARNING            = ( 'Warning'           , '' , 'warning.wav' )
    WEATHER_ALERT      = ( 'Weather Alert'     , '' , 'weather-alert.wav' )

    @property
    def url(self):
        return get_absolute_static_path( f'audio/{self.base_filename}' )
    
    def __init__( self,
                  label             : str,
                  description       : str,
                  base_filename     : str ):
        super().__init__( label, description )
        self.base_filename = base_filename
        return

    
class SubsystemType(LabeledEnum):

    LOCALE     = ('Locale'     , '' )
    DISPLAY    = ('Display'    , '' )
    ALERTS     = ('Alerts'     , '' )

    
class Theme(LabeledEnum):

    DEFAULT  = ( 'Default', '' )
    

class SubsystemAttributeType(LabeledEnum):

    TIMEZONE = (
        'Timezone',
        'Timezone to use for display',
        SubsystemType.LOCALE,
        AttributeValueType.ENUM,
        'hi.timezone',
        True,
        True,
        'America/Chicago',
    )
    THEME = (
        'Theme',
        'Overall look and feel of interfaces',
        SubsystemType.DISPLAY,
        AttributeValueType.ENUM,
        'hi.theme',
        True,
        True,
        str( Theme.default() ),
    )
    AWAY_ALERT_EMAILS_ENABLED = (
        'Send Email When Away',
        'Whether to send emails for critical alerts to when away.',
        SubsystemType.ALERTS,
        AttributeValueType.BOOLEAN,
        '',
        True,
        False,
        False,
    )
    AWAY_ALERT_EMAILS = (
        'Away Alert Addresses',
        'Email addresses to send critical alerts to when away.',
        SubsystemType.ALERTS,
        AttributeValueType.TEXT,
        '',
        True,
        False,
        '',
    )
    INFO_AUDIO_FILE = (
        'Info Alert Sound',
        'The sound to play when an INFO level alert arrives.',
        SubsystemType.ALERTS,
        AttributeValueType.ENUM,
        'hi.audio.file',
        True,
        False,
        AudioFile.INFO,
    )
    WARNING_AUDIO_FILE = (
        'Warning Alert Sound',
        'The sound to play when an WARNING level alert arrives.',
        SubsystemType.ALERTS,
        AttributeValueType.ENUM,
        'hi.audio.file',
        True,
        False,
        AudioFile.WARNING,
    )
    CRITICAL_AUDIO_FILE = (
        'Critical Alert Sound',
        'The sound to play when an CRITICAL level alert arrives.',
        SubsystemType.ALERTS,
        AttributeValueType.ENUM,
        'hi.audio.file',
        True,
        False,
        AudioFile.CRITICAL,
    )
    
    def __init__( self,
                  label             : str,
                  description       : str,
                  subsystem_type    : SubsystemType,
                  value_type        : AttributeValueType,
                  value_range_str   : str,
                  is_editable       : bool,
                  is_required       : bool,
                  initial_value     : str ):
        super().__init__( label, description )
        self.subsystem_type = subsystem_type
        self.value_type = value_type
        self.value_range_str = value_range_str
        self.is_editable = is_editable
        self.is_required = is_required
        self.initial_value = initial_value
        return

    
class AudioSignal(LabeledEnum):

    INFO      = ( 'Info'     , '', SubsystemAttributeType.INFO_AUDIO_FILE )
    WARNING   = ( 'Warning'  , '', SubsystemAttributeType.WARNING_AUDIO_FILE)
    CRITICAL  = ( 'Critical' , '', SubsystemAttributeType.CRITICAL_AUDIO_FILE )
    
    def __init__( self,
                  label                     : str,
                  description               : str,
                  subsystem_attribute_type  : str ):
        super().__init__( label, description )
        self.subsystem_attribute_type = subsystem_attribute_type
        return
