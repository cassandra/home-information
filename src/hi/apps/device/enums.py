from hi.apps.common.enums import LabeledEnum


class DeviceType(LabeledEnum):

    """ 
    SVG File needed for each (by convention): templates/device/svg/{name.lower()}.svg 
    """
    
    AIR_CONDITIONER      = ( 'Air_Conditioner', '' )  # Controls area
    APPLIANCE            = ( 'Appliance', '' )
    AREA                 = ( 'Area', '' )
    AUDIO_AMPLIFIER      = ( 'Audio Amplifier', '' )  # Controls SPeaker
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
    ELECTRIC_PANEL       = ( 'Electric_Panel', '' )
    ELECTRIC_WIRE        = ( 'Electric Wire', '' )
    HEATER               = ( 'Heater', '' )  # Controls area
    HUMIDIFIER           = ( 'Humidifier', '' )  # Controls area
    HYGROMETER           = ( 'Hygrometer', '' )
    LIGHT                = ( 'Light', '' )
    LIGHT_SENSOR         = ( 'Light Sensor', '' )
    MOTION_SENSOR        = ( 'Motion Sensor', '' )
    OPEN_CLOSE_DETECTOR  = ( 'Open/Close_Sensor', '' )
    OTHER                = ( 'Other', '' )
    PRESENCE_SENSOR      = ( 'Presence Sensor', '' )
    SEWER_LINE           = ( 'Sewer Wire', '' )
    SPEAKER              = ( 'Speaker', '' )
    SPINKLER_CONTROLLER  = ( 'Spinkler Controller', '' )
    SPINKLER_VALVE       = ( 'Spinkler Valve', '' )  # Controls sprinkler heads
    SPRINKLER_HEAD       = ( 'Sprinkler Head', '' )
    TELECOM_BOX          = ( 'Telecom Box', '' )
    TELECOM_WIRE         = ( 'Telecom Wire', '' )
    THERMOMETER          = ( 'Thermometer', '' )
    THERMOSTAT           = ( 'Thermostat', '' )
    TOOL                 = ( 'Tool', '' )
    VIDEO_PLAYER         = ( 'Video Player', '' )
    WALL_SWITCH          = ( 'Wall Switch', '' )
    WATER_LINE           = ( 'Water Line', '' )
    WATER_METER          = ( 'Water_Meter', '' )
    WATER_SHUTOFF_VALVE  = ( 'Water Shutoff Valve', '' )
    WEATHER_STATION      = ( 'Weather Station', '' )
    
    @property
    def svg_icon_name(self):
        raise NotImplementedError()

    @property
    def svg_path_style(self):
        raise NotImplementedError()

    
class DeviceStateType(LabeledEnum):

    DICRETE = ( 'Dicrete', '' )
    CONTINUOUS = ( 'Continuous', '' )
    BLOB = ( 'Blob', '' )
    MOVEMENT = ( 'Movement', '' )
    
    TEMPERATURE = ( 'Temperature', '' )
    HUMIDITY = ( 'Humidity', '' )
    LIGHT_LEVEL = ( 'Light Level', '' )
    SOUND_LEVEL = ( 'Sound Level', '' )
    MOISTURE = ( 'Moisture', '' )
    WIND_SPEED = ( 'Wind Speed', '' )

    
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


class AttributeSourceType(LabeledEnum):

    PREDEFINED  = ('Predefined', '' )
    CUSTOM = ('Custom', '' )
