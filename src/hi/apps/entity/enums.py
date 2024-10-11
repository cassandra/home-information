from hi.apps.common.enums import LabeledEnum


class EntityType(LabeledEnum):
    """ 
    - This helps define the default visual appearance.
    - No assumptions are made about what sensors or controllers are associated with a given EntityType.
    - SVG file is needed for each of these, else will use a default.
    - SVG filename is by convention:  
    """
    def __init__( self,
                  label           : str,
                  description     : str,
                  is_path         : bool = False,
                  is_path_closed  : bool = False ):
        super().__init__( label, description )
        self.is_path = is_path
        self.is_path_closed = is_path_closed
        return

    AIR_CONDITIONER      = ( 'Air Conditioner', '' )  # Controls area
    APPLIANCE            = ( 'Appliance', '' )
    AREA                 = ( 'Area', '', True, True )
    AUDIO_AMPLIFIER      = ( 'Audio Amplifier', '' )  # Controls Speaker
    AUDIO_PLAYER         = ( 'Audio Player', '' )
    BAROMETER            = ( 'Barometer', '' )
    CAMERA               = ( 'Camera', '' )
    COMPUTER             = ( 'Computer', '' )
    CONSUMABLE           = ( 'Consumable', '' )
    CONTROL_WIRE         = ( 'Control Wire', '', True )
    DISPLAY              = ( 'Display', '' )
    DOOR                 = ( 'Door', '' )
    DOOR_LOCK            = ( 'Door Lock', '' )  # Controls doors
    ELECTRICAL_OUTLET    = ( 'Electrical Outlet', '' )
    ELECTRICY_METER      = ( 'Electric Meter', '' )
    ELECTRIC_PANEL       = ( 'Electric Panel', '' )
    ELECTRIC_WIRE        = ( 'Electric Wire', '', True )
    HEALTHCHECK          = ( 'Healthcheck', '' )
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
    OTHER                = ( 'Other', '' )  # Will use generic visual element
    PRESENCE_SENSOR      = ( 'Presence Sensor', '' )
    SEWER_LINE           = ( 'Sewer Wire', '', True )
    SHOWER               = ( 'Shower', '' ) 
    SINK                 = ( 'Sink', '' ) 
    SPEAKER              = ( 'Speaker', '' )
    SPINKLER_CONTROLLER  = ( 'Spinkler Controller', '' )
    SPINKLER_VALVE       = ( 'Spinkler Valve', '' )  # Controls sprinkler heads
    SPRINKLER_HEAD       = ( 'Sprinkler Head', '' )
    SPRINKLER_WIRE       = ( 'Sprinkler Wire', '', True )
    TELECOM_BOX          = ( 'Telecom Box', '' )
    TELECOM_WIRE         = ( 'Telecom Wire', '', True )
    THERMOMETER          = ( 'Thermometer', '' )
    THERMOSTAT           = ( 'Thermostat', '' )
    TIME_SOURCE          = ( 'Time Source', '' )
    TOILET               = ( 'Toilet', '' ) 
    TOOL                 = ( 'Tool', '' )
    VIDEO_PLAYER         = ( 'Video Player', '' )
    WALL_SWITCH          = ( 'Wall Switch', '' )
    WASTE_PIPE           = ( 'Waste Pipe', '', True ) 
    WATER_HEATER         = ( 'Water Heater', '' )
    WATER_LINE           = ( 'Water Line', '', True )
    WATER_METER          = ( 'Water Meter', '' )
    WATER_SHUTOFF_VALVE  = ( 'Water Shutoff Valve', '' )
    WEATHER_STATION      = ( 'Weather Station', '' )
    WINDOW               = ( 'Window', '' )
    
    @classmethod
    def default(cls):
        return cls.OTHER

    @property
    def is_icon(self):
        return bool( not self.is_path )
                    
    
class EntityStateType(LabeledEnum):

    def __init__( self,
                  label             : str,
                  description       : str ):
        super().__init__( label, description )
        return
    
    # General types
    DISCRETE         = ( 'Discrete'         , 'Single value, fixed set of possible values' )
    CONTINUOUS       = ( 'Continuous'       , 'For single value with a float type value' )
    MULTVALUED       = ( 'Multi-valued'     , 'Provides multiple name-value pairs' )
    BLOB             = ( 'Blob'             , 'Provides blob of uninterpreted data' )

    # Specific types
    #
    # The general types (above) could be used for these, since all are just
    # name-value pairs. However, by being more specific, we can provide
    # more specific visual and processing for the sensors/controllers.
    
    AIR_PRESSURE     = ( 'Air Pressure'     , '' )
    BANDWIDTH_USAGE  = ( 'Bandwidth Usage'  , '' )
    CONNECTIVITY     = ( 'Connectivity'     , '' )    
    DATETIME         = ( 'Date/Time'        , '' )
    ELECTRIC_USAGE   = ( 'Electric Usage'   , '' )
    HIGH_LOW         = ( 'High/Low'         , '' )    
    HUMIDITY         = ( 'Humidity'         , '' )
    LIGHT_LEVEL      = ( 'Light Level'      , '' )
    MOISTURE         = ( 'Moisture'         , '' )
    MOVEMENT         = ( 'Movement'         , '' )    
    ON_OFF           = ( 'On/Off'           , '' )    
    OPEN_CLOSE       = ( 'Open/Close'       , '' )    
    PRESENCE         = ( 'Presence'         , '' )
    SOUND_LEVEL      = ( 'Sound Level'      , '' )
    TEMPERATURE      = ( 'Temperature'      , '' )
    VIDEO_STREAM     = ( 'Video Stream'     , '' )
    WATER_FLOW       = ( 'Water Flow'       , '' )
    WIND_SPEED       = ( 'Wind Speed'       , '' )
        

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
    
    INSTEON_ADDRESS = ( 'Insteon Address', '' )


class TemperatureUnit(LabeledEnum):

    FAHRENHEIT  = ( 'Fahrenheit', '' )
    CELSIUS     = ( 'Celsius', '' )

    
class HumidityUnit(LabeledEnum):

    PERCENT                = ( 'Percent', '' )
    GRAMS_PER_CUBIN_METER  = ( 'Grams per cubic meter (g/m³)', '' )
    GRAMS_PER_KILOGRAM     = ( 'Grams per kilogram (g/kg)', '' )
