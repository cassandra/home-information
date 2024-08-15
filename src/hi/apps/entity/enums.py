from hi.apps.common.enums import LabeledEnum


class EntityType(LabeledEnum):

    """ 
    SVG File needed for each (by convention): templates/entity/svg/{name.lower()}.svg 
    """
    
    CAMERA               = ( 'Camera', '' )
    MOTION_SENSOR        = ( 'Motion Sensor', '' )
    LIGHT_SWITCH         = ( 'Light Switch', '' )
    LIGHT                = ( 'Light', '' )
    ELECTRICAL_OUTLET    = ( 'Electrical Outlet', '' )
    CONTACT_SENSOR       = ( 'Contact Sensor', '' )
    DOOR                 = ( 'Door', '' )
    INTERNET_CONNECTION  = ( 'Internet Connection', '' )
    ELECTRIC_WIRE        = ( 'Electric Wire', '' )
    TELECOM_WIRE         = ( 'Telecom Wire', '' )
    TELECOM_BOX          = ( 'Telecom Box', '' )
    WATER_LINE           = ( 'Water Line', '' )
    SEWER_LINE           = ( 'Sewer Wire', '' )
    ELECTRIC_PANEL       = ( 'Electric_Panel', '' )
    WATER_SHUTOFF_VALVE  = ( 'Water Shutoff Valve', '' )
    WATER_METER          = ( 'Water_Meter', '' )
    DOOR_LOCK            = ( 'Door Lock', '' )
    THERMOSTAT           = ( 'Thermostat', '' )
    THERMOMETER          = ( 'Thermometer', '' )
    HYGROMETER           = ( 'Hygrometer', '' )
    BAROMETER            = ( 'Barometer', '' )
    HEATER               = ( 'Heater', '' )
    AIR_CONDITIONER      = ( 'Air_Conditioner', '' )
    HUMIDIFIER           = ( 'Humidifier', '' )
    COMPUTER             = ( 'Computer', '' )
    APPLIANCE            = ( 'Appliance', '' )
    TOOL                 = ( 'Tool', '' )
    SWITCH               = ( 'Switch', '' )
    SPINKLER_CONTROLLER  = ( 'Spinkler Controller', '' )
    SPINKLER_VALVE       = ( 'Spinkler Valve', '' )
    SPRINKLER_HEAD       = ( 'Sprinkler Head', '' )

    
class EntityAttributeType(LabeledEnum):

    STRING  = ('String', '' )
    INTEGER = ('Integer', '' )
    FLOAT   = ('Float', '' )
    TEXT    = ('Text', '' )  # relative filename in MEDIA_ROOT
    PDF     = ('PDF', '' )  # relative filename in MEDIA_ROOT
    IMAGE   = ('Image', '' )  # relative filename in MEDIA_ROOT
    VIDEO   = ('Video', '' )  # relative filename in MEDIA_ROOT
    AUDIO   = ('Audio', '' )  # relative filename in MEDIA_ROOT
    LINK    = ('Link', '' )
