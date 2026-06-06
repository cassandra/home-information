"""Display-level projections of raw monitor data.

The raw classes ``EntityStateStatusData`` and ``EntityStatusData`` (in
``status_data``) are pure data containers — cheap to construct,
free of display-format work. Templates and other rendering call sites
go through the wrapping ``EntityStateDisplayData`` /
``EntityDisplayData`` here, which add display-ready accessors (unit
conversion, formatted labels, SVG status styles, role-keyed lookup,
etc.). Manager produces raw; views project."""

from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
from typing import Dict, List, Optional, Set

import hi.apps.common.datetimeproxy as datetimeproxy

from hi.apps.common.svg_models import SvgIconItem
from hi.apps.console.console_converter_helper import (
    ConsoleConverterHelper,
    DisplayValue,
)
from hi.apps.entity.entity_state_role_order import ENTITY_STATUS_VIEW_ORDERING
from hi.apps.entity.enums import EntityStateRole, EntityStateType, EntityStateValue
from hi.apps.entity.models import Entity
from hi.apps.sense.transient_models import SensorResponse

from hi.hi_styles import StatusStyle
from hi.units import UnitQuantity

from .enums import EntityDisplayCategory
from .status_data import EntityStateStatusData, EntityStatusData


@dataclass(frozen=True)
class StateValueEntry:
    """A single converted entry from the recent state-value cache —
    a display-ready label paired with the timestamp the value was
    recorded. The label has already been through the same
    ``ConsoleConverterHelper`` pipeline as ``latest_display_label``,
    so templates render entries with the user's preferred unit
    without per-entry conversion logic."""
    display_label : str
    timestamp     : datetime


@dataclass(frozen=True)
class RecentStateValueSummary:
    """Cached recent state-value history for a single EntityState,
    surfaced to panel templates. The list is ``SensorResponseManager``'s
    in-cache window (up to 5 entries, newest-first, already deduped
    by value change), with each value converted to its display form.

    Bounded by cache size and cache lifetime: a non-empty summary
    represents only what is currently cached, not a claim about
    full history. Panels that need "no events in window" semantics
    should phrase UI accordingly — the framework makes no
    completeness claims and does not query the DB."""

    entries : List[ StateValueEntry ]

    @property
    def latest(self) -> Optional[ StateValueEntry ]:
        return self.entries[0] if self.entries else None

    @property
    def penultimate(self) -> Optional[ StateValueEntry ]:
        return self.entries[1] if len( self.entries ) > 1 else None


class EntityStateDisplayData:

    RECENT_MOVEMENT_THRESHOLD_SECS = 90
    PAST_MOVEMENT_THRESHOLD_SECS = 180

    RECENT_OPEN_THRESHOLD_SECS = 90
    PAST_OPEN_THRESHOLD_SECS = 180

    # Smoke-alarm decay is longer than movement/open-close: a fire
    # event is rare and the recent / past status carries higher
    # operator significance, so the visual reminder lingers.
    RECENT_SMOKE_THRESHOLD_SECS = 600
    PAST_SMOKE_THRESHOLD_SECS = 1800

    # Water-leak decay matches smoke — property-damage events
    # warrant a long visual reminder so the operator can act
    # on a recent leak even after the sensor clears.
    RECENT_MOISTURE_THRESHOLD_SECS = 600
    PAST_MOISTURE_THRESHOLD_SECS = 1800

    # Carbon-monoxide and combustible-gas decay matches smoke —
    # life-safety events warrant a long visual reminder so the
    # operator sees the recent event even after the sensor clears.
    RECENT_CO_THRESHOLD_SECS = 600
    PAST_CO_THRESHOLD_SECS = 1800
    RECENT_GAS_THRESHOLD_SECS = 600
    PAST_GAS_THRESHOLD_SECS = 1800
    
    def __init__( self, entity_state_status_data : EntityStateStatusData ):
        self._raw = entity_state_status_data
        self._entity_state = entity_state_status_data.entity_state
        self._sensor_response_list = entity_state_status_data.sensor_response_list
        self._controller_data_list = entity_state_status_data.controller_data_list

        # Compute once at init — every downstream consumer
        # (svg_status_style fallback, controller_data_value,
        # latest_display_label, to_polling_update_dict) reads
        # this through the property, so the ConsoleConverterHelper
        # lookup runs only once per instance.
        self._latest_display_value = ConsoleConverterHelper.from_entity_state_value(
            entity_state_value = self.latest_sensor_value,
            entity_state = self._entity_state,
        )
        self._svg_status_style = self._get_svg_status_style()
        self._controller_data_value = self._get_controller_data_value()
        return

    @classmethod
    def for_value( cls, entity_state, value ) -> 'EntityStateDisplayData':
        """Build a display projection for a single discrete value (e.g. a
        historical reading) so callers color it through the SAME status
        dispatch as the live display, rather than re-deriving the status
        token from the raw value. No time-decay is applied — a lone value
        has no penultimate to decay from — so the result reflects the
        value's own bucket/token (e.g. a TEMPERATURE reading's color band,
        a BATTERY level's low/ok)."""
        synthetic_response = SensorResponse(
            integration_key = None,
            value = None if value is None else str( value ),
            timestamp = datetimeproxy.now(),
        )
        status_data = EntityStateStatusData(
            entity_state = entity_state,
            sensor_response_list = [ synthetic_response ],
            controller_data_list = [],
        )
        return cls( status_data )

    def __getattr__( self, name ):
        # Fall through to the wrapped raw data for any accessor not
        # defined here (e.g. ``latest_sensor_response``, ``has_sensor``,
        # ``has_controller``). Lets mainline templates that take a raw
        # ``EntityStateStatusData`` also accept this display wrapper
        # without per-template breakage. Properties defined on this
        # class take precedence — ``__getattr__`` only fires for misses.
        if name.startswith( '_' ):
            raise AttributeError( name )
        return getattr( self._raw, name )

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
    def latest_sensor_timestamp(self):
        # Responses are deduplicated by value change upstream, so the
        # latest response is the most recent *transition*. In the decay
        # handlers this branch is only reached once the entity has left
        # the value of interest, making this timestamp the moment that
        # event ENDED — the correct anchor for the recent/past decay
        # window (independent of how long the event lasted).
        if self.sensor_response_list:
            return self.sensor_response_list[0].timestamp
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
        return self._latest_display_value

    @property
    def latest_display_label(self) -> str:
        """Human-readable display string for the current sensor
        value — universal source of truth for the polling-refresh
        display text. Unit-bearing states get the combined
        magnitude+unit form (``"72.0°F"``); other values resolve
        through ``EntityStateValue.to_display_label`` (enum label,
        humanized free-form, or numeric pass-through)."""
        return self._display_label_for_display_value( self.latest_display_value )

    def _display_label_for_value(self, sensor_value) -> str:
        """Convert one raw sensor value into its display label via
        the same pipeline as ``latest_display_label``. Shared so
        per-entry conversion in ``recent_state_value_summary``
        produces labels indistinguishable from the latest-only
        path."""
        display_value = ConsoleConverterHelper.from_entity_state_value(
            entity_state_value = sensor_value,
            entity_state = self._entity_state,
        )
        return self._display_label_for_display_value( display_value )

    @staticmethod
    def _display_label_for_display_value(display_value: DisplayValue) -> str:
        return EntityStateValue.to_display_label( str( display_value ) )

    @cached_property
    def recent_state_value_summary(self) -> Optional[ RecentStateValueSummary ]:
        """Cached recent state-value history (up to 5 entries,
        newest-first), each converted to its display label. Returns
        ``None`` when the sensor response cache is empty. See
        ``RecentStateValueSummary`` for the contract — the framework
        makes no claims about completeness, no DB query is performed,
        and these values are not included in the polling-update
        payload (panels see them only at server-side render)."""
        if not self._sensor_response_list:
            return None
        entries = [
            StateValueEntry(
                display_label = self._display_label_for_value( r.value ),
                timestamp     = r.timestamp,
            )
            for r in self._sensor_response_list
        ]
        return RecentStateValueSummary( entries = entries )

    def to_polling_update_dict(self) -> dict:
        """Build the per-EntityState row of ``entityStateStatusMap``.

        Shape consumed by the JS dispatcher; each top-level key feeds
        one element-level declaration:

        - ``status``    → for ``[data-status]``    (singular status
                          attribute push, e.g., panel root driving
                          ``[status="..."]`` CSS)
        - ``controller``→ for ``[data-controller-value]`` (form value
                          push to sliders / checkboxes / selects)
        - ``display``   → for ``[data-display-text]`` /
                          ``[data-display-magnitude]`` /
                          ``[data-display-unit]``
        - ``svg_style`` → for ``[data-svg-style]`` (bundled SVG
                          attribute push: status, stroke, fill, etc.,
                          for LocationView icon and path elements)

        ``status`` and ``svg_style.status`` carry the same value;
        consumers pick the bundle that matches their opt-in. Fields
        are present only when meaningful — sensor-only states omit
        ``controller``; unit-less states omit
        ``display.magnitude``/``display.unit``; states with no SVG
        styling omit ``svg_style``."""
        svg_style_dict = self.attribute_dict       # may be {} for unrecognized values
        display_value = self.latest_display_value
        display_dict = { 'text': self.latest_display_label }
        if display_value.unit_symbol:
            display_dict[ 'magnitude' ] = display_value.magnitude
            display_dict[ 'unit' ] = display_value.unit_symbol
        row = { 'display': display_dict }
        if svg_style_dict:
            row[ 'svg_style' ] = svg_style_dict
            if 'status' in svg_style_dict:
                row[ 'status' ] = svg_style_dict[ 'status' ]
        if self.controller_data_value is not None:
            row[ 'controller' ] = { 'value': self.controller_data_value }
        return row

    @property
    def penultimate_sensor_value(self):
        if len(self.sensor_response_list) > 1:
            return self.sensor_response_list[1].value
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

        if self.entity_state.entity_state_type == EntityStateType.OBJECT_PRESENCE:
            return self._get_object_presence_status_style()

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

        if self.entity_state.entity_state_type == EntityStateType.MOISTURE:
            return self._get_moisture_status_style()

        if self.entity_state.entity_state_type == EntityStateType.CO:
            return self._get_co_status_style()

        if self.entity_state.entity_state_type == EntityStateType.GAS:
            return self._get_gas_status_style()

        if self.entity_state.entity_state_type == EntityStateType.BATTERY_LEVEL:
            return self._get_battery_level_status_style()

        if self.entity_state.entity_state_type == EntityStateType.TEMPERATURE:
            return self._get_temperature_status_style()

        # TODO: These should map the latest value into a continuous range of colors/opacity
        #
        # EntityStateType.AIR_PRESSURE
        # EntityStateType.BANDWIDTH_USAGE
        # EntityStateType.ELECTRIC_USAGE
        # EntityStateType.HUMIDITY
        # EntityStateType.LIGHT_LEVEL
        # EntityStateType.MOISTURE
        # EntityStateType.SOUND_LEVEL
        # EntityStateType.WATER_FLOW
        # EntityStateType.WIND_SPEED

        return self._get_default_status_style()

    def _get_default_status_style( self ):
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
            movement_timedelta = datetimeproxy.now() - self.latest_sensor_timestamp
            if movement_timedelta.total_seconds() < self.RECENT_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementRecent

            elif movement_timedelta.total_seconds() < self.PAST_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementPast

        return StatusStyle.MovementIdle
        
    def _get_presence_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.ACTIVE):
            return StatusStyle.MovementActive

        if self.penultimate_sensor_value == str(EntityStateValue.ACTIVE):
            presence_timedelta = datetimeproxy.now() - self.latest_sensor_timestamp
            if presence_timedelta.total_seconds() < self.RECENT_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementRecent

            elif presence_timedelta.total_seconds() < self.PAST_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementPast

        return StatusStyle.MovementIdle

    def _get_object_presence_status_style( self ):
        # OBJECT_PRESENCE collapses onto the Movement Active/Recent/
        # Past/Idle vocabulary: any non-OBJECT_NONE value is treated
        # as "active" (detection happening). Same decay thresholds as
        # MOVEMENT so the visual treatment is uniform across both
        # state types — see the StatusStyle.Movement* status_values
        # and the CSS rules keyed off them.
        object_none_value = str(EntityStateValue.OBJECT_NONE)

        if self.latest_sensor_value and self.latest_sensor_value != object_none_value:
            return StatusStyle.MovementActive

        if ( self.penultimate_sensor_value
             and self.penultimate_sensor_value != object_none_value ):
            object_timedelta = datetimeproxy.now() - self.latest_sensor_timestamp
            if object_timedelta.total_seconds() < self.RECENT_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementRecent

            elif object_timedelta.total_seconds() < self.PAST_MOVEMENT_THRESHOLD_SECS:
                return StatusStyle.MovementPast

        return StatusStyle.MovementIdle

    def _get_smoke_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.SMOKE_DETECTED):
            return StatusStyle.SmokeDetected

        if self.penultimate_sensor_value == str(EntityStateValue.SMOKE_DETECTED):
            smoke_timedelta = datetimeproxy.now() - self.latest_sensor_timestamp
            if smoke_timedelta.total_seconds() < self.RECENT_SMOKE_THRESHOLD_SECS:
                return StatusStyle.SmokeRecent

            elif smoke_timedelta.total_seconds() < self.PAST_SMOKE_THRESHOLD_SECS:
                return StatusStyle.SmokePast

        return StatusStyle.SmokeClear

    def _get_moisture_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.MOISTURE_DETECTED):
            return StatusStyle.MoistureDetected

        if self.penultimate_sensor_value == str(EntityStateValue.MOISTURE_DETECTED):
            moisture_timedelta = datetimeproxy.now() - self.latest_sensor_timestamp
            if moisture_timedelta.total_seconds() < self.RECENT_MOISTURE_THRESHOLD_SECS:
                return StatusStyle.MoistureRecent

            elif moisture_timedelta.total_seconds() < self.PAST_MOISTURE_THRESHOLD_SECS:
                return StatusStyle.MoisturePast

        return StatusStyle.MoistureClear

    def _get_co_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.CO_DETECTED):
            return StatusStyle.CoDetected

        if self.penultimate_sensor_value == str(EntityStateValue.CO_DETECTED):
            co_timedelta = datetimeproxy.now() - self.latest_sensor_timestamp
            if co_timedelta.total_seconds() < self.RECENT_CO_THRESHOLD_SECS:
                return StatusStyle.CoRecent

            elif co_timedelta.total_seconds() < self.PAST_CO_THRESHOLD_SECS:
                return StatusStyle.CoPast

        return StatusStyle.CoClear

    def _get_gas_status_style( self ):

        if self.latest_sensor_value == str(EntityStateValue.GAS_DETECTED):
            return StatusStyle.GasDetected

        if self.penultimate_sensor_value == str(EntityStateValue.GAS_DETECTED):
            gas_timedelta = datetimeproxy.now() - self.latest_sensor_timestamp
            if gas_timedelta.total_seconds() < self.RECENT_GAS_THRESHOLD_SECS:
                return StatusStyle.GasRecent

            elif gas_timedelta.total_seconds() < self.PAST_GAS_THRESHOLD_SECS:
                return StatusStyle.GasPast

        return StatusStyle.GasClear

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
            open_timedelta = datetimeproxy.now() - self.latest_sensor_timestamp
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

    # Battery percentages below this threshold are flagged ``low``;
    # otherwise ``ok``. The token surfaces via the standard polling
    # pipeline so any panel that opts in via ``data-status`` on a
    # battery-bound element can react with CSS rules.
    BATTERY_LOW_THRESHOLD_PCT = 20

    def _get_battery_level_status_style( self ):
        try:
            magnitude = float( self.latest_sensor_value )
        except (TypeError, ValueError):
            return StatusStyle.BatteryOk
        if magnitude < self.BATTERY_LOW_THRESHOLD_PCT:
            return StatusStyle.BatteryLow
        return StatusStyle.BatteryOk

    def _get_temperature_status_style( self ):
        # Bucket on the absolute temperature (cold -> pleasant -> hot).
        # Normalize to the canonical °C first so the bucket thresholds are
        # unit-agnostic regardless of whether this state is stored in °F,
        # °C, etc. If the value or units can't be resolved, fall back to the
        # plain numeric status display.
        celsius = self._latest_temperature_celsius()
        if celsius is None:
            return self._get_default_status_style()
        return StatusStyle.temperature( celsius )

    def _latest_temperature_celsius( self ):
        """The latest sensor value converted to canonical °C using the
        EntityState's stored ``units``, or None when it can't be resolved
        (no value, no/unknown units, non-numeric)."""
        raw_value = self.latest_sensor_value
        units = self.entity_state.units
        if raw_value is None or not units:
            return None
        try:
            return UnitQuantity( float( raw_value ), units ).to( 'degC' ).magnitude
        except Exception:
            return None


@dataclass
class EntityDisplayData:
    """Display projection of an ``EntityStatusData``. Wraps the raw
    entity-level status data and exposes the accessors templates
    need: a role-keyed map of per-state display projections, an
    ordered list of the same, plus pass-through to the basic
    ``entity`` / ``entity_for_video`` / ``display_only_svg_icon_item``
    references. Constructed once per render at the view layer; each
    contained state is wrapped exactly once at construction time."""

    entity_status_data : EntityStatusData
    state_display_data_map : Dict[ int, 'EntityStateDisplayData' ] = field(
        init = False, repr = False,
    )

    def __post_init__(self):
        # Build each contained state's ``EntityStateDisplayData`` exactly
        # once. ``state_status_data_list`` and ``state_status_data_by_role``
        # below both project from this map, so the per-state construction
        # cost (the ConsoleConverterHelper lookup and the
        # _get_svg_status_style dispatch) is paid once per render even
        # when both projections are accessed.
        self.state_display_data_map = {
            d.entity_state.id: EntityStateDisplayData( d )
            for d in self.entity_status_data.entity_state_status_data_list
        }

    @property
    def entity(self) -> Entity:
        return self.entity_status_data.entity

    @property
    def entity_for_video(self) -> Optional[Entity]:
        return self.entity_status_data.entity_for_video

    @property
    def display_only_svg_icon_item(self) -> Optional[SvgIconItem]:
        return self.entity_status_data.display_only_svg_icon_item

    @property
    def display_category(self) -> EntityDisplayCategory:
        return self.entity_status_data.display_category

    @property
    def state_status_data_list(self) -> List['EntityStateDisplayData']:
        """Display-ordered list of per-state display projections,
        sorted by ``ENTITY_STATUS_VIEW_ORDERING`` for the entity's
        type. Each item wraps the corresponding raw
        ``EntityStateStatusData``."""
        ordered_raw = sorted(
            self.entity_status_data.entity_state_status_data_list,
            key = lambda d: ENTITY_STATUS_VIEW_ORDERING.sort_key(
                d.entity_state.entity_state_role,
                self.entity_status_data.entity.entity_type,
            ),
        )
        return [ self.state_display_data_map[ d.entity_state.id ] for d in ordered_raw ]

    @property
    def present_roles(self) -> Set[EntityStateRole]:
        return {
            d.entity_state.entity_state_role
            for d in self.entity_status_data.entity_state_status_data_list
        }

    def filter_to_roles( self, declared_roles: Set[EntityStateRole] ):
        """Project ``state_status_data_list`` and ``state_status_data_by_role``
        down to states whose role is in ``declared_roles``. Returns a tuple
        ``(state_list, by_role_dict)`` — the same shapes the unfiltered
        properties expose, just filtered."""
        state_list = [
            d for d in self.state_status_data_list
            if d.entity_state.entity_state_role in declared_roles
        ]
        by_role = {
            name: data
            for name, data in self.state_status_data_by_role.items()
            if data.entity_state.entity_state_role in declared_roles
        }
        return state_list, by_role

    @property
    def state_status_data_by_role(self) -> Dict[str, 'EntityStateDisplayData']:
        """Role-keyed lookup for panel templates that pull a
        specific state by semantic role. Keys are the lowercase
        ``EntityStateRole`` name. Values are
        ``EntityStateDisplayData`` so panel templates get the
        display-ready accessors directly."""
        return {
            d.entity_state.entity_state_role.name.lower(): self.state_display_data_map[ d.entity_state.id ]
            for d in self.entity_status_data.entity_state_status_data_list
        }

