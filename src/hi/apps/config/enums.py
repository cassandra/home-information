import json

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum
from hi.apps.config.audio_file import AudioFile
from hi.apps.security.enums import SecurityState


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
    ALERTS_DAY_START = (
        'Security Day Start',
        'Determines what time of day to switch to the "Day" security posture.',
        SubsystemType.ALERTS,
        AttributeValueType.ENUM,
        'hi.datetime.time-of-day',
        True,
        True,
        '08:00',
    )
    ALERTS_NIGHT_START = (
        'Security Night Start',
        'Determines what time of day to switch to the "Night" security posture.',
        SubsystemType.ALERTS,
        AttributeValueType.ENUM,
        'hi.datetime.time-of-day',
        True,
        True,
        '23:00',
    )
    ALERTS_AWAY_DELAY_MINS = (
        'Away Delay Time (mins)',
        'Amount of time to ignore alerts when switching to "Away" security posture.',
        SubsystemType.ALERTS,
        AttributeValueType.INTEGER,
        '',
        True,
        True,
        '5',
    )
    ALERTS_SNOOZE_DELAY_MINS = (
        'Snooze Delay Time (mins)',
        'Amount of time to ignore alerts when "Snooze" option is chosen.',
        SubsystemType.ALERTS,
        AttributeValueType.INTEGER,
        '',
        True,
        True,
        '5',
    )
    ALERTS_STARTUP_SECURITY_STATE = (
        'Startup Security State',
        'Security state to enter when system starts.',
        SubsystemType.ALERTS,
        AttributeValueType.ENUM,
        'hi.security.state',
        True,
        True,
        SecurityState.default_value(),
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
