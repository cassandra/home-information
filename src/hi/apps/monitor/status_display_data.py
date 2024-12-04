import hi.apps.common.datetimeproxy as datetimeproxy
from dataclasses import dataclass

from hi.apps.entity.enums import EntityStateType
from hi.apps.sense.enums import SensorValue

from .transient_models import EntityStateStatusData


@dataclass
class SvgStatusStyle:
    
    status_value  : str
    stroke_color  : str
    stroke_width  : float
    fill_color    : str
    fill_opacity  : float

    def to_dict(self):
        return {
            'status': self.status_value,
            'stroke': self.stroke_color,
            'stroke-width': self.stroke_width,
            'fill': self.fill_color,
            'fill-opacity': self.fill_opacity,
        }

    
class StatusStyle:

    MovementActive = SvgStatusStyle(
        status_value = 'active',
        stroke_color = 'red',
        stroke_width = None,
        fill_color = 'red',
        fill_opacity = 0.5,
    )
    MovementRecent = SvgStatusStyle(
        status_value = 'recent',
        stroke_color = 'orange',
        stroke_width = None,
        fill_color = 'orange',
        fill_opacity = 0.5,
    )
    MovementPast = SvgStatusStyle(
        status_value = 'past',
        stroke_color = 'yellow',
        stroke_width = None,
        fill_color = 'yellow',
        fill_opacity = 0.5,
    )
    MovementIdle = SvgStatusStyle(
        status_value = 'idle',
        stroke_color = '#888888',
        stroke_width = None,
        fill_color = 'white',
        fill_opacity = 0.0,
    )
    On = SvgStatusStyle(
        status_value = 'on',
        stroke_color = 'green',
        stroke_width = None,
        fill_color = 'green',
        fill_opacity = 0.5,
    )
    Off = SvgStatusStyle(
        status_value = 'off',
        stroke_color = '#888888',
        stroke_width = None,
        fill_color = '#888888',
        fill_opacity = 0.5,
    )
    Open = SvgStatusStyle(
        status_value = 'open',
        stroke_color = 'green',
        stroke_width = None,
        fill_color = 'green',
        fill_opacity = 0.5,
    )
    Closed = SvgStatusStyle(
        status_value = 'closed',
        stroke_color = '#888888',
        stroke_width = None,
        fill_color = '#888888',
        fill_opacity = 0.5,
    )
    Connected = SvgStatusStyle(
        status_value = 'connected',
        stroke_color = 'green',
        stroke_width = None,
        fill_color = 'green',
        fill_opacity = 0.5,
    )
    Disconnected = SvgStatusStyle(
        status_value = 'disconnected',
        stroke_color = 'red',
        stroke_width = None,
        fill_color = 'red',
        fill_opacity = 0.5,
    )
    High = SvgStatusStyle(
        status_value = 'high',
        stroke_color = 'green',
        stroke_width = None,
        fill_color = 'green',
        fill_opacity = 0.5,
    )
    Low = SvgStatusStyle(
        status_value = 'low',
        stroke_color = 'red',
        stroke_width = None,
        fill_color = 'red',
        fill_opacity = 0.5,
    )

    
class StatusDisplayData:
    
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
    
        return SvgStatusStyle(
            status_value = self.latest_sensor_value,
            stroke_color = None,
            stroke_width = None,
            fill_color = None,
            fill_opacity = None,
        )
    
    def _get_movement_status_style( self ):

        if self.latest_sensor_value == str(SensorValue.ACTIVE):
            return StatusStyle.MovementActive

        if self.penultimate_sensor_value == str(SensorValue.ACTIVE):
            movement_timedelta = datetimeproxy.now() - self.penultimate_sensor_timestamp
            if movement_timedelta.seconds < 30:
                return StatusStyle.MovementRecent

            elif movement_timedelta.seconds < 60:
                return StatusStyle.MovementPast

        return StatusStyle.MovementIdle
        
    def _get_presence_status_style( self ):

        if self.latest_sensor_value == str(SensorValue.ACTIVE):
            return StatusStyle.PresenceActive

        if self.penultimate_sensor_value == str(SensorValue.ACTIVE):
            presence_timedelta = datetimeproxy.now() - self.penultimate_sensor_timestamp
            if presence_timedelta.seconds < 30:
                return StatusStyle.MovementRecent

            elif presence_timedelta.seconds < 60:
                return StatusStyle.MovementPast

        return StatusStyle.MovementIdle
        
    def _get_on_off_status_style( self ):

        if self.latest_sensor_value == str(SensorValue.ON):
            return StatusStyle.On
        if self.latest_sensor_value == str(SensorValue.OFF):
            return StatusStyle.Off
        return None
        
    def _get_open_close_status_style( self ):

        if self.latest_sensor_value == str(SensorValue.OPEN):
            return StatusStyle.Open
        if self.latest_sensor_value == str(SensorValue.CLOSED):
            return StatusStyle.Closed
        return None
        
    def _get_connectivity_status_style( self ):

        if self.latest_sensor_value == str(SensorValue.CONNECTED):
            return StatusStyle.Connected
        if self.latest_sensor_value == str(SensorValue.DISCONNECTED):
            return StatusStyle.Disconnected
        return None
        
    def _get_high_low_status_style( self ):

        if self.latest_sensor_value == str(SensorValue.HIGH):
            return StatusStyle.High
        if self.latest_sensor_value == str(SensorValue.LOW):
            return StatusStyle.Low
        return None
        
