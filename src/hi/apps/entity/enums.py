from typing import List, Set, Tuple

from hi.apps.common.enums import LabeledEnum
from hi.apps.common.utils import get_humanized_name


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
    BATTERY_STORAGE      = ( 'Battery Storage', '' )
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
    EV_CHARGER           = ( 'EV Charger', '' )
    EXHAUST_FAN          = ( 'Exhaust Fan', '' )
    FENCE                = ( 'Fence', '' )
    FIRE_EXTINGUISHER    = ( 'Fire Extinguisher', '' )
    FIREPLACE            = ( 'Fireplace', '' )
    FREEZER              = ( 'Freezer', '' )
    FURNITURE            = ( 'Furniture', '' )
    GARAGE_DOOR          = ( 'Garage Door', '' )
    GARAGE_DOOR_OPENER   = ( 'Garage Door Opener', '' )
    GARBAGE_DISPOSAL     = ( 'Garbage Disposal', '' )
    GAS_DETECTOR         = ( 'Gas Detector', '' )
    GAS_LINE             = ( 'Gas Line', '' )
    GAS_METER            = ( 'Gas Meter', '' )
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
    INVERTER             = ( 'Inverter', '' )
    IRRIGATION_CONTROLLER = ( 'Irrigation Controller', '' )
    LAWN_MOWER           = ( 'Lawn Mower', '' )
    LEAF_BLOWER          = ( 'Leaf Blower', '' )
    LEAK_SENSOR          = ( 'Leak Sensor', '' )
    LIGHT                = ( 'Light', '' )
    LIGHT_SENSOR         = ( 'Light Sensor', '' )
    MICROWAVE_OVEN       = ( 'Microwave Oven', '' )
    MODEM                = ( 'Modem', '' )
    MOTION_SENSOR        = ( 'Motion Sensor', '' )
    MOTOR                = ( 'Motor', '' )
    NETWORK_SWITCH       = ( 'Network Switch', '' )
    ON_OFF_SWITCH        = ( 'On/Off Switch', '' )
    OPEN_CLOSE_ACTUATOR  = ( 'Open/Close Actuator', '' )  # Controls things that open/close
    OPEN_CLOSE_SENSOR    = ( 'Open/Close Sensor', '' )
    OTHER                = ( 'Other', '' )  # Will use generic visual element
    OVEN                 = ( 'Oven', '' )
    PIPE                 = ( 'Pipe', '' )
    PLANT                = ( 'Plant', '' )
    POOL_FILTER          = ( 'Pool Filter', '' )
    POOL_HEATER          = ( 'Pool Heater', '' )
    POOL_PUMP            = ( 'Pool Pump', '' )
    POOL_SWG             = ( 'Pool SWG', '' )
    POWER_WASHER         = ( 'Power Washer', '' )
    PRESENCE_SENSOR      = ( 'Presence Sensor', '' )
    PRINTER              = ( 'Printer', '' )
    PUMP                 = ( 'Pump', '' )
    RADON_DETECTOR       = ( 'Radon Detector', '' )
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
    SUMP_PUMP            = ( 'Sump Pump', '' )
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
    WATER_FILTER         = ( 'Water Filter', '' )
    WATER_HEATER         = ( 'Water Heater', '' )
    WATER_SOFTENER       = ( 'Water Softener', '' )
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
            cls.GARAGE_DOOR,
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
            cls.GAS_LINE,
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

    def entity_status_template_name(self) -> str:
        """Template used to render the EntityStatusView modal's body
        for this EntityType. Create the template at the returned
        path to define an EntityType-specific layout (e.g., a
        graphical thermostat widget); otherwise the dispatcher
        falls back to the default flat-list rendering."""
        return f'entity/modals/entity_status_{self.name.lower()}.html'


class EntityStateValue(LabeledEnum):
    # Alarm-style values (e.g., ACTIVE, OPEN, SMOKE_DETECTED) are
    # rendered as the ``status`` attribute on both the SVG icon
    # ``g`` element and the sensor card ``div``. Each new pair
    # needs matching ``g[status="..."]`` and ``div[status="..."]``
    # rules in main.css for the resting and alarmed states (the
    # resting state may legitimately omit the ``g`` rule when no
    # glow is wanted). Missing rules surface as a first-paint
    # color flash that disappears on the first poll once the
    # bucketed StatusStyle value gets applied.

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

    SMOKE_DETECTED = ( 'Smoke Detected', '' )
    SMOKE_CLEAR    = ( 'Clear', '' )

    MOISTURE_DETECTED = ( 'Moisture Detected', '' )
    MOISTURE_CLEAR    = ( 'Clear', '' )

    CO_DETECTED    = ( 'Carbon Monoxide Detected', '' )
    CO_CLEAR       = ( 'Clear', '' )

    GAS_DETECTED   = ( 'Gas Detected', '' )
    GAS_CLEAR      = ( 'Clear', '' )

    # OBJECT_PRESENCE values — canonical buckets the integration's
    # converter maps raw upstream object-detection labels onto. The
    # raw label (e.g. Frigate's ``dog`` / ``truck`` / arbitrary
    # custom-model class) is preserved on the sensor's
    # ``detail_attrs``; the typed-enum value lets rule matching and
    # styling key off a stable, bounded vocabulary.
    OBJECT_NONE     = ( 'No Object', '' )
    OBJECT_PERSON   = ( 'Person', '' )
    OBJECT_CAR      = ( 'Car', '' )
    OBJECT_ANIMAL   = ( 'Animal', '' )
    OBJECT_PACKAGE  = ( 'Package', '' )
    OBJECT_OTHER    = ( 'Other Object', '' )

    # COLOR_MODE values — modes a smart bulb can be in. UNKNOWN
    # covers integrations that don't report a mode and cases where
    # the bulb hasn't yet declared one. Names follow HA's modes;
    # see EntityStateType.COLOR_MODE for the integration mapping.
    COLOR_MODE_UNKNOWN     = ( 'Unknown', '' )
    COLOR_MODE_ONOFF       = ( 'Basic On/Off', '' )
    COLOR_MODE_BRIGHTNESS  = ( 'Brightness', '' )
    COLOR_MODE_COLOR_TEMP  = ( 'White Temperature', '' )
    COLOR_MODE_HS          = ( 'HS Color', '' )
    COLOR_MODE_RGB         = ( 'RGB Color', '' )
    COLOR_MODE_RGBW        = ( 'RGBW Color', '' )
    COLOR_MODE_RGBWW       = ( 'RGBWW Color', '' )
    COLOR_MODE_XY          = ( 'XY Color', '' )
    COLOR_MODE_WHITE       = ( 'White', '' )

    @classmethod
    def to_display_label( cls, entity_state_value : str ) -> str:
        """Resolve a stored EntityState value to a display label.
        Known enum members return their authoritative ``.label``;
        free-form values (e.g., HA-derived ``'heating'``,
        ``'fan_only'`` after integration-boundary normalization)
        are humanized into title case. Numeric values pass through
        unchanged so the humanizer doesn't mangle them."""
        if not entity_state_value:
            return entity_state_value
        try:
            return cls.from_name( entity_state_value ).label
        except ValueError:
            if entity_state_value[ 0 ].isdigit():
                return entity_state_value
            return get_humanized_name( entity_state_value )


class EntityStateRole(LabeledEnum):
    """Semantic role an EntityState plays within its enclosing entity's
    presentation. Type defaults (member name matches an EntityStateType
    member) provide a baseline for any EntityState; domain-prefixed
    members refine the role when multiple EntityStates of the same type
    coexist on an entity (e.g., a thermostat's current vs. target
    temperatures).

    Some labels collide between a type-default member and a domain
    refinement (e.g., ON_OFF / LIGHT_ON_OFF both display "On/Off";
    BRIGHTNESS-like roles share labels). This is intentional: labels
    describe what the user reads; the enum *name* is the disambiguator
    used internally (admin, debug, role-priority lookups)."""

    # Type defaults. One member per EntityStateType; names match
    # so EntityStateType.default_role() can resolve by name.
    DISCRETE             = ( 'Discrete'           , '' )
    CONTINUOUS           = ( 'Continuous'         , '' )
    MULTIVALUED          = ( 'Multi-valued'       , '' )
    BLOB                 = ( 'Blob'               , '' )
    AIR_PRESSURE         = ( 'Air Pressure'       , '' )
    BANDWIDTH_USAGE      = ( 'Bandwidth Usage'    , '' )
    BATTERY_LEVEL        = ( 'Battery'            , '' )
    COLOR_MODE           = ( 'Color Mode'         , '' )
    COLOR_TEMPERATURE    = ( 'Color Temperature'  , '' )
    CONNECTIVITY         = ( 'Connectivity'       , '' )
    DATETIME             = ( 'Date/Time'          , '' )
    ELECTRIC_USAGE       = ( 'Electric Usage'     , '' )
    HIGH_LOW             = ( 'High/Low'           , '' )
    HUE                  = ( 'Hue'                , '' )
    HUMIDITY             = ( 'Humidity'           , '' )
    LIGHT_DIMMER         = ( 'Light Dimmer'       , '' )
    LIGHT_LEVEL          = ( 'Light Level'        , '' )
    MOISTURE             = ( 'Moisture'           , '' )
    MOVEMENT             = ( 'Movement'           , '' )
    OBJECT_PRESENCE      = ( 'Object Presence'    , '' )
    ON_OFF               = ( 'On/Off'             , '' )
    OPEN_CLOSE           = ( 'Open/Close'         , '' )
    OPEN_CLOSE_POSITION  = ( 'Open/Close Position', '' )
    POWER_LEVEL          = ( 'Power Level'        , '' )
    PRESENCE             = ( 'Presence'           , '' )
    SATURATION           = ( 'Saturation'         , '' )
    SMOKE                = ( 'Smoke'              , '' )
    CO                   = ( 'Carbon Monoxide'    , '' )
    GAS                  = ( 'Gas'                , '' )
    SOUND_LEVEL          = ( 'Sound Level'        , '' )
    TEMPERATURE          = ( 'Temperature'        , '' )
    WATER_FLOW           = ( 'Water Flow'         , '' )
    WIND_SPEED           = ( 'Wind Speed'         , '' )

    # Domain-prefixed refinements for multi-state entities.
    THERMOSTAT_CURRENT_TEMPERATURE     = ( 'Current Temperature' , '' )
    THERMOSTAT_TARGET_TEMPERATURE      = ( 'Setpoint'            , '' )
    THERMOSTAT_TARGET_TEMPERATURE_LOW  = ( 'Setpoint Low'        , '' )
    THERMOSTAT_TARGET_TEMPERATURE_HIGH = ( 'Setpoint High'       , '' )
    HVAC_MODE                          = ( 'HVAC Mode'           , '' )
    HVAC_ACTION                        = ( 'HVAC Action'         , '' )
    FAN_MODE                           = ( 'Fan Mode'            , '' )
    PRESET_MODE                        = ( 'Preset Mode'         , '' )
    SWING_MODE                         = ( 'Swing Mode'          , '' )

    FAN_SPEED                          = ( 'Fan Speed'           , '' )
    FAN_OSCILLATION                    = ( 'Fan Oscillation'     , '' )
    FAN_DIRECTION                      = ( 'Fan Direction'       , '' )
    FAN_PRESET_MODE                    = ( 'Fan Preset Mode'     , '' )

    LIGHT_BRIGHTNESS                   = ( 'Brightness'          , '' )
    LIGHT_HUE                          = ( 'Hue'                 , '' )
    LIGHT_SATURATION                   = ( 'Saturation'          , '' )
    LIGHT_COLOR_TEMPERATURE            = ( 'Color Temperature'   , '' )
    LIGHT_COLOR_MODE                   = ( 'Color Mode'          , '' )
    LIGHT_ON_OFF                       = ( 'On/Off'              , '' )

    @classmethod
    def default(cls):
        return cls.DISCRETE


class DisplayContext(LabeledEnum):
    """Author-facing shape vocabulary for panel templates.

    Each value names a shape the panel author designs for; consumers
    (CollectionView, modal renderers, etc.) map their layout choices
    onto these shapes. See ``docs/dev/frontend/entity-state-panels.md``
    for size budgets and the CSS-variable contract.
    """

    MODAL = ( 'Modal', '' )
    ROW   = ( 'Row' , '' )    # wide, full-width strip; ~80px tall
    TILE  = ( 'Tile', '' )    # square-ish, gridable; 240-280 wide × 200-260 tall


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
    BATTERY_LEVEL    = ( 'Battery'          , 'Battery level as a percentage (0-100)',
                         [] )
    # COLOR_MODE reports which lighting mode a smart bulb is
    # currently in (e.g., HS color, white temperature, basic
    # on/off). The per-device supported subset is declared by HA
    # in ``supported_color_modes`` and captured in
    # ``value_range_str`` at import time, so ``choices()`` reads
    # from there rather than enumerating every COLOR_MODE_*
    # member here. The COLOR_MODE_* EntityStateValue members
    # still provide authoritative labels for display via
    # ``to_display_label``.
    COLOR_MODE       = ( 'Color Mode'       , 'Active lighting color mode',
                         [] )
    # COLOR_TEMPERATURE is the white-light Kelvin scale
    # (warm 2000K to cool 6500K); distinct from a chromatic
    # color (HUE+SATURATION) since the underlying physics and
    # the natural UI affordance are different — a 1-D Kelvin
    # slider, not a 2-D color picker.
    COLOR_TEMPERATURE = ( 'Color Temperature', 'White-light temperature in Kelvin',
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
    # HUE and SATURATION are paired in HA's ``hs_color`` 2-tuple
    # but modeled as separate 1-D EntityStates here so each gets
    # its own slider; the controller dispatch composes the pair
    # at the HA service-call boundary. HUE is in degrees (0-360);
    # SATURATION is a percentage (0-100). Brightness is a third,
    # independent dimension (LIGHT_DIMMER) — see hi_styles.py
    # for the chromaticity-vs-intensity rationale.
    HUE              = ( 'Hue'              , 'Color hue in degrees (0-360)',
                         [] )
    HUMIDITY         = ( 'Humidity'         , '',
                         [] )
    LIGHT_DIMMER     = ( 'Light Dimmer'     , 'Controllable light brightness (0-100)',
                         [] )
    LIGHT_LEVEL      = ( 'Light Level'      , '',
                         [] )
    MOISTURE         = ( 'Moisture'         , 'Binary leak / moisture detected state',
                         [ EntityStateValue.MOISTURE_DETECTED,
                           EntityStateValue.MOISTURE_CLEAR ] )
    MOVEMENT         = ( 'Movement'         , '',
                         [ EntityStateValue.ACTIVE,
                           EntityStateValue.IDLE ] )
    # OBJECT_PRESENCE — discrete object-class detection. Value space
    # is the canonical bucket set; the integration's converter
    # (e.g. ``FrigateConverter.to_canonical_object_class``) maps raw
    # upstream labels onto these so rule matching and styling key
    # off a bounded vocabulary. ``OBJECT_NONE`` is the resting
    # value; everything else is an alarm-style detection.
    OBJECT_PRESENCE  = ( 'Object Presence' , '',
                         [ EntityStateValue.OBJECT_NONE,
                           EntityStateValue.OBJECT_PERSON,
                           EntityStateValue.OBJECT_CAR,
                           EntityStateValue.OBJECT_ANIMAL,
                           EntityStateValue.OBJECT_PACKAGE,
                           EntityStateValue.OBJECT_OTHER ] )
    ON_OFF           = ( 'On/Off'           , '',
                         [ EntityStateValue.ON,
                           EntityStateValue.OFF ] )    
    OPEN_CLOSE       = ( 'Open/Close'       , '',
                         [ EntityStateValue.OPEN,
                           EntityStateValue.CLOSED ] )
    OPEN_CLOSE_POSITION = ( 'Open/Close Position',
                            'Continuous open/close position as a percentage (0=closed, 100=open)',
                            [] )
    POWER_LEVEL      = ( 'Power Level',
                         'Generic continuous power/intensity/speed (0-100). Per-context label '
                         '(e.g., "Speed" for fans, "Aperture" for dampers) is set on the '
                         'EntityState.',
                         [] )
    PRESENCE         = ( 'Presence'         , '',
                         [ EntityStateValue.ACTIVE,
                           EntityStateValue.IDLE ] )
    SATURATION       = ( 'Saturation'       , 'Color saturation as a percentage (0-100)',
                         [] )
    SMOKE            = ( 'Smoke'            , '',
                         [ EntityStateValue.SMOKE_DETECTED,
                           EntityStateValue.SMOKE_CLEAR ] )
    CO               = ( 'Carbon Monoxide'  , 'Binary carbon monoxide detected state',
                         [ EntityStateValue.CO_DETECTED,
                           EntityStateValue.CO_CLEAR ] )
    GAS              = ( 'Gas'              , 'Binary combustible-gas detected state',
                         [ EntityStateValue.GAS_DETECTED,
                           EntityStateValue.GAS_CLEAR ] )
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

    def default_role(self) -> EntityStateRole:
        """The default EntityStateRole for an EntityState of this type.
        Type-default ``EntityStateRole`` members share their name with
        the matching ``EntityStateType`` member; lookup is by name."""
        return EntityStateRole[ self.name ]


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
    """Discrimination of what kind of media lives at ``VideoStream.source_url``.
    Drives the HI render layer's choice between ``<img>`` (browsers
    render multipart/x-mixed-replace MJPEG inside <img>) and
    ``<video>`` (for actual MP4 / HLS / WebM clips)."""

    MJPEG = ('MJPEG', 'multipart/x-mixed-replace stream rendered by <img>')
    MP4 = ('MP4', 'MP4 clip rendered by <video>')
    OTHER = ('Other', 'Other video stream type for future extensibility')

    @classmethod
    def default(cls):
        return cls.OTHER


class EntityGroupType(LabeledEnum):
    """Rollup of leaf ``EntityType`` values into broader buckets that
    match how a homeowner organizes their LocationView floor plans
    and CollectionViews. Surfaced in the entity-editing and
    collection-editing group lists, and used as the default
    grouping dimension by integration placement modals.

    Bucket-assignment invariants pinned by ``test_enums.py``:
      - Every ``EntityType`` is explicitly assigned to exactly one
        bucket — no silent fallbacks.
      - ``GENERAL`` is the catchall for types that don't fit a
        domain bucket; ``EntityType.OTHER`` lives there too."""

    APPLIANCES = ( 'Appliances', '', {
        EntityType.APPLIANCE,
        EntityType.LARGE_APPLIANCE,
        EntityType.CLOTHES_DRYER,
        EntityType.CLOTHES_WASHER,
        EntityType.COFFEE_MAKER,
        EntityType.COOKTOP,
        EntityType.DISHWASHER,
        EntityType.EXHAUST_FAN,
        EntityType.FREEZER,
        EntityType.GARBAGE_DISPOSAL,
        EntityType.GRILL,
        EntityType.HUMIDIFIER,
        EntityType.HVAC_AIR_HANDLER,
        EntityType.HVAC_CONDENSER,
        EntityType.HVAC_FURNACE,
        EntityType.HVAC_MINI_SPLIT,
        EntityType.MICROWAVE_OVEN,
        EntityType.OVEN,
        EntityType.RANGE_HOOD,
        EntityType.REFRIGERATOR,
        EntityType.THERMOSTAT,
        EntityType.WATER_FILTER,
        EntityType.WATER_HEATER,
        EntityType.WATER_SOFTENER,
    })
    AUDIO_VISUAL = ( 'Audio/Visual', '', {
        EntityType.AV_RECEIVER,
        EntityType.SPEAKER,
        EntityType.SPEAKER_WIRE,
        EntityType.TELEVISION,
    })
    AUTOMATION = ( 'Automation', '', {
        EntityType.CONTROLLER,
        EntityType.DOOR_LOCK,
        EntityType.ELECTRICAL_OUTLET,
        EntityType.GARAGE_DOOR_OPENER,
        EntityType.IRRIGATION_CONTROLLER,
        EntityType.LIGHT,
        EntityType.ON_OFF_SWITCH,
        EntityType.OPEN_CLOSE_ACTUATOR,
        EntityType.WALL_SWITCH,
    })
    COMPUTERS = ( 'Computers', '', {
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
    ELECTRICAL = ( 'Electrical', '', {
        EntityType.BATTERY_STORAGE,
        EntityType.CONTROL_WIRE,
        EntityType.ELECTRIC_PANEL,
        EntityType.ELECTRIC_WIRE,
        EntityType.EV_CHARGER,
        EntityType.GENERATOR,
        EntityType.INVERTER,
        EntityType.MOTOR,
        EntityType.PUMP,
        EntityType.SOLAR_PANEL,
        EntityType.SUMP_PUMP,
        EntityType.UPS,
    })
    FIXTURES = ( 'Fixtures', '', {
        EntityType.BATHTUB,
        EntityType.CEILING_FAN,
        EntityType.FURNITURE,
        EntityType.SHOWER,
        EntityType.SINK,
        EntityType.TOILET,
        EntityType.VANITY,
    })
    GENERAL = ( 'General', '', {
        EntityType.AUTOMOBILE,
        EntityType.CONSUMABLE,
        EntityType.OTHER,
    })
    OUTDOORS = ( 'Outdoors', '', {
        EntityType.FENCE,
        EntityType.GREENHOUSE,
        EntityType.PLANT,
        EntityType.SPRINKLER_HEAD,
        EntityType.SPRINKLER_VALVE,
        EntityType.SPRINKLER_WIRE,
        EntityType.TREE,
    })
    POOL = ( 'Pool', '', {
        EntityType.POOL_FILTER,
        EntityType.POOL_HEATER,
        EntityType.POOL_PUMP,
        EntityType.POOL_SWG,
    })
    SECURITY = ( 'Security', '', {
        EntityType.CAMERA,
        EntityType.CARBON_MONOXIDE_DETECTOR,
        EntityType.DOORBELL,
        EntityType.FIRE_EXTINGUISHER,
        EntityType.GAS_DETECTOR,
        EntityType.LEAK_SENSOR,
        EntityType.MOTION_SENSOR,
        EntityType.OPEN_CLOSE_SENSOR,
        EntityType.PRESENCE_SENSOR,
        EntityType.RADON_DETECTOR,
        EntityType.SMOKE_DETECTOR,
    })
    SENSORS = ( 'Sensors', '', {
        EntityType.BAROMETER,
        EntityType.HYGROMETER,
        EntityType.LIGHT_SENSOR,
        EntityType.THERMOMETER,
        EntityType.TIME_SOURCE,
        EntityType.WEATHER_STATION,
    })
    STRUCTURAL = ( 'Structural', '', {
        EntityType.AREA,
        EntityType.ATTIC_STAIRS,
        EntityType.DOOR,
        EntityType.FIREPLACE,
        EntityType.GARAGE_DOOR,
        EntityType.SKYLIGHT,
        EntityType.WALL,
        EntityType.WINDOW,
    })
    TOOLS = ( 'Tools', '', {
        EntityType.HEDGE_TRIMMER,
        EntityType.LAWN_MOWER,
        EntityType.LEAF_BLOWER,
        EntityType.POWER_WASHER,
        EntityType.TOOL,
        EntityType.TRIMMER,
    })
    UTILITIES = ( 'Utilities', '', {
        EntityType.ANTENNA,
        EntityType.DRAINAGE_PIPE,
        EntityType.ELECTRICITY_METER,
        EntityType.GAS_LINE,
        EntityType.GAS_METER,
        EntityType.PIPE,
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
        return cls.GENERAL

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
