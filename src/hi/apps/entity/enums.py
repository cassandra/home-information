from hi.apps.common.enums import LabeledEnum


class EntityType(LabeledEnum):
    """ 
    - This helps define the default visual appearance.
    - No assumptions are made about what sensors or controllers are associated with a given EntityType.
    - SVG file is needed for each of these, else will use a default.
    - SVG filename is by convention:  
    """

    AIR_CONDITIONER      = ( 'Air Conditioner', '' )  # Controls area
    APPLIANCE            = ( 'Appliance', '' )
    AREA                 = ( 'Area', '' )
    AUDIO_AMPLIFIER      = ( 'Audio Amplifier', '' )  # Controls Speaker
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
    SEWER_LINE           = ( 'Sewer Line', '' )
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
    WATER_HEATER         = ( 'Water Heater', '' )
    WATER_LINE           = ( 'Water Line', '' )
    WATER_METER          = ( 'Water Meter', '' )
    WATER_SHUTOFF_VALVE  = ( 'Water Shutoff Valve', '' )
    WEATHER_STATION      = ( 'Weather Station', '' )
    WINDOW               = ( 'Window', '' )
    
    @classmethod
    def default(cls):
        return cls.OTHER
                    
    
class EntityStateType(LabeledEnum):
    
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

    def value_template_name(self):
        """
        Template used to render a sensor's value for this state. Create the
        template at the given location to define a state-specific rendering, else
        it will fallback to the default template of
        "entity/panes/sensor_value_default.html"
        """
        return f'sense/panes/sensor_value_{self.name.lower()}.html'

    def controller_template_name(self):
        """
        Template used to render a controllers for this state. Create the
        template at the given location to define a state-specific rendering, else
        it will fallback to the default template of
        "entity/panes/controller_value_default.html"
        """
        return f'control/panes/controller_{self.name.lower()}.html'


class EntityStateValue(LabeledEnum):

    ACTIVE         = ( 'Active', '' )
    IDLE           = ( 'Idle', '' )

    ON             = ( 'On', '' )
    OFF            = ( 'Off', '' )
    
    OPEN           = ( 'Open', '' )
    CLOSED         = ( 'Closed', '' )

    CONNECTED      = ( 'Connected', '' )
    DISCONNECTED   = ( 'Disconnected', '' )

    HIGH           = ( 'High', '' )
    LOW            = ( 'Low', '' )

    @classmethod
    def entity_state_value_choices(cls):
        return {
            EntityStateType.CONNECTIVITY: [ ( str(x), x.label )
                                            for x in [ EntityStateValue.CONNECTED,
                                                       EntityStateValue.DISCONNECTED ]],
            EntityStateType.HIGH_LOW: [ ( str(x), x.label )
                                        for x in [ EntityStateValue.HIGH,
                                                   EntityStateValue.LOW ]],
            EntityStateType.MOVEMENT: [ ( str(x), x.label )
                                        for x in [ EntityStateValue.ACTIVE,
                                                   EntityStateValue.IDLE ]],
            EntityStateType.ON_OFF: [ ( str(x), x.label )
                                      for x in [ EntityStateValue.ON,
                                                 EntityStateValue.OFF ]],
            EntityStateType.OPEN_CLOSE: [ ( str(x), x.label )
                                          for x in [ EntityStateValue.OPEN,
                                                     EntityStateValue.CLOSED ]],
        }

    
class TemperatureUnit(LabeledEnum):

    FAHRENHEIT  = ( 'Fahrenheit', '' )
    CELSIUS     = ( 'Celsius', '' )

    
class HumidityUnit(LabeledEnum):

    PERCENT                = ( 'Percent', '' )
    GRAMS_PER_CUBIN_METER  = ( 'Grams per cubic meter (g/m³)', '' )
    GRAMS_PER_KILOGRAM     = ( 'Grams per kilogram (g/kg)', '' )
