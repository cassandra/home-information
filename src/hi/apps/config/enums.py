from hi.apps.attribute.enums import AttributeValueType
from hi.apps.common.enums import LabeledEnum


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
    DISPLAY    = ('Display'     , '' )

    
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
