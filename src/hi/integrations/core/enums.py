from hi.apps.common.enums import LabeledEnum


class PropertyValueType(LabeledEnum):

    STRING  = ('String', '' )
    INTEGER = ('Integer', '' )
    FLOAT   = ('Float', '' )
    

class IntegrationType(LabeledEnum):

    NONE              = ( 'None', 'No integration placeholder.' )
    ZONEMINDER        = ( 'ZoneMinder', 'ZoneMinder camera streaming and motion detection.' )
    HASS              = ( 'Home Assistant (hass)', 'Home Assistant device access' )
    
