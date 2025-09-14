from hi.apps.common.svg_models import SvgRadius, SvgStatusStyle, SvgViewBox

from hi.apps.collection.enums import CollectionType
from hi.apps.entity.enums import EntityType


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
        fill_color = '#e6f0fa',
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
        EntityType.ATTIC_STAIRS,
        EntityType.AUTOMOBILE,
        EntityType.AV_RECEIVER,
        EntityType.BAROMETER,
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
        EntityType.EXHAUST_FAN,
        EntityType.FIRE_EXTINGUISHER,
        EntityType.FIREPLACE,
        EntityType.GARBAGE_DISPOSAL,
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
        EntityType.LAWN_MOWER,
        EntityType.LEAF_BLOWER,
        EntityType.LIGHT,
        EntityType.LIGHT_SENSOR,
        EntityType.MICROWAVE_OVEN,
        EntityType.MODEM,
        EntityType.MOTION_SENSOR,
        EntityType.MOTOR,
        EntityType.NETWORK_SWITCH,
        EntityType.ON_OFF_SWITCH,
        EntityType.OPEN_CLOSE_SENSOR,
        EntityType.OVEN,
        EntityType.PLANT,
        EntityType.POOL_FILTER,
        EntityType.POWER_WASHER,
        EntityType.PRESENCE_SENSOR,
        EntityType.PRINTER,
        EntityType.PUMP,
        EntityType.RANGE_HOOD,
        EntityType.REFRIGERATOR,
        EntityType.SATELLITE_DISH,
        EntityType.SERVER,
        EntityType.SERVICE,
        EntityType.SHED,
        EntityType.SHOWER,
        EntityType.SINK,
        EntityType.SKYLIGHT,
        EntityType.SMOKE_DETECTOR,
        EntityType.SOLAR_PANEL,
        EntityType.SPEAKER,
        EntityType.SPRINKLER_HEAD,
        EntityType.SPRINKLER_VALVE,
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
        EntityType.WATER_HEATER,
        EntityType.WATER_METER,
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
        EntityType.PUMP: SvgViewBox( x = 0, y = 0, width = 64, height = 45 ),
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
        EntityType.WATER_HEATER: SvgViewBox( x = 0, y = 0, width = 38, height = 64 ),
        EntityType.WATER_METER: SvgViewBox( x = 0, y = 0, width = 64, height = 43 ),
    }
    PathEntityTypeToSvgStatusStyle = {
        EntityType.APPLIANCE: Appliance,
        EntityType.AREA: Area,
        EntityType.CONTROL_WIRE: ControlWire,
        EntityType.DOOR: Door,
        EntityType.ELECTRIC_WIRE: ElectricWire,
        EntityType.FENCE: Fence,
        EntityType.FURNITURE: Furniture,
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

    @classmethod
    def get_svg_icon_viewbox( cls, entity_type : EntityType ) -> SvgViewBox:
        if entity_type in cls.EntityTypeToIconViewbox:
            return cls.EntityTypeToIconViewbox.get( entity_type )
        return ItemStyle.get_default_svg_icon_viewbox()
            
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
