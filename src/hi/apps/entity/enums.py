from typing import List, Set, Tuple

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
    LARGE_APPLIANCE      = ( 'Large Appliance', '' )
    AREA                 = ( 'Area', '' )
    ATTIC_STAIRS         = ( 'Attic Stairs', '' )
    AUTOMOBILE           = ( 'Automobile', '' )
    AV_RECEIVER          = ( 'A/V Receiver', '' )  # Controls Speakers/TV
    BAROMETER            = ( 'Barometer', '' )
    BATHTUB              = ( 'Bathtub', '' )
    CAMERA               = ( 'Camera', '' )
    CARBON_MONOXIDE_DETECTOR = ( 'Carbon Monoxide Detector', '' )
    CEILING_FAN          = ( 'Ceiling Fan', '' )
    CLOTHES_DRYER        = ( 'Clothes Dryer', '' )
    CLOTHES_WASHER       = ( 'Clothes Washer', '' )
    COFFEE_MAKER         = ( 'Coffee Maker', '' )
    COMPUTER             = ( 'Computer', '' )
    CONSUMABLE           = ( 'Consumable', '' )
    CONTROLLER           = ( 'Controller', '' )
    CONTROL_WIRE         = ( 'Control Wire', '' )
    COOKTOP              = ( 'Cooktop', '' )
    DISHWASHER           = ( 'Dishwasher', '' )
    DISK                 = ( 'Disk', '' )
    DOOR                 = ( 'Door', '' )
    DOORBELL             = ( 'Doorbell', '' )
    DOOR_LOCK            = ( 'Door Lock', '' )  # Controls doors
    DRAINAGE_PIPE        = ( 'Drainage Pipe', '' )
    ELECTRICAL_OUTLET    = ( 'Electrical Outlet', '' )
    ELECTRICITY_METER    = ( 'Electricity Meter', '' )
    ELECTRIC_PANEL       = ( 'Electric Panel', '' )
    ELECTRIC_WIRE        = ( 'Electric Wire', '' )
    EXHAUST_FAN          = ( 'Exhaust Fan', '' )
    FENCE                = ( 'Fence', '' )
    FIRE_EXTINGUISHER    = ( 'Fire Extinguisher', '' )
    FIREPLACE            = ( 'Fireplace', '' )
    FURNITURE            = ( 'Furniture', '' )
    GARBAGE_DISPOSAL     = ( 'Garbage Disposal', '' )
    GENERATOR            = ( 'Generator', '' )
    GREENHOUSE           = ( 'Greenhouse', '' )
    GRILL                = ( 'Grill', '' )  # BBQ
    HEALTHCHECK          = ( 'Healthcheck', '' )
    HEDGE_TRIMMER        = ( 'Hedge Trimmer', '' )
    HUMIDIFIER           = ( 'Humidifier', '' )  # Controls area
    HVAC_AIR_HANDLER     = ( 'HVAC Air Handler', '' )  # Controls area
    HVAC_CONDENSER       = ( 'HVAC Condenser', '' )  # Controls area
    HVAC_FURNACE         = ( 'HVAC Furnace', '' )  # Controls area
    HVAC_MINI_SPLIT      = ( 'HVAC Mini-split', '' )  # Controls area
    HYGROMETER           = ( 'Hygrometer', '' )
    LAWN_MOWER           = ( 'Lawn Mower', '' )
    LEAF_BLOWER          = ( 'Leaf Blower', '' )
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
    POWER_WASHER         = ( 'Power Washer', '' )
    PRESENCE_SENSOR      = ( 'Presence Sensor', '' )
    PRINTER              = ( 'Printer', '' )
    PUMP                 = ( 'Pump', '' )
    RANGE_HOOD           = ( 'Range Hood', '' )
    REFRIGERATOR         = ( 'Refrigerator', '' )
    SATELLITE_DISH       = ( 'Satellite Dish'  , '' )
    SERVER               = ( 'Server'  , '' )
    SERVICE              = ( 'Service'   , '' )
    SEWER_LINE           = ( 'Sewer Line', '' )
    SHOWER               = ( 'Shower', '' )
    SINK                 = ( 'Sink', '' ) 
    SKYLIGHT             = ( 'Skylight', '' )
    SMOKE_DETECTOR       = ( 'Smoke Detector', '' )
    SOLAR_PANEL          = ( 'Solar Panel', '' )
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
    TRIMMER              = ( 'Trimmer', '' )
    UPS                  = ( 'UPS', '' )  # Uninterruptible Power Supply
    VANITY               = ( 'Vanity', '' )
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
    
    # Single source of truth for position vs path classification
    @classmethod
    def get_closed_path_types(cls) -> Set['EntityType']:
        """EntityTypes that require closed paths (areas/regions)"""
        return {
            cls.LARGE_APPLIANCE,
            cls.AREA,
            cls.DOOR,
            cls.FURNITURE,
            cls.GREENHOUSE,
            cls.WALL,
            cls.WINDOW,
        }
    
    @classmethod
    def get_open_path_types(cls) -> Set['EntityType']:
        """EntityTypes that require open paths (lines/routes)"""
        return {
            cls.CONTROL_WIRE,
            cls.DRAINAGE_PIPE,
            cls.ELECTRIC_WIRE,
            cls.FENCE,
            cls.PIPE,
            cls.SEWER_LINE,
            cls.SPEAKER_WIRE,
            cls.SPRINKLER_WIRE,
            cls.TELECOM_WIRE,
            cls.WATER_LINE,
        }
    
    # Convenience methods for structural decisions
    def requires_position(self) -> bool:
        """True if EntityType should be represented as EntityPosition (icon) - DEFAULT"""
        return not self.requires_path()
    
    def requires_path(self) -> bool:
        """True if EntityType should be represented as EntityPath"""
        return self in (self.get_closed_path_types() | self.get_open_path_types())
    
    def requires_closed_path(self) -> bool:
        """True if EntityType requires a closed path"""
        return self in self.get_closed_path_types()
    
    def requires_open_path(self) -> bool:
        """True if EntityType requires an open path"""
        return self in self.get_open_path_types()
                    
    
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
 
    
class EntityStateType(LabeledEnum):
    
    # General types
    DISCRETE         = ( 'Discrete'         , 'Single value, fixed set of possible values',
                         [] )
    CONTINUOUS       = ( 'Continuous'       , 'For single value with a float type value',
                         [] )
    MULTIVALUED      = ( 'Multi-valued'     , 'Provides multiple name-value pairs',
                         [] )
    BLOB             = ( 'Blob'             , 'Provides blob of uninterpreted data',
                         [] )

    # Specific types
    #
    # The general types (above) could be used for these, since all are just
    # name-value pairs. However, by being more specific, we can provide
    # more specific visual and processing for the sensors/controllers.
    
    AIR_PRESSURE     = ( 'Air Pressure'     , '',
                         [] )
    BANDWIDTH_USAGE  = ( 'Bandwidth Usage'  , '',
                         [] )
    CONNECTIVITY     = ( 'Connectivity'     , '',
                         [ EntityStateValue.CONNECTED,
                           EntityStateValue.DISCONNECTED ] )    
    DATETIME         = ( 'Date/Time'        , '',
                         [] )
    ELECTRIC_USAGE   = ( 'Electric Usage'   , '',
                         [] )
    HIGH_LOW         = ( 'High/Low'         , '',
                         [ EntityStateValue.HIGH,
                           EntityStateValue.LOW ] )    
    HUMIDITY         = ( 'Humidity'         , '',
                         [] )
    LIGHT_DIMMER     = ( 'Light Dimmer'     , 'Controllable light brightness (0-100)',
                         [] )
    LIGHT_LEVEL      = ( 'Light Level'      , '',
                         [] )
    MOISTURE         = ( 'Moisture'         , '',
                         [] )
    MOVEMENT         = ( 'Movement'         , '',
                         [ EntityStateValue.ACTIVE,
                           EntityStateValue.IDLE ] )    
    ON_OFF           = ( 'On/Off'           , '',
                         [ EntityStateValue.ON,
                           EntityStateValue.OFF ] )    
    OPEN_CLOSE       = ( 'Open/Close'       , '',
                         [ EntityStateValue.OPEN,
                           EntityStateValue.CLOSED ] )    
    PRESENCE         = ( 'Presence'         , '',
                         [ EntityStateValue.ACTIVE,
                           EntityStateValue.IDLE ] )
    SOUND_LEVEL      = ( 'Sound Level'      , '',
                         [] )
    TEMPERATURE      = ( 'Temperature'      , '',
                         [] )
    WATER_FLOW       = ( 'Water Flow'       , '',
                         [] )
    WIND_SPEED       = ( 'Wind Speed'       , '',
                         [] )
    
    def __init__( self,
                  label                    : str,
                  description              : str,
                  entity_state_value_list  : List[ EntityStateValue ] ):
        super().__init__( label, description )
        self.entity_state_value_list = entity_state_value_list
        return

    def choices(self) -> List[ Tuple[str, str] ]:
        return [ ( str(x), x.label ) for x in self.entity_state_value_list ]
    
    def toggle_values(self) -> List[str]:
        return [ str(x) for x in self.entity_state_value_list ]
                         
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
    

class VideoStreamMode(LabeledEnum):
    """Mode of video stream - whether live or recorded."""

    LIVE = ('Live', 'Live real-time video stream')
    RECORDED = ('Recorded', 'Recorded video playback')

    @classmethod
    def default(cls):
        return cls.LIVE


class VideoStreamType(LabeledEnum):
    """Types of video streams that can be provided by entities or sensor responses."""

    URL = ('URL', 'Direct video stream URL')
    OTHER = ('Other', 'Other video stream type for future extensibility')

    @classmethod
    def default(cls):
        return cls.OTHER


class EntityGroupType(LabeledEnum):

    APPLIANCES = ( 'Appliances', '', {
        EntityType.APPLIANCE,
        EntityType.LARGE_APPLIANCE,
        EntityType.CLOTHES_DRYER,
        EntityType.CLOTHES_WASHER,
        EntityType.COFFEE_MAKER,
        EntityType.COOKTOP,
        EntityType.DISHWASHER,
        EntityType.GARBAGE_DISPOSAL,
        EntityType.GRILL,
        EntityType.MICROWAVE_OVEN,
        EntityType.OVEN,
        EntityType.RANGE_HOOD,
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
        EntityType.BATHTUB,
        EntityType.CEILING_FAN,
        EntityType.FURNITURE,
        EntityType.SHOWER,
        EntityType.SINK,
        EntityType.TOILET,
        EntityType.VANITY,
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
        EntityType.HEDGE_TRIMMER,
        EntityType.LAWN_MOWER,
        EntityType.LEAF_BLOWER,
        EntityType.MOTOR,
        EntityType.PIPE,
        EntityType.PLANT,
        EntityType.POOL_FILTER,
        EntityType.POWER_WASHER,
        EntityType.PUMP,
        EntityType.SPRINKLER_HEAD,
        EntityType.SPRINKLER_VALVE,
        EntityType.SPRINKLER_WIRE,
        EntityType.TREE,
        EntityType.TRIMMER,
    })
    SECURITY = ( 'Security', '', {
        EntityType.CAMERA,
        EntityType.CARBON_MONOXIDE_DETECTOR,
        EntityType.DOORBELL,
        EntityType.DOOR_LOCK,
        EntityType.FIRE_EXTINGUISHER,
        EntityType.LIGHT_SENSOR,
        EntityType.MOTION_SENSOR,
        EntityType.OPEN_CLOSE_SENSOR,
        EntityType.PRESENCE_SENSOR,
        EntityType.SMOKE_DETECTOR,
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
        EntityType.DRAINAGE_PIPE,
        EntityType.ELECTRICITY_METER,
        EntityType.ELECTRIC_PANEL,
        EntityType.ELECTRIC_WIRE,
        EntityType.GENERATOR,
        EntityType.SATELLITE_DISH,
        EntityType.SEWER_LINE,
        EntityType.SOLAR_PANEL,
        EntityType.TELECOM_BOX,
        EntityType.TELECOM_WIRE,
        EntityType.UPS,
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

    
class EntityTransitionType(LabeledEnum):
    """Types of entity type transitions that can occur during entity type changes."""
    
    # Successful transition types
    ICON_TO_ICON = ('Icon to Icon', 'Transition between two icon-based entity types')
    ICON_TO_PATH = ('Icon to Path', 'Transition from icon-based to path-based entity type')  
    PATH_TO_ICON = ('Path to Icon', 'Transition from path-based to icon-based entity type')
    PATH_TO_PATH = ('Path to Path', 'Transition between two path-based entity types')
    CREATED_POSITION = ('Created Position', 'Created new entity position for entity without existing representation')
    CREATED_PATH = ('Created Path', 'Created new entity path for entity without existing representation')
    
    # Error/edge case types  
    NO_LOCATION_VIEW = ('No Location View', 'No location view provided for transition')
    NO_TRANSITION_NEEDED = ('No Transition Needed', 'Entity type change did not require visual transition')
