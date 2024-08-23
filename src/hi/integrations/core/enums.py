from hi.apps.common.enums import LabeledEnum


class PropertyValueType(LabeledEnum):

    STRING  = ('String', '' )
    INTEGER = ('Integer', '' )
    FLOAT   = ('Float', '' )
    

class IntegrationType(LabeledEnum):

    ZONEMINDER        = ( 'ZoneMinder', 'ZoneMinder camera streaming and motion detection.' )
    INSTEON_HASS      = ( 'Insteon (hass)', 'Insteon devices via Home Assistant API and its integration' )
    INSTEON_SERIAL    = ( 'Insteon (serial)', 'Insteon devices via modem on serial port.' )
    
