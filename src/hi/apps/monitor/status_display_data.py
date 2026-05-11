import hi.apps.common.datetimeproxy as datetimeproxy

from hi.apps.console.console_converter_helper import (
    ConsoleConverterHelper,
    DisplayValue,
)
from hi.apps.entity.enums import EntityStateType, EntityStateValue

from hi.hi_styles import StatusStyle

from .transient_models import EntityStateStatusData

    
class StatusDisplayData:

    RECENT_MOVEMENT_THRESHOLD_SECS = 90
    PAST_MOVEMENT_THRESHOLD_SECS = 180

    RECENT_OPEN_THRESHOLD_SECS = 90
    PAST_OPEN_THRESHOLD_SECS = 180

    # Smoke-alarm decay is longer than movement/open-close: a fire
    # event is rare and the recent / past status carries higher
    # operator significance, so the visual reminder lingers.
    RECENT_SMOKE_THRESHOLD_SECS = 600
    PAST_SMOKE_THRESHOLD_SECS = 1800
    
    def __init__( self, entity_state_status_data : EntityStateStatusData ):
        self._entity_state = entity_state_status_data.entity_state
        self._sensor_response_list = entity_state_status_data.sensor_response_list
        self._controller_data_list = entity_state_status_data.controller_data_list

        self._svg_status_style = self._get_svg_status_style()
        self._controller_data_value = self._get_controller_data_value()
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
    def controller_data_value(self):
        """The value to push to controller widgets (slider, checkbox,
        select, color picker) for this state via the polling
        controller-value map. None means this state has no
        controller (read-only sensor) and should be skipped.

        Distinct from the visual ``svg_status_style`` (CSS-driven
        bucketed status): the controller value is whatever the
        widget needs to faithfully reflect the latest state — a
        precise numeric for a slider, ``'on'``/``'off'`` for a
        checkbox, the discrete value for a select, a structured
        dict for a future color picker. Per-state-type reshaping
        can be added in ``_get_controller_data_value`` when a
        widget needs something other than the raw sensor value."""
        return self._controller_data_value
            
    @property
    def latest_sensor_value(self):
        if self.sensor_response_list:
            return self.sensor_response_list[0].value
        return None

    @property
    def latest_display_value(self) -> DisplayValue:
        """Latest sensor value translated to the user's preferred
        display unit (when the EntityState has unit-bearing data) —
        the polling-update analogue of the template-render boundary
        translation. Returns a ``DisplayValue`` with separated
        magnitude and unit_symbol so consumers can format per
        their need (slider's numeric ``value=`` uses ``.magnitude``;
        status text uses ``str(...)`` which combines both)."""
        return ConsoleConverterHelper.from_entity_state_value(
            entity_state_value = self.latest_sensor_value,
            entity_state = self._entity_state,
        )

    @property
    def latest_display_label(self) -> str:
        """Human-readable display string for the current sensor
        value — universal source of truth for the polling-refresh
        display text. Unit-bearing states get the combined
        magnitude+unit form (``"72.0°F"``); unit-less enum states
        get the labeled form (wire ``"smoke_detected"`` →
        ``"Smoke Detected"``); unit-less numeric / free-form
        values pass through. Matches what the template-render
        path produces via ``as_display_value`` / ``value_label``
        so the initial render and the polling refresh agree."""
        combined = str( self.latest_display_value )
        if not combined:
            return ''
        try:
            return EntityStateValue.from_name( combined ).label
        except ValueError:
            return combined

    def to_polling_update_dict(self) -> dict:
        """Build the per-EntityState row of ``entityStateStatusMap``.
        Carries the three UI update pieces: DOM attributes,
        controller widget state, and the human-readable display
        text."""
        display_value = self.latest_display_value
        display_dict = { 'text': self.latest_display_label }
        if display_value.unit_symbol:
            display_dict[ 'magnitude' ] = display_value.magnitude
            display_dict[ 'unit_symbol' ] = display_value.unit_symbol
        row = {
            'attributes': self.attribute_dict,
            'display_value': display_dict,
        }
        if self.controller_data_value is not None:
            row[ 'controller' ] = { 'value': self.controller_data_value }
        return row

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
    
    def _get_controller_data_value(self):
        """Compute the controller-shaped value for this state.

        Returns None when the state has no controller (purely
        read-only sensors like motion or open/close binary
        sensors), so the polling map skips them. Default for
        controllable states is the latest sensor value translated
        to the user's display unit when the EntityState has units —
        widgets rendered by ``continuous_slider_with_units.html``
        operate in display-unit space, so the polling refresh has
        to push values in that same unit. Unit-less states pass
        through unchanged so existing widget contracts (slider
        ``value=...``, checkbox ``checked=...``, select option
        ``selected=...``) are preserved.

        Per-state-type overrides go here when a widget needs a
        reshape — e.g., a future COLOR state would return a dict
        like ``{"hs": [60, 100]}`` for the color picker to consume.
        """
        if not self._controller_data_list:
            return None
        # Slider widget's numeric ``value=`` attribute needs just
        # the magnitude — combined-string would break the range
        # input's parsing.
        return self.latest_display_value.magnitude

    def _get_svg_status_style(self):

        if self.entity_state.entity_state_type == EntityStateType.MOVEMENT:
            return self._get_movement_status_style()
        
        if self.entity_state.entity_state_type == EntityStateType.PRESENCE:
            return self._get_presence_status_style()
            
        if self.entity_state.entity_state_type == EntityStateType.ON_OFF:
            return self._get_on_off_status_style()

        if self.entity_state.entity_state_type == EntityStateType.LIGHT_DIMMER:
            return self._get_light_dimmer_status_style()

        if self.entity_state.entity_state_type == EntityStateType.OPEN_CLOSE:
            return self._get_open_close_status_style()

        if self.entity_state.entity_state_type == EntityStateType.OPEN_CLOSE_POSITION:
            return self._get_open_close_position_status_style()

        if self.entity_state.entity_state_type == EntityStateType.POWER_LEVEL:
            return StatusStyle.light_dimmer( self.latest_sensor_value )
        
        if self.entity_state.entity_state_type == EntityStateType.CONNECTIVITY:
            return self._get_connectivity_status_style()
        
        if self.entity_state.entity_state_type == EntityStateType.HIGH_LOW:
            return self._get_high_low_status_style()

        if self.entity_state.entity_state_type == EntityStateType.SMOKE:
            return self._get_smoke_status_style()

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

        # Use the display-unit text so the polling refresh of the
        # status display matches what the initial server-side
        # template render produced (combined magnitude + unit
        # suffix for unit-bearing values, raw value otherwise).
        status_value = str( self.latest_display_value )
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
            return StatusStyle.MovementActive

        if self.penultimate_sensor_value == str(EntityStateValue.ACTIVE):
            presence_timedelta = datetimeproxy.now() - self.penultimate_sensor_timestamp
            if presence_timedelta.total_seconds() < self.RECENT_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementRecent

            elif presence_timedelta.total_seconds() < self.PAST_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementPast

        return StatusStyle.MovementIdle

    def _get_smoke_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.SMOKE_DETECTED):
            return StatusStyle.SmokeDetected

        if self.penultimate_sensor_value == str(EntityStateValue.SMOKE_DETECTED):
            smoke_timedelta = datetimeproxy.now() - self.penultimate_sensor_timestamp
            if smoke_timedelta.total_seconds() < self.RECENT_SMOKE_THRESHOLD_SECS:
                return StatusStyle.SmokeRecent

            elif smoke_timedelta.total_seconds() < self.PAST_SMOKE_THRESHOLD_SECS:
                return StatusStyle.SmokePast

        return StatusStyle.SmokeClear
        
    def _get_on_off_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.ON):
            return StatusStyle.On
        if self.latest_sensor_value == str(EntityStateValue.OFF):
            return StatusStyle.Off
        return None
        
    def _get_light_dimmer_status_style( self ):
        return StatusStyle.light_dimmer( self.latest_sensor_value )
        
    def _get_open_close_position_status_style( self ):
        # Discretize the continuous position into three visual
        # buckets, mirroring the dimmer pattern (off / dim / on).
        # A continuous color gradient would require per-value CSS
        # rules; three buckets keep the SVG palette finite while
        # still distinguishing closed, partially-open, and
        # fully-open states.
        try:
            position = int( float( self.latest_sensor_value ) )
        except ( TypeError, ValueError ):
            position = 0
        if position <= 0:
            return StatusStyle.Closed
        if position < 75:
            return StatusStyle.OpenPartial
        return StatusStyle.Open

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
    
