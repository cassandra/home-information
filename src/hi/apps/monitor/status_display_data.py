import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.svg_models import SvgStatusStyle

from hi.apps.entity.enums import EntityStateType, EntityStateValue

from .transient_models import EntityStateStatusData


class StatusStyle:

    DEFAULT_STATUS_VALUE = ''
    DEFAULT_STROKE_COLOR = '#40f040'
    DEFAULT_STROKE_WIDTH = 5.0
    DEFAULT_FILL_COLOR = 'white'
    DEFAULT_FILL_OPACITY = 0.0
    
    MovementActive = SvgStatusStyle(
        status_value = 'active',
        stroke_color = 'red',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'red',
        fill_opacity = 0.5,
    )
    MovementRecent = SvgStatusStyle(
        status_value = 'recent',
        stroke_color = 'orange',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'orange',
        fill_opacity = 0.5,
    )
    MovementPast = SvgStatusStyle(
        status_value = 'past',
        stroke_color = 'yellow',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'yellow',
        fill_opacity = 0.5,
    )
    MovementIdle = SvgStatusStyle(
        status_value = 'idle',
        stroke_color = '#888888',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'white',
        fill_opacity = 0.0,
    )
    On = SvgStatusStyle(
        status_value = 'on',
        stroke_color = 'green',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'green',
        fill_opacity = 0.5,
    )
    Off = SvgStatusStyle(
        status_value = 'off',
        stroke_color = '#888888',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = '#888888',
        fill_opacity = 0.5,
    )
    Open = SvgStatusStyle(
        status_value = 'open',
        stroke_color = 'green',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'green',
        fill_opacity = 0.5,
    )
    Closed = SvgStatusStyle(
        status_value = 'closed',
        stroke_color = '#888888',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = '#888888',
        fill_opacity = 0.5,
    )
    Connected = SvgStatusStyle(
        status_value = 'connected',
        stroke_color = 'green',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'green',
        fill_opacity = 0.5,
    )
    Disconnected = SvgStatusStyle(
        status_value = 'disconnected',
        stroke_color = 'red',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'red',
        fill_opacity = 0.5,
    )
    High = SvgStatusStyle(
        status_value = 'high',
        stroke_color = 'green',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'green',
        fill_opacity = 0.5,
    )
    Low = SvgStatusStyle(
        status_value = 'low',
        stroke_color = 'red',
        stroke_width = DEFAULT_STROKE_WIDTH,
        fill_color = 'red',
        fill_opacity = 0.5,
    )

    @classmethod
    def default(cls):
        return SvgStatusStyle(
            status_value = cls.DEFAULT_STATUS_VALUE,
            stroke_color = cls.DEFAULT_STROKE_COLOR,
            stroke_width = cls.DEFAULT_STROKE_WIDTH,
            fill_color = cls.DEFAULT_FILL_COLOR,
            fill_opacity = cls.DEFAULT_FILL_OPACITY,
        )

    
class StatusDisplayData:

    RECENT_MOVEMENT_THRESHOLD_SECS = 90
    PAST_MOVEMENT_THRESHOLD_SECS = 180
    
    def __init__( self, entity_state_status_data : EntityStateStatusData ):
        self._entity_state = entity_state_status_data.entity_state
        self._sensor_response_list = entity_state_status_data.sensor_response_list
        self._controller_data_list = entity_state_status_data.controller_data_list

        self._svg_status_style = self._get_svg_status_style()
        return

    @property
    def entity_state(self):
        return self._entity_state
    
    @property
    def sensor_response_list(self):
        return self._sensor_response_list
    
    @property
    def controller_data_list(self):
        return self._controller_data_list

    @property
    def svg_status_style(self):
        return self._svg_status_style

    @property
    def should_skip(self):
        return bool( self._svg_status_style is None )
    
    @property
    def css_class(self):
        return self.entity_state.css_class

    @property
    def attribute_dict(self):
        if self._svg_status_style:
            return self._svg_status_style.to_dict()
        return dict()
            
    @property
    def latest_sensor_value(self):
        if self.sensor_response_list:
            return self.sensor_response_list[0].value
        return None

    @property
    def penultimate_sensor_value(self):
        if len(self.sensor_response_list) > 1:
            return self.sensor_response_list[1].value
        return None
    
    @property
    def penultimate_sensor_timestamp(self):
        if len(self.sensor_response_list) > 1:
            return self.sensor_response_list[1].timestamp
        return None
    
    def _get_svg_status_style(self):
    
        if self.entity_state.entity_state_type == EntityStateType.MOVEMENT:
            return self._get_movement_status_style()
        
        if self.entity_state.entity_state_type == EntityStateType.PRESENCE:
            return self._get_presence_status_style()
            
        if self.entity_state.entity_state_type == EntityStateType.ON_OFF:
            return self._get_on_off_status_style()

        if self.entity_state.entity_state_type == EntityStateType.OPEN_CLOSE:
            return self._get_open_close_status_style()
        
        if self.entity_state.entity_state_type == EntityStateType.CONNECTIVITY:
            return self._get_connectivity_status_style()
        
        if self.entity_state.entity_state_type == EntityStateType.HIGH_LOW:
            return self._get_high_low_status_style()

        # TODO: These should map the latest value into a continuous range of colors/opacity
        #
        # EntityStateType.AIR_PRESSURE
        # EntityStateType.BANDWIDTH_USAGE
        # EntityStateType.ELECTRIC_USAGE
        # EntityStateType.HUMIDITY
        # EntityStateType.LIGHT_LEVEL
        # EntityStateType.MOISTURE
        # EntityStateType.SOUND_LEVEL
        # EntityStateType.TEMPERATURE
        # EntityStateType.WATER_FLOW
        # EntityStateType.WIND_SPEED

        status_value = self.latest_sensor_value
        if not status_value:
            status_value = StatusStyle.DEFAULT_STATUS_VALUE
            
        return SvgStatusStyle(
            status_value = status_value,
            stroke_color = StatusStyle.DEFAULT_STROKE_COLOR,
            stroke_width = StatusStyle.DEFAULT_STROKE_WIDTH,
            fill_color = StatusStyle.DEFAULT_FILL_COLOR,
            fill_opacity = StatusStyle.DEFAULT_FILL_OPACITY,
        )
    
    def _get_movement_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.ACTIVE):
            return StatusStyle.MovementActive

        if self.penultimate_sensor_value == str(EntityStateValue.ACTIVE):
            movement_timedelta = datetimeproxy.now() - self.penultimate_sensor_timestamp
            if movement_timedelta.total_seconds() < self.RECENT_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementRecent

            elif movement_timedelta.total_seconds() < self.PAST_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementPast

        return StatusStyle.MovementIdle
        
    def _get_presence_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.ACTIVE):
            return StatusStyle.PresenceActive

        if self.penultimate_sensor_value == str(EntityStateValue.ACTIVE):
            presence_timedelta = datetimeproxy.now() - self.penultimate_sensor_timestamp
            if presence_timedelta.total_seconds() < self.RECENT_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementRecent

            elif presence_timedelta.total_seconds() < self.PAST_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementPast

        return StatusStyle.MovementIdle
        
    def _get_on_off_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.ON):
            return StatusStyle.On
        if self.latest_sensor_value == str(EntityStateValue.OFF):
            return StatusStyle.Off
        return None
        
    def _get_open_close_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.OPEN):
            return StatusStyle.Open
        if self.latest_sensor_value == str(EntityStateValue.CLOSED):
            return StatusStyle.Closed
        return None
        
    def _get_connectivity_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.CONNECTED):
            return StatusStyle.Connected
        if self.latest_sensor_value == str(EntityStateValue.DISCONNECTED):
            return StatusStyle.Disconnected
        return None
        
    def _get_high_low_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.HIGH):
            return StatusStyle.High
        if self.latest_sensor_value == str(EntityStateValue.LOW):
            return StatusStyle.Low
        return None
    
