from hi.apps.common.enums import LabeledEnum


class SimStateType(LabeledEnum):

    # General types
    DISCRETE         = ( 'Discrete'         , 'Single value, fixed set of possible values' )
    CONTINUOUS       = ( 'Continuous'       , 'For single value with a float type value' )

    # Specific types
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
    
    @classmethod
    def default(cls):
        return cls.DISCRETE
    
    def template_name(self):
        """
        Template used to render the simulator control for this state. Create the
        template at the given location to define a state-specific rendering, else
        it will fallback to the default template of
        "simulator/panes/sim_control_default.html"
        """
        return f'simulator/panes/sim_control_{self.name.lower()}.html'

    
class SimEntityType(LabeledEnum):

    AIR_CONDITIONER      = ( 'Air Conditioner', '' )
    APPLIANCE            = ( 'Appliance', '' )
    AREA                 = ( 'Area', '' )
    AUDIO_AMPLIFIER      = ( 'Audio Amplifier', '' )
    AUDIO_PLAYER         = ( 'Audio Player', '' )
    AUTOMOBILE           = ( 'Automobile', '' )
    BAROMETER            = ( 'Barometer', '' )
    CAMERA               = ( 'Camera', '' )
    COMPUTER             = ( 'Computer', '' )
    CONSUMABLE           = ( 'Consumable', '' )
    CONTROL_WIRE         = ( 'Control Wire', '' )
    DISPLAY              = ( 'Display', '' )
    DOOR                 = ( 'Door', '' )
    DOOR_LOCK            = ( 'Door Lock', '' )  # Controls doors
    ELECTRICAL_OUTLET    = ( 'Electrical Outlet', '' )
    ELECTRICY_METER      = ( 'Electric Meter', '' )
    ELECTRIC_PANEL       = ( 'Electric Panel', '' )
    ELECTRIC_WIRE        = ( 'Electric Wire', '' )
    FURNITURE            = ( 'Furniture', '' )
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
    NETWORK_SWITCH       = ( 'Network Switch', '' )
    OPEN_CLOSE_SENSOR    = ( 'Open/Close Sensor', '' )
    OTHER                = ( 'Other', '' )  # Will use generic visual element
    PRESENCE_SENSOR      = ( 'Presence Sensor', '' )
    SEWER_LINE           = ( 'Sewer Wire', '' )
    SHOWER               = ( 'Shower', '' ) 
    SINK                 = ( 'Sink', '' ) 
    SERVICE              = ( 'Service'         , '' )
    SPEAKER              = ( 'Speaker', '' )
    SPINKLER_CONTROLLER  = ( 'Spinkler Controller', '' )
    SPINKLER_VALVE       = ( 'Spinkler Valve', '' )  # Controls sprinkler heads
    SPRINKLER_HEAD       = ( 'Sprinkler Head', '' )
    SPRINKLER_WIRE       = ( 'Sprinkler Wire', '' )
    TELECOM_BOX          = ( 'Telecom Box', '' )
    TELECOM_WIRE         = ( 'Telecom Wire', '' )
    THERMOMETER          = ( 'Thermometer', '' )
    THERMOSTAT           = ( 'Thermostat', '' )
    TIME_SOURCE          = ( 'Time Source', '' )
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
    WINDOW               = ( 'Window', '' )
    
    @classmethod
    def default(cls):
        return cls.OTHER
