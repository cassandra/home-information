import hi.apps.common.datetimeproxy as datetimeproxy

from hi.apps.entity.enums import EntityStateType, EntityStateValue

from hi.hi_styles import StatusStyle

from .transient_models import EntityStateStatusData

    
class StatusDisplayData:

    RECENT_MOVEMENT_THRESHOLD_SECS = 90
    PAST_MOVEMENT_THRESHOLD_SECS = 180
    
    RECENT_OPEN_THRESHOLD_SECS = 90
    PAST_OPEN_THRESHOLD_SECS = 180
    
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

        return StatusStyle.default( status_value = status_value )
    
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

        if self.penultimate_sensor_value == str(EntityStateValue.OPEN):
            open_timedelta = datetimeproxy.now() - self.penultimate_sensor_timestamp
            if open_timedelta.total_seconds() < self.RECENT_OPEN_THRESHOLD_SECS:
                return StatusStyle.OpenRecent

            elif open_timedelta.total_seconds() < self.PAST_OPEN_THRESHOLD_SECS:
                return StatusStyle.OpenPast

        return StatusStyle.Closed
        
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
    
