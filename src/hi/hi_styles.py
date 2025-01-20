from hi.apps.common.svg_models import SvgStatusStyle

from hi.apps.entity.enums import EntityType


class ItemStyle:

    @classmethod
    def get_default_svg_icon_template_name( cls ):
        return 'entity/svg/type.other.svg'

    
class EntityStyle:

    DEFAULT_STATUS_VALUE = ''
    DEFAULT_STROKE_COLOR = '#a0a0a0'
    DEFAULT_STROKE_WIDTH = 4.0
    DEFAULT_STROKE_DASHARRAY = []
    DEFAULT_FILL_COLOR = 'white'
    DEFAULT_FILL_OPACITY = 0.0

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
        EntityType.AUDIO_RECEIVER,
        EntityType.AUTOMOBILE,
        EntityType.BAROMETER,
        EntityType.CAMERA,
        EntityType.CLOTHES_DRYER,
        EntityType.CLOTHES_WASHER,
        EntityType.COMPUTER,
        EntityType.CONSUMABLE,
        EntityType.COOKTOP,
        EntityType.ELECTRIC_PANEL,
        EntityType.LIGHT,
    }
    EntityTypeClosedPaths = {
        EntityType.APPLIANCE,
        EntityType.AREA,
        EntityType.DOOR,
        EntityType.FURNITURE,
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
    def get_svg_icon_template_name( cls, entity_type : EntityType ):
        if entity_type in cls.EntityTypesWithIcons:
            return f'entity/svg/type.{entity_type}.svg'
        return ItemStyle.get_default_svg_icon_template_name()
    
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
        stroke_color = 'green',
        stroke_width = DEFAULT_STROKE_WIDTH,
        stroke_dasharray = DEFAULT_STROKE_DASHARRAY,
        fill_color = 'green',
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
