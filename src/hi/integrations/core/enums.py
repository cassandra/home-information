from hi.apps.common.enums import LabeledEnum


class PropertyValueType(LabeledEnum):

    STRING  = ('String', '' )
    INTEGER = ('Integer', '' )
    FLOAT   = ('Float', '' )
    

class IntegrationType(LabeledEnum):

    ZONEMINDER        = ( 'ZoneMinder', 'ZoneMinder camera streaming and motion detection.' )
    INSTEON_HASS      = ( 'InsteonHASS', 'Insteon devices via Home Assistant API and its integration' )
    INSTEON_DIRECT    = ( 'InsteonDirect', 'Insteon devices via modem on serial port.' )
    
