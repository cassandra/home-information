from hi.apps.common.svg_models import SvgStatusStyle, SvgViewBox

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
            stroke_color = '#a0a0a0',
            stroke_width = 4.0,
            stroke_dasharray = [],
            fill_color = 'none',
            fill_opacity = 0.0,
        )

        
class EntityStyle:

    Appliance = SvgStatusStyle(
        status_value = '',
        stroke_color = '#0606a0',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#808080',
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
        stroke_color = '#4f3022',
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
    Furniture = SvgStatusStyle(
        status_value = '',
        stroke_color = '#0606a0',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#808080',
        fill_opacity = 1,
    )
    SewerLine = SvgStatusStyle(
        status_value = '',
        stroke_color = '#008000',
        stroke_width = 3,
        stroke_dasharray = [ 8, 4, 2, 4 ],
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
        stroke_color = '#0606a0',
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
        stroke_color = '#0606a0',
        stroke_width = 2,
        stroke_dasharray = [],
        fill_color = '#808080',
        fill_opacity = 1,
    )

    EntityTypesWithIcons = {
        # Default icon used if not in this map
        EntityType.ACCESS_POINT,
        EntityType.AUTOMOBILE,
        EntityType.AV_RECEIVER,
        EntityType.BAROMETER,
        EntityType.CAMERA,
        EntityType.CLOTHES_DRYER,
        EntityType.CLOTHES_WASHER,
        EntityType.COMPUTER,
        EntityType.CONSUMABLE,
        EntityType.COOKTOP,
        EntityType.DOOR_LOCK,
        EntityType.ELECTRICAL_OUTLET,
        EntityType.ELECTRICITY_METER,
        EntityType.ELECTRIC_PANEL,
        EntityType.FIREPLACE,
        EntityType.HEALTHCHECK,
        EntityType.HVAC_AIR_HANDLER,
        EntityType.HVAC_CONDENSER,
        EntityType.HVAC_FURNACE,
        EntityType.HVAC_MINI_SPLIT,
        EntityType.HUMIDIFIER,
        EntityType.HYGROMETER,
        EntityType.LIGHT,
        EntityType.LIGHT_SENSOR,
        EntityType.MODEM,
        EntityType.MOTION_SENSOR,
        EntityType.NETWORK_SWITCH,
        EntityType.OPEN_CLOSE_SENSOR,
        EntityType.OVEN,
        EntityType.PLANT,
        EntityType.POOL_EQUIPMENT,
        EntityType.PRESENCE_SENSOR,
        EntityType.REFRIGERATOR,
        EntityType.SHOWER,
        EntityType.SINK,
        EntityType.SERVICE,
        EntityType.SPEAKER,
        EntityType.SPRINKLER_CONTROLLER,
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
        EntityType.WALL_SWITCH,
        EntityType.WATER_HEATER,
        EntityType.WATER_METER,
        EntityType.WATER_SHUTOFF_VALVE,
        EntityType.WEATHER_STATION,
    }
    EntityTypeToIconViewbox = {
        # Default viewbox used if not in this map
        EntityType.AUTOMOBILE: SvgViewBox( x = 0, y = 0, width = 200, height = 300 ),
        EntityType.BAROMETER: SvgViewBox( x = 0, y = 0, width = 44, height = 64 ),
        EntityType.ELECTRICAL_OUTLET: SvgViewBox( x = 0, y = 0, width = 45, height = 64 ),
        EntityType.HVAC_AIR_HANDLER: SvgViewBox( x = 0, y = 0, width = 64, height = 44 ),
        EntityType.HUMIDIFIER: SvgViewBox( x = 0, y = 0, width = 44, height = 64 ),
        EntityType.MODEM: SvgViewBox( x = 0, y = 0, width = 37, height = 64 ),
        EntityType.MOTION_SENSOR: SvgViewBox( x = 0, y = 0, width = 42, height = 64 ),
        EntityType.NETWORK_SWITCH: SvgViewBox( x = 0, y = 0, width = 64, height = 32 ),
        EntityType.OPEN_CLOSE_SENSOR: SvgViewBox( x = 0, y = 0, width = 64, height = 50 ),
        EntityType.REFRIGERATOR: SvgViewBox( x = 0, y = 0, width = 48, height = 64 ),
        EntityType.SINK: SvgViewBox( x = 0, y = 0, width = 64, height = 50 ),
        EntityType.SPRINKLER_HEAD: SvgViewBox( x = 0, y = 0, width = 64, height = 44 ),
        EntityType.SPRINKLER_CONTROLLER: SvgViewBox( x = 0, y = 0, width = 42, height = 64 ),
        EntityType.TELEVISION: SvgViewBox( x = 0, y = 0, width = 64, height = 48 ),
        EntityType.THERMOMETER: SvgViewBox( x = 0, y = 0, width = 27, height = 64 ),
        EntityType.THERMOSTAT: SvgViewBox( x = 0, y = 0, width = 64, height = 44 ),
        EntityType.TOILET: SvgViewBox( x = 0, y = 0, width = 48, height = 64 ),
        EntityType.WALL_SWITCH: SvgViewBox( x = 0, y = 0, width = 42, height = 64 ),
        EntityType.WATER_HEATER: SvgViewBox( x = 0, y = 0, width = 38, height = 64 ),
        EntityType.WATER_METER: SvgViewBox( x = 0, y = 0, width = 64, height = 43 ),
    }
    EntityTypeClosedPaths = {
        EntityType.APPLIANCE,
        EntityType.AREA,
        EntityType.DOOR,
        EntityType.FURNITURE,
        EntityType.GREENHOUSE,
        EntityType.WALL,
        EntityType.WINDOW,
    }
    EntityTypeOpenPaths = {
        EntityType.CONTROL_WIRE,
        EntityType.ELECTRIC_WIRE,
        EntityType.SEWER_LINE,
        EntityType.SPRINKLER_WIRE,
        EntityType.TELECOM_WIRE,
        EntityType.WATER_LINE,
    }
    PathEntityTypeToSvgStatusStyle = {
        EntityType.APPLIANCE: Appliance,
        EntityType.AREA: Area,
        EntityType.CONTROL_WIRE: ControlWire,
        EntityType.DOOR: Door,
        EntityType.ELECTRIC_WIRE: ElectricWire,
        EntityType.FURNITURE: Furniture,
        EntityType.SEWER_LINE: SewerLine,
        EntityType.SPRINKLER_WIRE: ControlWire,
        EntityType.TELECOM_WIRE: TelecomWire,
        EntityType.WALL: Wall,
        EntityType.WATER_LINE: WaterLine,
        EntityType.WINDOW: Window,
    }

    @classmethod
    def get_svg_icon_viewbox( cls, entity_type : EntityType ):
        if entity_type in cls.EntityTypeToIconViewbox:
            return cls.EntityTypeToIconViewbox.get( entity_type )
        return ItemStyle.get_default_svg_icon_viewbox()
            
    @classmethod
    def get_svg_icon_template_name( cls, entity_type : EntityType ):
        if entity_type in cls.EntityTypesWithIcons:
            return f'entity/svg/type.{entity_type}.svg'
        return ItemStyle.get_default_svg_icon_template_name()
    
    @classmethod
    def get_svg_path_status_style( cls, entity_type : EntityType ):
        if entity_type in cls.PathEntityTypeToSvgStatusStyle:
            return cls.PathEntityTypeToSvgStatusStyle.get( entity_type )
        return ItemStyle.get_default_svg_path_status_style()
    
    
class StatusStyle:

    DEFAULT_STATUS_VALUE = ''
    DEFAULT_STROKE_COLOR = '#a0a0a0'
    DEFAULT_STROKE_WIDTH = 4.0
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
