from typing import Set

from hi.apps.common.enums import LabeledEnum


class EntityType(LabeledEnum):
    """ 
    - This helps define the default visual appearance.
    - No assumptions are made about what sensors or controllers are associated with a given EntityType.
    - SVG file is needed for each of these, else will use a default.
    - SVG filename is by convention:  
    """

    ACCESS_POINT         = ( 'Access Point', '' )
    ANTENNA              = ( 'Antenna', '' )
    APPLIANCE            = ( 'Appliance', '' )
    AREA                 = ( 'Area', '' )
    ATTIC_STAIRS         = ( 'Attic Stairs', '' )
    AUTOMOBILE           = ( 'Automobile', '' )
    AV_RECEIVER          = ( 'A/V Receiver', '' )  # Controls Speakers/TV
    BAROMETER            = ( 'Barometer', '' )
    CAMERA               = ( 'Camera', '' )
    CEILING_FAN          = ( 'Ceiling Fan', '' )
    CLOTHES_DRYER        = ( 'Clothes Dryer', '' )
    CLOTHES_WASHER       = ( 'Clothes Washer', '' )
    COMPUTER             = ( 'Computer', '' )
    CONSUMABLE           = ( 'Consumable', '' )
    CONTROLLER           = ( 'Controller', '' )
    CONTROL_WIRE         = ( 'Control Wire', '' )
    COOKTOP              = ( 'Cooktop', '' )
    DISHWASHER           = ( 'Dishwasher', '' )
    DISK                 = ( 'Disk', '' )
    DOOR                 = ( 'Door', '' )    
    DOOR_LOCK            = ( 'Door Lock', '' )  # Controls doors
    ELECTRICAL_OUTLET    = ( 'Electrical Outlet', '' )
    ELECTRICITY_METER    = ( 'Electricity Meter', '' )
    ELECTRIC_PANEL       = ( 'Electric Panel', '' )
    ELECTRIC_WIRE        = ( 'Electric Wire', '' )
    EXHAUST_FAN          = ( 'Exhaust Fan', '' )
    FENCE                = ( 'Fence', '' )
    FIREPLACE            = ( 'Fireplace', '' )
    FURNITURE            = ( 'Furniture', '' )
    GREENHOUSE           = ( 'Greenhouse', '' )
    HEALTHCHECK          = ( 'Healthcheck', '' )
    HUMIDIFIER           = ( 'Humidifier', '' )  # Controls area
    HVAC_AIR_HANDLER     = ( 'HVAC Air Handler', '' )  # Controls area
    HVAC_CONDENSER       = ( 'HVAC Condenser', '' )  # Controls area
    HVAC_FURNACE         = ( 'HVAC Furnace', '' )  # Controls area
    HVAC_MINI_SPLIT      = ( 'HVAC Mini-split', '' )  # Controls area
    HYGROMETER           = ( 'Hygrometer', '' )
    LIGHT                = ( 'Light', '' )
    LIGHT_SENSOR         = ( 'Light Sensor', '' )
    MICROWAVE_OVEN       = ( 'Microwave Oven', '' )
    MODEM                = ( 'Modem', '' )
    MOTION_SENSOR        = ( 'Motion Sensor', '' )
    MOTOR                = ( 'Motor', '' )
    NETWORK_SWITCH       = ( 'Network Switch', '' )
    ON_OFF_SWITCH        = ( 'On/Off Switch', '' )
    OPEN_CLOSE_SENSOR    = ( 'Open/Close Sensor', '' )
    OTHER                = ( 'Other', '' )  # Will use generic visual element
    OVEN                 = ( 'Oven', '' )
    PIPE                 = ( 'Pipe', '' )
    PLANT                = ( 'Plant', '' )
    POOL_FILTER          = ( 'Pool Filter', '' )
    PRESENCE_SENSOR      = ( 'Presence Sensor', '' )
    PRINTER              = ( 'Printer', '' )
    PUMP                 = ( 'Pump', '' )
    REFRIGERATOR         = ( 'Refrigerator', '' )
    SATELLITE_DISH       = ( 'Satellite Dish'  , '' )
    SERVER               = ( 'Server'  , '' )
    SERVICE              = ( 'Service'   , '' )
    SEWER_LINE           = ( 'Sewer Line', '' )
    SHOWER               = ( 'Shower', '' ) 
    SHED                 = ( 'Shed', '' ) 
    SINK                 = ( 'Sink', '' ) 
    SKYLIGHT             = ( 'Skylight', '' ) 
    SPEAKER              = ( 'Speaker', '' )
    SPEAKER_WIRE         = ( 'Speaker Wire', '' )
    SPRINKLER_HEAD       = ( 'Sprinkler Head', '' )
    SPRINKLER_VALVE      = ( 'Sprinkler Valve', '' )  # Controls sprinkler heads
    SPRINKLER_WIRE       = ( 'Sprinkler Wire', '' )
    TELECOM_BOX          = ( 'Telecom Box', '' )
    TELECOM_WIRE         = ( 'Telecom Wire', '' )
    TELEVISION           = ( 'Television', '' )
    THERMOMETER          = ( 'Thermometer', '' )
    THERMOSTAT           = ( 'Thermostat', '' )
    TIME_SOURCE          = ( 'Time Source', '' )
    TOILET               = ( 'Toilet', '' ) 
    TOOL                 = ( 'Tool', '' )
    TREE                 = ( 'Tree', '' )
    WALL                 = ( 'Wall', '' )
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
    LIGHT_DIMMER     = ( 'Light Dimmer'     , 'Controllable light brightness (0-100%)' )
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

    @property
    def suppress_display_name(self):
        return bool( self in { EntityStateType.VIDEO_STREAM })

    @property
    def suppress_history(self):
        return bool( self in { EntityStateType.VIDEO_STREAM })
    

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


class EntityPairingType(LabeledEnum):

    PRINCIPAL  = ( 'Principal', '' )
    DELEGATE   = ( 'Delegate', '' )
    

class EntityGroupType(LabeledEnum):

    APPLIANCES = ( 'Appliances', '', {
        EntityType.APPLIANCE,
        EntityType.CLOTHES_DRYER,
        EntityType.CLOTHES_WASHER,
        EntityType.COOKTOP,
        EntityType.DISHWASHER,
        EntityType.MICROWAVE_OVEN,
        EntityType.OVEN,
        EntityType.REFRIGERATOR,
        EntityType.WATER_HEATER,
    })
    AREAS = ( 'Areas', '', {
        EntityType.AREA,
    })
    AUDIO_VISUAL = ( 'Audio/Visual', '', {
        EntityType.AV_RECEIVER,
        EntityType.SPEAKER,
        EntityType.SPEAKER_WIRE,
        EntityType.TELEVISION,
    })
    AUTO = ( 'Auto', '', {
        EntityType.AUTOMOBILE,
    })
    CLIMATE = ( 'Climate', '', {
        EntityType.BAROMETER,
        EntityType.CONTROL_WIRE,
        EntityType.EXHAUST_FAN,
        EntityType.HUMIDIFIER,
        EntityType.HVAC_AIR_HANDLER,
        EntityType.HVAC_CONDENSER,
        EntityType.HVAC_FURNACE,
        EntityType.HVAC_MINI_SPLIT,
        EntityType.HYGROMETER,
        EntityType.THERMOMETER,
        EntityType.THERMOSTAT,
    })
    COMPUTER_NETWORK = ( 'Computer/Network', '', {
        EntityType.ACCESS_POINT,
        EntityType.COMPUTER,
        EntityType.DISK,
        EntityType.HEALTHCHECK,
        EntityType.MODEM,
        EntityType.NETWORK_SWITCH,
        EntityType.PRINTER,
        EntityType.SERVER,
        EntityType.SERVICE,
    })
    CONSUMABLES = ( 'Consumable', '', {
        EntityType.CONSUMABLE,
    })
    FIXTURES = ( 'Fixtures', '', {
        EntityType.ATTIC_STAIRS,
        EntityType.CEILING_FAN,
        EntityType.FURNITURE,
        EntityType.SHOWER,
        EntityType.SINK,
        EntityType.TOILET,
    })
    LIGHTS_SWITCHES = ( 'Lights, Switches, Outlets', '', {
        EntityType.ELECTRICAL_OUTLET,
        EntityType.LIGHT,
        EntityType.ON_OFF_SWITCH,
        EntityType.WALL_SWITCH,
    })
    OTHER = ( 'Other', '', {
        EntityType.OTHER,
    })
    OUTDOORS = ( 'Outdoors', '', {
        EntityType.FENCE,
        EntityType.CONTROLLER,
        EntityType.GREENHOUSE,
        EntityType.MOTOR,
        EntityType.PIPE,
        EntityType.PLANT,
        EntityType.POOL_FILTER,
        EntityType.PUMP,
        EntityType.SHED,
        EntityType.SPRINKLER_HEAD,
        EntityType.SPRINKLER_VALVE,
        EntityType.SPRINKLER_WIRE,
        EntityType.TREE,
    })
    SECURITY = ( 'Security', '', {
        EntityType.CAMERA,
        EntityType.DOOR_LOCK,
        EntityType.LIGHT_SENSOR,
        EntityType.MOTION_SENSOR,
        EntityType.OPEN_CLOSE_SENSOR,
        EntityType.PRESENCE_SENSOR,
    })
    STRUCTURAL = ( 'Structural', '', {
        EntityType.DOOR,
        EntityType.FIREPLACE,
        EntityType.SKYLIGHT,
        EntityType.WINDOW,
        EntityType.WALL,
    })
    TIME_WEATHER = ( 'Time/Weather', '', {
        EntityType.TIME_SOURCE,
        EntityType.WEATHER_STATION,
    })
    TOOLS = ( 'Tools', '', {
        EntityType.TOOL,
    })
    UTILITIES = ( 'Utilities', '', {
        EntityType.ANTENNA,
        EntityType.ELECTRICITY_METER,
        EntityType.ELECTRIC_PANEL,
        EntityType.ELECTRIC_WIRE,
        EntityType.SATELLITE_DISH,
        EntityType.SEWER_LINE,
        EntityType.TELECOM_BOX,
        EntityType.TELECOM_WIRE,
        EntityType.WATER_LINE,
        EntityType.WATER_METER,
        EntityType.WATER_SHUTOFF_VALVE,
    })
    
    def __init__( self,
                  label             : str,
                  description       : str,
                  entity_type_set  : Set[ EntityType ] ):
        super().__init__( label, description )
        self.entity_type_set = entity_type_set
        return

    @classmethod
    def default(cls):
        return cls.OTHER
 
    @classmethod
    def from_entity_type( cls, entity_type : EntityType ):
        for entity_group_type in cls:
            if entity_type in entity_group_type.entity_type_set:
                return entity_group_type
            continue
        return cls.default()
    
