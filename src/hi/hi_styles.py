from enum import Enum

from hi.apps.common.svg_models import SvgRadius, SvgStatusStyle, SvgViewBox

from hi.apps.collection.enums import CollectionType
from hi.apps.entity.enums import EntityType


class EntityIconDirection(Enum):
    """Direction an entity's source icon SVG was authored to point.
    Independent of any runtime rotation the user applies to a placed
    entity. Values for the cardinal directions are (dx, dy) unit
    vectors in SVG coordinates (+x = right, +y = down). ``UNKNOWN``
    is a sentinel returned by ``EntityStyle.get_icon_direction`` when
    the entity type has no mapped direction; callers choose their own
    default behavior."""
    UNKNOWN      = None
    POINTS_RIGHT = (1.0, 0.0)
    POINTS_DOWN  = (0.0, 1.0)
    POINTS_LEFT  = (-1.0, 0.0)
    POINTS_UP    = (0.0, -1.0)


class ItemStyle:

    @classmethod
    def get_default_svg_icon_template_name( cls ):
        return 'entity/svg/type.other.svg'

    @classmethod
    def get_default_svg_icon_viewbox( cls ):
        return SvgViewBox( x = 0, y = 0, width = 64, height = 64 )
    
    @classmethod
    def get_default_svg_icon_status_style( cls ):
        return SvgStatusStyle(
            status_value = '',
            stroke_color = '#a0a0a0',
            stroke_width = 4.0,
            stroke_dasharray = [],
            fill_color = 'none',
            fill_opacity = 0.0,
        )

    @classmethod
    def get_default_svg_path_status_style( cls ):
        return SvgStatusStyle(
            status_value = '',
            stroke_color = '#404050',
            stroke_width = 4.0,
            stroke_dasharray = [],
            fill_color = '#ffffd0',
            fill_opacity = 1.0,
        )
    
        
class CollectionStyle:

    DEFAULT_STATUS_VALUE = 3
    DEFAULT_STROKE_COLOR = '#202030'
    DEFAULT_STROKE_WIDTH = 2
    DEFAULT_DASHARRAY = [ 6, 3 ]
    DEFAULT_OPACITY = 1.0
    
    PathCollectionTypeToSvgStatusStyle = {
        CollectionType.APPLIANCES: SvgStatusStyle(
            status_value = DEFAULT_STATUS_VALUE,
            stroke_color = DEFAULT_STROKE_COLOR,
            stroke_width = DEFAULT_STROKE_WIDTH,
            stroke_dasharray = DEFAULT_DASHARRAY,
            fill_color = '#ffffff',
            fill_opacity = DEFAULT_OPACITY,
        ),
        CollectionType.CAMERAS: SvgStatusStyle(
            status_value = DEFAULT_STATUS_VALUE,
            stroke_color = DEFAULT_STROKE_COLOR,
            stroke_width = DEFAULT_STROKE_WIDTH,
            stroke_dasharray = DEFAULT_DASHARRAY,
            fill_color = '#ffffc0',
            fill_opacity = DEFAULT_OPACITY,
        ),
        CollectionType.DEVICES: SvgStatusStyle(
            status_value = DEFAULT_STATUS_VALUE,
            stroke_color = DEFAULT_STROKE_COLOR,
            stroke_width = DEFAULT_STROKE_WIDTH,
            stroke_dasharray = DEFAULT_DASHARRAY,
            fill_color = '#c0c0c0',
            fill_opacity = DEFAULT_OPACITY,
        ),
        CollectionType.ELECTRONICS: SvgStatusStyle(
            status_value = DEFAULT_STATUS_VALUE,
            stroke_color = DEFAULT_STROKE_COLOR,
            stroke_width = DEFAULT_STROKE_WIDTH,
            stroke_dasharray = DEFAULT_DASHARRAY,
            fill_color = '#ffffd0',
            fill_opacity = DEFAULT_OPACITY,
        ),
        CollectionType.GARDENING: SvgStatusStyle(
            status_value = DEFAULT_STATUS_VALUE,
            stroke_color = DEFAULT_STROKE_COLOR,
            stroke_width = DEFAULT_STROKE_WIDTH,
            stroke_dasharray = DEFAULT_DASHARRAY,
            fill_color = '#c0ffc0',
            fill_opacity = DEFAULT_OPACITY,
        ),
        CollectionType.LANDSCAPING: SvgStatusStyle(
            status_value = DEFAULT_STATUS_VALUE,
            stroke_color = DEFAULT_STROKE_COLOR,
            stroke_width = DEFAULT_STROKE_WIDTH,
            stroke_dasharray = DEFAULT_DASHARRAY,
            fill_color = '#c0c0ff',
            fill_opacity = DEFAULT_OPACITY,
        ),
        CollectionType.TOOLS: SvgStatusStyle(
            status_value = '',
            stroke_color = DEFAULT_STROKE_COLOR,
            stroke_width = DEFAULT_STROKE_WIDTH,
            stroke_dasharray = DEFAULT_DASHARRAY,
            fill_color = '#c0c0ff',
            fill_opacity = DEFAULT_OPACITY,
        ),
    }
    CollectionTypePathInitialRadius = {
    }

    @classmethod
    def get_svg_path_status_style( cls, collection_type : CollectionType ) -> SvgStatusStyle:
        if collection_type in cls.PathCollectionTypeToSvgStatusStyle:
            return cls.PathCollectionTypeToSvgStatusStyle.get( collection_type )
        return ItemStyle.get_default_svg_path_status_style()

    @classmethod
    def get_svg_path_initial_radius( cls, collection_type : CollectionType ) -> SvgRadius:
        if collection_type in cls.CollectionTypePathInitialRadius:
            return cls.CollectionTypePathInitialRadius.get( collection_type )
        return SvgRadius( x = None, y = None )

    
class EntityStyle:

    Appliance = SvgStatusStyle(
        status_value = '',
        stroke_color = '#040406',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#f8f8f0',
        fill_opacity = 1,
    )
    Area = SvgStatusStyle(
        status_value = '',
        stroke_color = '#0606a0',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#8080ff',
        fill_opacity = 0.1,
    )
    ControlWire = SvgStatusStyle(
        status_value = '',
        stroke_color = '#800080',
        stroke_width = 3,
        stroke_dasharray = [ 3, 6 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    Door = SvgStatusStyle(
        status_value = '',
        stroke_color = '#c0c0c0',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#5f3929',
        fill_opacity = 1,
    )
    ElectricWire = SvgStatusStyle(
        status_value = '',
        stroke_color = '#FF0000',
        stroke_width = 3,
        stroke_dasharray = [ 2, 2 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    Fence = SvgStatusStyle(
        status_value = '',
        stroke_color = '#8B4513',
        stroke_width = 6,
        stroke_dasharray = [ 10, 2 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    Furniture = SvgStatusStyle(
        status_value = '',
        stroke_color = '#8B4513',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#D2B48C',
        fill_opacity = 1,
    )
    Greenhouse = SvgStatusStyle(
        status_value = '',
        stroke_color = '#06a006',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#a0f0a0',
        fill_opacity = 1,
    )
    Pipe = SvgStatusStyle(
        status_value = '',
        stroke_color = '#808080',
        stroke_width = 3,
        stroke_dasharray = [ 6, 2, 6, 2, 3, 2 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    GarageDoor = SvgStatusStyle(
        status_value = '',
        stroke_color = '#888888',
        stroke_width = 3,
        stroke_dasharray = [],
        fill_color = '#b0b0b0',
        fill_opacity = 1,
    )
    GasLine = SvgStatusStyle(
        status_value = '',
        stroke_color = '#CCAA00',
        stroke_width = 3,
        stroke_dasharray = [ 6, 3 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    SewerLine = SvgStatusStyle(
        status_value = '',
        stroke_color = '#008000',
        stroke_width = 3,
        stroke_dasharray = [ 8, 4, 2, 4 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    SpeakerWire = SvgStatusStyle(
        status_value = '',
        stroke_color = '#04a004',
        stroke_width = 2,
        stroke_dasharray = [ 8, 2, 2, 2, 2, 2 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    TelecomWire = SvgStatusStyle(
        status_value = '',
        stroke_color = '#FFA500',
        stroke_width = 3,
        stroke_dasharray = [ 6, 2 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    Wall = SvgStatusStyle(
        status_value = '',
        stroke_color = '#c0c0c0',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#808080',
        fill_opacity = 1,
    )
    WaterLine = SvgStatusStyle(
        status_value = '',
        stroke_color = '#0000FF',
        stroke_width = 3,
        stroke_dasharray = [ 4, 2 ],
        fill_color = None,
        fill_opacity = 0.0,
    )
    Window = SvgStatusStyle(
        status_value = '',
        stroke_color = '#808080',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#78e3df',
        fill_opacity = 1,
    )

    EntityTypesWithIcons = {
        # Default icon used if not in this map
        EntityType.ACCESS_POINT,
        EntityType.ANTENNA,
        EntityType.APPLIANCE,
        EntityType.ATTIC_STAIRS,
        EntityType.AUTOMOBILE,
        EntityType.AV_RECEIVER,
        EntityType.BAROMETER,
        EntityType.BATTERY_STORAGE,
        EntityType.BATHTUB,
        EntityType.CAMERA,
        EntityType.CARBON_MONOXIDE_DETECTOR,
        EntityType.CEILING_FAN,
        EntityType.CLOTHES_DRYER,
        EntityType.CLOTHES_WASHER,
        EntityType.COFFEE_MAKER,
        EntityType.COMPUTER,
        EntityType.CONSUMABLE,
        EntityType.CONTROLLER,
        EntityType.COOKTOP,
        EntityType.DISHWASHER,
        EntityType.DISK,
        EntityType.DOORBELL,
        EntityType.DOOR_LOCK,
        EntityType.ELECTRICAL_OUTLET,
        EntityType.ELECTRICITY_METER,
        EntityType.ELECTRIC_PANEL,
        EntityType.EV_CHARGER,
        EntityType.EXHAUST_FAN,
        EntityType.FIRE_EXTINGUISHER,
        EntityType.FIREPLACE,
        EntityType.FREEZER,
        EntityType.GARAGE_DOOR_OPENER,
        EntityType.GARBAGE_DISPOSAL,
        EntityType.GAS_DETECTOR,
        EntityType.GAS_METER,
        EntityType.GENERATOR,
        EntityType.GRILL,
        EntityType.HEALTHCHECK,
        EntityType.HEDGE_TRIMMER,
        EntityType.HUMIDIFIER,
        EntityType.HVAC_AIR_HANDLER,
        EntityType.HVAC_CONDENSER,
        EntityType.HVAC_FURNACE,
        EntityType.HVAC_MINI_SPLIT,
        EntityType.HYGROMETER,
        EntityType.INVERTER,
        EntityType.IRRIGATION_CONTROLLER,
        EntityType.LAWN_MOWER,
        EntityType.LEAF_BLOWER,
        EntityType.LEAK_SENSOR,
        EntityType.LIGHT,
        EntityType.LIGHT_SENSOR,
        EntityType.MICROWAVE_OVEN,
        EntityType.MODEM,
        EntityType.MOTION_SENSOR,
        EntityType.MOTOR,
        EntityType.NETWORK_SWITCH,
        EntityType.ON_OFF_SWITCH,
        EntityType.OPEN_CLOSE_ACTUATOR,
        EntityType.OPEN_CLOSE_SENSOR,
        EntityType.OVEN,
        EntityType.PLANT,
        EntityType.POOL_FILTER,
        EntityType.POOL_HEATER,
        EntityType.POOL_PUMP,
        EntityType.POOL_SWG,
        EntityType.POWER_WASHER,
        EntityType.PRESENCE_SENSOR,
        EntityType.PRINTER,
        EntityType.PUMP,
        EntityType.RANGE_HOOD,
        EntityType.REFRIGERATOR,
        EntityType.SATELLITE_DISH,
        EntityType.SERVER,
        EntityType.SERVICE,
        EntityType.SHOWER,
        EntityType.SINK,
        EntityType.SKYLIGHT,
        EntityType.RADON_DETECTOR,
        EntityType.SMOKE_DETECTOR,
        EntityType.SOLAR_PANEL,
        EntityType.SPEAKER,
        EntityType.SPRINKLER_HEAD,
        EntityType.SPRINKLER_VALVE,
        EntityType.SUMP_PUMP,
        EntityType.TELECOM_BOX,
        EntityType.TELEVISION,
        EntityType.THERMOMETER,
        EntityType.THERMOSTAT,
        EntityType.TIME_SOURCE,
        EntityType.TOILET,
        EntityType.TOOL,
        EntityType.TREE,
        EntityType.TRIMMER,
        EntityType.UPS,
        EntityType.VANITY,
        EntityType.WALL_SWITCH,
        EntityType.WATER_FILTER,
        EntityType.WATER_HEATER,
        EntityType.WATER_METER,
        EntityType.WATER_SOFTENER,
        EntityType.WATER_SHUTOFF_VALVE,
        EntityType.WEATHER_STATION,
    }
    EntityTypeToIconViewbox = {
        # Default viewbox used if not in this map
        EntityType.ATTIC_STAIRS: SvgViewBox( x = 0, y = 0, width = 47, height = 64 ),
        EntityType.AUTOMOBILE: SvgViewBox( x = 0, y = 0, width = 200, height = 300 ),
        EntityType.BAROMETER: SvgViewBox( x = 0, y = 0, width = 44, height = 64 ),
        EntityType.CAMERA: SvgViewBox( x = 0, y = 0, width = 64, height = 43 ),
        EntityType.CONTROLLER: SvgViewBox( x = 0, y = 0, width = 47, height = 64 ),
        EntityType.DISK: SvgViewBox( x = 0, y = 0, width = 51, height = 64 ),
        EntityType.ELECTRICAL_OUTLET: SvgViewBox( x = 0, y = 0, width = 45, height = 64 ),
        EntityType.HUMIDIFIER: SvgViewBox( x = 0, y = 0, width = 44, height = 64 ),
        EntityType.HVAC_AIR_HANDLER: SvgViewBox( x = 0, y = 0, width = 64, height = 44 ),
        EntityType.MICROWAVE_OVEN: SvgViewBox( x = 0, y = 0, width = 64, height = 46 ),
        EntityType.MODEM: SvgViewBox( x = 0, y = 0, width = 37, height = 64 ),
        EntityType.MOTION_SENSOR: SvgViewBox( x = 0, y = 0, width = 42, height = 64 ),
        EntityType.MOTOR: SvgViewBox( x = 0, y = 0, width = 64, height = 46 ),
        EntityType.NETWORK_SWITCH: SvgViewBox( x = 0, y = 0, width = 64, height = 32 ),
        EntityType.ON_OFF_SWITCH: SvgViewBox( x = 0, y = 0, width = 44, height = 64 ),
        EntityType.OPEN_CLOSE_SENSOR: SvgViewBox( x = 0, y = 0, width = 64, height = 50 ),
        EntityType.POOL_PUMP: SvgViewBox( x = 0, y = 0, width = 64, height = 48 ),
        EntityType.PUMP: SvgViewBox( x = 0, y = 0, width = 64, height = 45 ),
        EntityType.FREEZER: SvgViewBox( x = 0, y = 0, width = 48, height = 64 ),
        EntityType.REFRIGERATOR: SvgViewBox( x = 0, y = 0, width = 48, height = 64 ),
        EntityType.SERVER: SvgViewBox( x = 0, y = 0, width = 45, height = 64 ),
        EntityType.SINK: SvgViewBox( x = 0, y = 0, width = 64, height = 50 ),
        EntityType.SPRINKLER_HEAD: SvgViewBox( x = 0, y = 0, width = 64, height = 44 ),
        EntityType.SKYLIGHT: SvgViewBox( x = 0, y = 0, width = 57, height = 64 ),
        EntityType.TELEVISION: SvgViewBox( x = 0, y = 0, width = 64, height = 48 ),
        EntityType.THERMOMETER: SvgViewBox( x = 0, y = 0, width = 27, height = 64 ),
        EntityType.THERMOSTAT: SvgViewBox( x = 0, y = 0, width = 64, height = 44 ),
        EntityType.TOILET: SvgViewBox( x = 0, y = 0, width = 48, height = 64 ),
        EntityType.WALL_SWITCH: SvgViewBox( x = 0, y = 0, width = 42, height = 64 ),
        EntityType.WATER_FILTER: SvgViewBox( x = 0, y = 0, width = 48, height = 64 ),
        EntityType.WATER_HEATER: SvgViewBox( x = 0, y = 0, width = 38, height = 64 ),
        EntityType.WATER_METER: SvgViewBox( x = 0, y = 0, width = 64, height = 43 ),
    }
    PathEntityTypeToSvgStatusStyle = {
        EntityType.LARGE_APPLIANCE: Appliance,
        EntityType.AREA: Area,
        EntityType.CONTROL_WIRE: ControlWire,
        EntityType.DOOR: Door,
        EntityType.DRAINAGE_PIPE: Pipe,
        EntityType.ELECTRIC_WIRE: ElectricWire,
        EntityType.FENCE: Fence,
        EntityType.FURNITURE: Furniture,
        EntityType.GARAGE_DOOR: GarageDoor,
        EntityType.GAS_LINE: GasLine,
        EntityType.GREENHOUSE: Greenhouse,
        EntityType.PIPE: Pipe,
        EntityType.SEWER_LINE: SewerLine,
        EntityType.SPEAKER_WIRE: SpeakerWire,
        EntityType.SPRINKLER_WIRE: ControlWire,
        EntityType.TELECOM_WIRE: TelecomWire,
        EntityType.WALL: Wall,
        EntityType.WATER_LINE: WaterLine,
        EntityType.WINDOW: Window,
    }

    # Per-EntityType initial-placement size factor. Opt-in: only entity
    # types whose intended layout size deviates from the default (1.0)
    # need entries here. The factor multiplies the base placement size
    # in PositionGeometry.default_icon_scale.
    #
    # This is layout-driven, not realism-driven — the goal is fitting
    # many items in a view with touch-friendly sizing and reducing
    # post-placement resizing labor. Smaller-than-default types are
    # ones a user is likely to place many of in a single view; larger-
    # than-default types are ones that anchor a view's visual layout.
    # Primary control surfaces (lights, switches) stay at the default
    # since they are interactive targets the user will exercise.
    EntityTypeToIconSizeFactor = {
        # Smaller (high-count or modest-importance items)
        EntityType.BAROMETER: 0.7,
        EntityType.CARBON_MONOXIDE_DETECTOR: 0.7,
        EntityType.CONSUMABLE: 0.7,
        EntityType.DOORBELL: 0.7,
        EntityType.DOOR_LOCK: 0.7,
        EntityType.ELECTRICAL_OUTLET: 0.7,
        EntityType.FIRE_EXTINGUISHER: 0.7,
        EntityType.GARBAGE_DISPOSAL: 0.7,
        EntityType.GAS_DETECTOR: 0.7,
        EntityType.HYGROMETER: 0.7,
        EntityType.LEAK_SENSOR: 0.7,
        EntityType.LIGHT_SENSOR: 0.7,
        EntityType.MOTION_SENSOR: 0.7,
        EntityType.OPEN_CLOSE_SENSOR: 0.7,
        EntityType.PRESENCE_SENSOR: 0.7,
        EntityType.RADON_DETECTOR: 0.7,
        EntityType.SMOKE_DETECTOR: 0.7,
        EntityType.SPEAKER: 0.7,
        EntityType.SPRINKLER_HEAD: 0.7,
        EntityType.THERMOMETER: 0.7,
        EntityType.WATER_SHUTOFF_VALVE: 0.7,

        # Larger (room-anchoring single items)
        EntityType.BATHTUB: 1.5,
        EntityType.FIREPLACE: 1.5,
        EntityType.HVAC_AIR_HANDLER: 1.5,
        EntityType.HVAC_CONDENSER: 1.5,
        EntityType.HVAC_FURNACE: 1.5,
        EntityType.REFRIGERATOR: 1.5,
        EntityType.TREE: 1.5,

        # Very large
        EntityType.AUTOMOBILE: 2.0,
    }

    @classmethod
    def get_svg_icon_viewbox( cls, entity_type : EntityType ) -> SvgViewBox:
        if entity_type in cls.EntityTypeToIconViewbox:
            return cls.EntityTypeToIconViewbox.get( entity_type )
        return ItemStyle.get_default_svg_icon_viewbox()

    @classmethod
    def get_icon_size_factor( cls, entity_type : EntityType ) -> float:
        return cls.EntityTypeToIconSizeFactor.get( entity_type, 1.0 )

    # Per-EntityType source-icon facing direction. Used at placement
    # time to give the auto-created Area delegate a triangular path
    # (apex near the principal, base extending along the icon's facing
    # direction) instead of the generic rectangle, so the delegate
    # visually reads as a coverage cone for the principal.
    #
    # Opt-in: entity types without an entry get no triangle treatment;
    # the delegate stays as the default rectangle.
    EntityTypeToIconDirection = {
        EntityType.CAMERA: EntityIconDirection.POINTS_RIGHT,
        EntityType.MOTION_SENSOR: EntityIconDirection.POINTS_DOWN,
        EntityType.PRESENCE_SENSOR: EntityIconDirection.POINTS_RIGHT,
    }

    @classmethod
    def get_icon_direction( cls, entity_type : EntityType ) -> 'EntityIconDirection':
        return cls.EntityTypeToIconDirection.get(
            entity_type, EntityIconDirection.UNKNOWN,
        )

    @classmethod
    def get_svg_icon_template_name( cls, entity_type : EntityType ) -> str:
        if entity_type in cls.EntityTypesWithIcons:
            return f'entity/svg/type.{entity_type}.svg'
        return ItemStyle.get_default_svg_icon_template_name()
    
    @classmethod
    def get_svg_path_status_style( cls, entity_type : EntityType ) -> SvgStatusStyle:
        if entity_type in cls.PathEntityTypeToSvgStatusStyle:
            return cls.PathEntityTypeToSvgStatusStyle.get( entity_type )
        return ItemStyle.get_default_svg_path_status_style()


class StatusStyle:

    DEFAULT_STATUS_VALUE = ''
    DEFAULT_STROKE_COLOR = '#a0a0a0'
    DEFAULT_STROKE_WIDTH = 2.0
    DEFAULT_STROKE_DASHARRAY = []
    DEFAULT_FILL_COLOR = 'white'
    DEFAULT_FILL_OPACITY = 0.0

    # These should match those in main.css
    STATUS_ACTIVE_COLOR = 'red'
    STATUS_RECENT_COLOR = 'orange'
    STATUS_PAST_COLOR = 'yellow'
    STATUS_OK_COLOR = 'green'
    STATUS_BAD_COLOR = 'red'
    STATUS_IDLE_COLOR = '#888888'
    
    MovementActive = SvgStatusStyle(
        status_value = 'active',
        stroke_color = STATUS_ACTIVE_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_ACTIVE_COLOR,
        fill_opacity = 0.5,
    )
    MovementRecent = SvgStatusStyle(
        status_value = 'recent',
        stroke_color = STATUS_RECENT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_RECENT_COLOR,
        fill_opacity = 0.5,
    )
    MovementPast = SvgStatusStyle(
        status_value = 'past',
        stroke_color = STATUS_PAST_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_PAST_COLOR,
        fill_opacity = 0.5,
    )
    MovementIdle = SvgStatusStyle(
        status_value = 'idle',
        stroke_color = STATUS_OK_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_OK_COLOR,
        fill_opacity = 0.15,
    )
    # Smoke alarm reuses the movement / open-close ``active`` /
    # ``recent`` / ``past`` / ``idle`` status_value vocabulary so
    # the existing g[status="…"] / div[status="…"] CSS rules
    # apply unchanged. The state-type-specific labeling lives in
    # the ``EntityStateValue`` enum, not the SVG status attribute.
    SmokeDetected = SvgStatusStyle(
        status_value = 'active',
        stroke_color = STATUS_ACTIVE_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_ACTIVE_COLOR,
        fill_opacity = 0.5,
    )
    SmokeRecent = SvgStatusStyle(
        status_value = 'recent',
        stroke_color = STATUS_RECENT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_RECENT_COLOR,
        fill_opacity = 0.5,
    )
    SmokePast = SvgStatusStyle(
        status_value = 'past',
        stroke_color = STATUS_PAST_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_PAST_COLOR,
        fill_opacity = 0.5,
    )
    SmokeClear = SvgStatusStyle(
        status_value = 'idle',
        stroke_color = STATUS_OK_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_OK_COLOR,
        fill_opacity = 0.15,
    )
    # Moisture (water-leak) decay parallels smoke — both are
    # property-damage events with operator-significant recent /
    # past visual reminders.
    MoistureDetected = SvgStatusStyle(
        status_value = 'active',
        stroke_color = STATUS_ACTIVE_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_ACTIVE_COLOR,
        fill_opacity = 0.5,
    )
    MoistureRecent = SvgStatusStyle(
        status_value = 'recent',
        stroke_color = STATUS_RECENT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_RECENT_COLOR,
        fill_opacity = 0.5,
    )
    MoisturePast = SvgStatusStyle(
        status_value = 'past',
        stroke_color = STATUS_PAST_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_PAST_COLOR,
        fill_opacity = 0.5,
    )
    MoistureClear = SvgStatusStyle(
        status_value = 'idle',
        stroke_color = STATUS_OK_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_OK_COLOR,
        fill_opacity = 0.15,
    )
    # Carbon monoxide and combustible-gas decay parallel smoke —
    # life-safety events warrant a lingering visual reminder.
    CoDetected = SvgStatusStyle(
        status_value = 'active',
        stroke_color = STATUS_ACTIVE_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_ACTIVE_COLOR,
        fill_opacity = 0.5,
    )
    CoRecent = SvgStatusStyle(
        status_value = 'recent',
        stroke_color = STATUS_RECENT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_RECENT_COLOR,
        fill_opacity = 0.5,
    )
    CoPast = SvgStatusStyle(
        status_value = 'past',
        stroke_color = STATUS_PAST_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_PAST_COLOR,
        fill_opacity = 0.5,
    )
    CoClear = SvgStatusStyle(
        status_value = 'idle',
        stroke_color = STATUS_OK_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_OK_COLOR,
        fill_opacity = 0.15,
    )
    GasDetected = SvgStatusStyle(
        status_value = 'active',
        stroke_color = STATUS_ACTIVE_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_ACTIVE_COLOR,
        fill_opacity = 0.5,
    )
    GasRecent = SvgStatusStyle(
        status_value = 'recent',
        stroke_color = STATUS_RECENT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_RECENT_COLOR,
        fill_opacity = 0.5,
    )
    GasPast = SvgStatusStyle(
        status_value = 'past',
        stroke_color = STATUS_PAST_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_PAST_COLOR,
        fill_opacity = 0.5,
    )
    GasClear = SvgStatusStyle(
        status_value = 'idle',
        stroke_color = STATUS_OK_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_OK_COLOR,
        fill_opacity = 0.15,
    )
    On = SvgStatusStyle(
        status_value = 'on',
        stroke_color = 'yellow',
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = 'yellow',
        fill_opacity = 0.5,
    )
    Off = SvgStatusStyle(
        status_value = 'off',
        stroke_color = STATUS_IDLE_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_IDLE_COLOR,
        fill_opacity = 0.5,
    )
    Open = SvgStatusStyle(
        status_value = 'open',
        stroke_color = STATUS_ACTIVE_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_ACTIVE_COLOR,
        fill_opacity = 0.5,
    )
    OpenRecent = SvgStatusStyle(
        status_value = 'recent',
        stroke_color = STATUS_RECENT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_RECENT_COLOR,
        fill_opacity = 0.5,
    )
    OpenPast = SvgStatusStyle(
        status_value = 'past',
        stroke_color = STATUS_PAST_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_PAST_COLOR,
        fill_opacity = 0.5,
    )
    # Partially-open spatial state for continuous-position covers.
    # Distinct from ``OpenRecent`` (temporal decay after a recent
    # open) so spatial and temporal semantics don't share a name,
    # even though the visual palette is intentionally aligned.
    OpenPartial = SvgStatusStyle(
        status_value = 'partial',
        stroke_color = STATUS_RECENT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_RECENT_COLOR,
        fill_opacity = 0.5,
    )
    Closed = SvgStatusStyle(
        status_value = 'closed',
        stroke_color = STATUS_IDLE_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_IDLE_COLOR,
        fill_opacity = 0.5,
    )
    Connected = SvgStatusStyle(
        status_value = 'connected',
        stroke_color = STATUS_OK_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_OK_COLOR,
        fill_opacity = 0.5,
    )
    Disconnected = SvgStatusStyle(
        status_value = 'disconnected',
        stroke_color = STATUS_BAD_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_BAD_COLOR,
        fill_opacity = 0.5,
    )
    High = SvgStatusStyle(
        status_value = 'high',
        stroke_color = STATUS_OK_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_OK_COLOR,
        fill_opacity = 0.5,
    )
    Low = SvgStatusStyle(
        status_value = 'low',
        stroke_color = STATUS_BAD_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_BAD_COLOR,
        fill_opacity = 0.5,
    )
    BatteryLow = SvgStatusStyle(
        status_value = 'low',
        stroke_color = STATUS_BAD_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_BAD_COLOR,
        fill_opacity = 0.5,
    )
    BatteryOk = SvgStatusStyle(
        status_value = 'ok',
        stroke_color = STATUS_OK_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_OK_COLOR,
        fill_opacity = 0.15,
    )

    # Temperature: a single absolute-temperature scale, bucketed into a
    # blue (cold) -> green (pleasant) -> orange/red (hot) ramp. One scale
    # serves both thermostats and outdoor thermometers because comfortable
    # indoor temperatures naturally land in the green band while only the
    # outdoors reaches the blue/red extremes — so the same reading always
    # gets the same color, no indoor/outdoor distinction needed. The
    # extremes also carry higher fill_opacity (more intense) than the
    # subtle pleasant band, reinforcing "how far from comfortable" at a
    # glance. Thresholds live in EntityStateDisplayData (in canonical °C);
    # these are just the finite palette the CSS rules key off.
    STATUS_TEMP_COLD_COLOR     = '#2c7fb8'   # blue
    STATUS_TEMP_COOL_COLOR     = '#74add1'   # light blue
    STATUS_TEMP_PLEASANT_COLOR = '#1a9850'   # green
    STATUS_TEMP_WARM_COLOR     = '#fdae61'   # orange
    STATUS_TEMP_HOT_COLOR      = '#d73027'   # red

    TemperatureCold = SvgStatusStyle(
        status_value = 'temperature_cold',
        stroke_color = STATUS_TEMP_COLD_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_TEMP_COLD_COLOR,
        fill_opacity = 0.5,
    )
    TemperatureCool = SvgStatusStyle(
        status_value = 'temperature_cool',
        stroke_color = STATUS_TEMP_COOL_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_TEMP_COOL_COLOR,
        fill_opacity = 0.35,
    )
    TemperaturePleasant = SvgStatusStyle(
        status_value = 'temperature_pleasant',
        stroke_color = STATUS_TEMP_PLEASANT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_TEMP_PLEASANT_COLOR,
        fill_opacity = 0.2,
    )
    TemperatureWarm = SvgStatusStyle(
        status_value = 'temperature_warm',
        stroke_color = STATUS_TEMP_WARM_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_TEMP_WARM_COLOR,
        fill_opacity = 0.35,
    )
    TemperatureHot = SvgStatusStyle(
        status_value = 'temperature_hot',
        stroke_color = STATUS_TEMP_HOT_COLOR,
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = STATUS_TEMP_HOT_COLOR,
        fill_opacity = 0.5,
    )

    @classmethod
    def default( cls, status_value : str = DEFAULT_STATUS_VALUE ):
        return SvgStatusStyle(
            status_value = status_value,
            stroke_color = cls.DEFAULT_STROKE_COLOR,
            stroke_width = cls.DEFAULT_STROKE_WIDTH,
            stroke_dasharray = cls.DEFAULT_STROKE_DASHARRAY,
            fill_color = cls.DEFAULT_FILL_COLOR,
            fill_opacity = cls.DEFAULT_FILL_OPACITY,
        )

    @classmethod
    def light_dimmer( cls, status_value_str : str ):
        try:
            status_value = int(status_value_str)
        except (TypeError, ValueError):
            status_value = 0
            
        opacity = status_value / 100.0
        if status_value < 15:
            new_value = 'off'
        elif status_value < 85:
            new_value = 'dim'
        else:
            new_value = 'on'
        
        return SvgStatusStyle(
            status_value = new_value,
            stroke_color = 'yellow',
            stroke_width = cls.DEFAULT_STROKE_WIDTH,
            stroke_dasharray = cls.DEFAULT_STROKE_DASHARRAY,
            fill_color = 'yellow',
            fill_opacity = opacity,
        )

    # Upper bound (exclusive, in canonical °C) for each temperature bucket,
    # paired with the style to use below that bound; the final entry is the
    # open-ended "hot" catch-all. Bounds are chosen so human-comfortable
    # readings (~19-24°C) land in the green "pleasant" band.
    TEMPERATURE_BUCKETS_CELSIUS = [
        ( 5.0, TemperatureCold ),       # below freezing-ish / bitter
        ( 16.0, TemperatureCool ),      # chilly
        ( 25.0, TemperaturePleasant ),  # comfortable
        ( 31.0, TemperatureWarm ),      # warm
    ]

    @classmethod
    def temperature( cls, celsius : float ):
        for upper_bound_celsius, status_style in cls.TEMPERATURE_BUCKETS_CELSIUS:
            if celsius < upper_bound_celsius:
                return status_style
        return cls.TemperatureHot
