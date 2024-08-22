from hi.apps.common.enums import LabeledEnum


class EntityType(LabeledEnum):
    """ 
    - SVG File needed for each of these, else uses default.
    - SVG filename is by convention: templates/entity/svg/type.{name.lower()}.svg 
    """
    
    AIR_CONDITIONER      = ( 'Air Conditioner', '' )  # Controls area
    APPLIANCE            = ( 'Appliance', '' )
    AREA                 = ( 'Area', '' )
    AUDIO_AMPLIFIER      = ( 'Audio Amplifier', '' )  # Controls Speaker
    AUDIO_PLAYER         = ( 'Audio Player', '' )
    BAROMETER            = ( 'Barometer', '' )
    CAMERA               = ( 'Camera', '' )
    COMPUTER             = ( 'Computer', '' )
    CONTROL_WIRE         = ( 'Control Wire', '' )
    DISPLAY              = ( 'Display', '' )
    DOOR                 = ( 'Door', '' )
    DOOR_LOCK            = ( 'Door Lock', '' )  # Controls doors
    ELECTRICAL_OUTLET    = ( 'Electrical Outlet', '' )
    ELECTRICY_METER      = ( 'Electric Meter', '' )
    ELECTRIC_PANEL       = ( 'Electric Panel', '' )
    ELECTRIC_WIRE        = ( 'Electric Wire', '' )
    HEATER               = ( 'Heater', '' )  # Controls area
    HVAC_AIR_HANDLER     = ( 'HVAC Air Handler', '' )  # Controls area
    HVAC_CONDENSER       = ( 'HVAC Condenser', '' )  # Controls area
    HVAC_MIN_SPLIT       = ( 'HVAC Mini-split', '' )  # Controls area
    HUMIDIFIER           = ( 'Humidifier', '' )  # Controls area
    HYGROMETER           = ( 'Hygrometer', '' )
    LIGHT                = ( 'Light', '' )
    LIGHT_SENSOR         = ( 'Light Sensor', '' )
    MOTION_SENSOR        = ( 'Motion Sensor', '' )
    OPEN_CLOSE_DETECTOR  = ( 'Open/Close Sensor', '' )
    OTHER                = ( 'Other', '' )
    PRESENCE_SENSOR      = ( 'Presence Sensor', '' )
    SEWER_LINE           = ( 'Sewer Wire', '' )
    SHOWER               = ( 'Shower', '' ) 
    SINK                 = ( 'Sink', '' ) 
    SPEAKER              = ( 'Speaker', '' )
    SPINKLER_CONTROLLER  = ( 'Spinkler Controller', '' )
    SPINKLER_VALVE       = ( 'Spinkler Valve', '' )  # Controls sprinkler heads
    SPRINKLER_HEAD       = ( 'Sprinkler Head', '' )
    TELECOM_BOX          = ( 'Telecom Box', '' )
    TELECOM_WIRE         = ( 'Telecom Wire', '' )
    THERMOMETER          = ( 'Thermometer', '' )
    THERMOSTAT           = ( 'Thermostat', '' )
    TOILET               = ( 'Toilet', '' ) 
    TOOL                 = ( 'Tool', '' )
    VIDEO_PLAYER         = ( 'Video Player', '' )
    WALL_SWITCH          = ( 'Wall Switch', '' )
    WASTE_PIPE           = ( 'Waste Pipe', '' ) 
    WATER_HEATER         = ( 'Water Heater', '' )
    WATER_LINE           = ( 'Water Line', '' )
    WATER_METER          = ( 'Water Meter', '' )
    WATER_SHUTOFF_VALVE  = ( 'Water Shutoff Valve', '' )
    WEATHER_STATION      = ( 'Weather Station', '' )
    
    @property
    def svg_icon_name(self):
        raise NotImplementedError()

    @property
    def svg_path_style(self):
        raise NotImplementedError()

    
class EntityStateType(LabeledEnum):

    # General types
    DICRETE          = ( 'Dicrete', '' )
    CONTINUOUS       = ( 'Continuous', '' )
    BLOB             = ( 'Blob', '' )

    # Specific types
    AIR_PRESSURE     = ( 'Air Pressure', '' )
    BANDWIDTH_USAGE  = ( 'Bandwidth Usage', '' )
    CONNECTION       = ( 'Connection', '' )    
    ELECTRIC_USAGE   = ( 'Electric Usage', '' )
    HUMIDITY         = ( 'Humidity', '' )
    VIDEO_STREAM     = ( 'Video Stream', '' )
    LIGHT_LEVEL      = ( 'Light Level', '' )
    MOISTURE         = ( 'Moisture', '' )
    MOVEMENT         = ( 'Movement', '' )    
    NOISE_LEVEL      = ( 'Noise Level', '' )
    ON_OFF           = ( 'On/Off', '' )    
    OPEN_CLOSE       = ( 'Open/Close', '' )    
    PRESENCE         = ( 'Presence', '' )
    SOUND_LEVEL      = ( 'Sound Level', '' )
    TEMPERATURE      = ( 'Temperature', '' )
    WATER_FLOW       = ( 'Water Flow', '' )
    WIND_SPEED       = ( 'Wind Speed', '' )
        

class AttributeType(LabeledEnum):

    PREDEFINED  = ('Predefined', '' )
    CUSTOM = ('Custom', '' )

    
class AttributeValueType(LabeledEnum):

    STRING  = ('String', '' )
    INTEGER = ('Integer', '' )
    FLOAT   = ('Float', '' )
    TEXT    = ('Text', '' )  # relative filename in MEDIA_ROOT
    PDF     = ('PDF', '' )  # relative filename in MEDIA_ROOT
    IMAGE   = ('Image', '' )  # relative filename in MEDIA_ROOT
    VIDEO   = ('Video', '' )  # relative filename in MEDIA_ROOT
    AUDIO   = ('Audio', '' )  # relative filename in MEDIA_ROOT
    LINK    = ('Link', '' )


class AttributeName(LabeledEnum):
    # Common attribute names
    
    INTEGRATION_SOURCE = ( 'Integration Source', '' )
