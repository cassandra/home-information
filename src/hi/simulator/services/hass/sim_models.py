import base64
from dataclasses import dataclass
import os
import time
from typing import ClassVar, Dict, List, Tuple

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.utils import str_to_bool

from hi.simulator.base_models import SimEntityFields, SimState, SimEntityDefinition
from hi.simulator.enums import SimEntityType, SimStateType


@dataclass
class HassState( SimState ):
    """
    Base class for each HAss SimState which directly translated into one
    API status response item.
    """

    def __post_init__(self):
        self._context = {
            'id': self.generate_ksuid(),
            'parent_id': None,
            'user_id': None,
        }
        return

    @property
    def entity_name(self):
        return self.sim_entity_fields.name
        
    @property
    def entity_id(self):
        raise NotImplementedError('Subclasses must override this method.')
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        raise NotImplementedError('Subclasses must override this method.')
    
    @property
    def state(self):
        """
        Will be a derivitive of the SimState.value.  This will convert
        the internal, normalized EntityStateValue values into the
        external HAss-recognized state values.
        """       
        raise NotImplementedError('Subclasses must override this method.')
    
    def generate_ksuid(self):
        timestamp = int(time.time()).to_bytes(4, 'big')
        random_data = os.urandom(16)
        raw_ksuid = timestamp + random_data
        return base64.b64encode(raw_ksuid).decode('utf-8').replace('=', '').replace('/', '').replace('+', '')
        
    def to_api_dict(self):
        dummy_datetime_iso = datetimeproxy.now().isoformat()
        return {
            'attributes': self.attributes,
            'context': self._context,
            'entity_id': self.entity_id,
            'last_changed': dummy_datetime_iso,
            'last_reported': dummy_datetime_iso,
            'last_updated': dummy_datetime_iso,
            'state' : self.state,
        }

    
class HassBrightnessHelper:
    """Conversions between the simulator's stored brightness value
    (HA's 0-255 numeric string) and the two HA-shape outputs that
    light states emit: the entity-level ``state`` field
    (``'on'``/``'off'``) and the ``brightness`` attribute integer.
    Shared across HASS light state classes (Insteon dimmer, smart
    bulb, color smart bulb's brightness component)."""

    @staticmethod
    def value_to_state( value : str ) -> str:
        """Map a brightness value to the HA ``state`` field. HA
        reports ``state='on'`` whenever the light is producing any
        light, ``state='off'`` only when fully off."""
        try:
            numeric = int( float( value ) ) if value is not None else 0
        except ( TypeError, ValueError ):
            numeric = 0
        return 'on' if numeric > 0 else 'off'

    @staticmethod
    def value_to_attr( value : str ) -> int:
        """Map a brightness value to the integer ``brightness``
        attribute (1-255). Returns None when the bulb is off so
        callers can omit the attribute, matching HA's typical
        off-state shape."""
        try:
            numeric = int( float( value ) ) if value is not None else 0
        except ( TypeError, ValueError ):
            numeric = 0
        if numeric <= 0:
            return None
        return min( numeric, 255 )


@dataclass( frozen = True )
class HassInsteonSimEntityFields( SimEntityFields ):
    """ Base class for all HAss Insteon devices """

    insteon_address  : str  = None


@dataclass
class HassInsteonState( HassState ):
    """ Base class for all HAss Insteon device states """
    
    sim_entity_fields  : HassInsteonSimEntityFields
        
    @property
    def insteon_address(self):
        return self.sim_entity_fields.insteon_address
    
    @property
    def insteon_address_id_suffix(self):
        return self.insteon_address.replace( '.', '_' ).lower()
    
    @property
    def state(self):
        is_on = str_to_bool( self.value )
        if is_on:
            return "on"
        return "off"
    
    
@dataclass( frozen = True )
class HassInsteonLightSwitchFields( HassInsteonSimEntityFields ):
    pass

    
@dataclass
class HassInsteonLightSwitchState( HassInsteonState ):

    sim_entity_fields  : HassInsteonLightSwitchFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'switch'

    @property
    def name(self):
        return f'{self.entity_name} Switch'
    
    @property
    def entity_id(self):
        return 'switch.switchlinc_relay_%s' % self.insteon_address_id_suffix
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'friendly_name': self.entity_name,
            "icon": "mdi:lightbulb",
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }

    
@dataclass( frozen = True )
class HassInsteonDimmerLightSwitchFields( HassInsteonSimEntityFields ):
    pass

    
@dataclass
class HassInsteonDimmerLightLightState( HassInsteonState ):

    sim_entity_fields  : HassInsteonDimmerLightSwitchFields
    # CONTINUOUS so the operator can set arbitrary brightness via
    # the simulator's range slider. Value is a string-encoded int
    # in HA's 1-255 brightness range; 0 means off. Without this
    # change HI's _has_brightness_capability check failed (no
    # ``brightness`` in attributes) and the entity imported as
    # ON_OFF rather than LIGHT_DIMMER, leaving the existing
    # ``controller_light_dimmer.html`` slider unreachable for
    # HASS-imported dimmers.
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'light'
    value              : str                           = '255'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 255

    @property
    def name(self):
        return f'{self.entity_name} Light'

    @property
    def entity_id(self):
        return 'light.switchlinc_dimmer_%s' % self.insteon_address_id_suffix

    @property
    def state(self):
        return HassBrightnessHelper.value_to_state( self.value )

    @property
    def attributes(self) -> Dict[ str, str ]:
        attrs = {
            'friendly_name': self.entity_name,
            "icon": "mdi:lightbulb",
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
            "supported_color_modes": [ "brightness" ],
        }
        brightness = HassBrightnessHelper.value_to_attr( self.value )
        if brightness is not None:
            attrs[ "brightness" ] = brightness
            attrs[ "color_mode" ] = "brightness"
        return attrs

    
@dataclass( frozen = True )
class HassInsteonDualBandLightSwitchFields( HassInsteonLightSwitchFields ):
    pass

    
@dataclass
class HassInsteonDualBandLightSwitchState( HassInsteonLightSwitchState ):
    """Dual-band variant (can use powerline or RF) """

    sim_entity_fields  : HassInsteonDualBandLightSwitchFields

    @property
    def entity_id(self):
        return 'switch.switchlinc_relay_dual_band_%s' % self.insteon_address_id_suffix


@dataclass( frozen = True )
class HassInsteonMotionDetectorFields( HassInsteonSimEntityFields ):
    pass


@dataclass
class HassInsteonMotionDetectorMotionState( HassInsteonState ):

    sim_entity_fields  : HassInsteonMotionDetectorFields
    sim_state_type     : SimStateType                     = SimStateType.MOVEMENT
    sim_state_id       : str                              = 'motion'
    
    @property
    def name(self):
        return f'{self.entity_name} Motion'
        
    @property
    def entity_id(self):
        return 'binary_sensor.motion_sensor_%s_motion' % self.insteon_address_id_suffix
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            "device_class": "motion",
            'friendly_name': self.name,
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }

    
@dataclass
class HassInsteonMotionDetectorLightState( HassInsteonState ):

    sim_entity_fields  : HassInsteonMotionDetectorFields
    sim_state_type     : SimStateType                     = SimStateType.ON_OFF
    sim_state_id       : str                              = 'light'
    
    @property
    def name(self):
        return f'{self.entity_name} Light'
        
    @property
    def entity_id(self):
        return 'binary_sensor.motion_sensor_%s_light' % self.insteon_address_id_suffix
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            "device_class": "light",
            'friendly_name': self.name,
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }

    
@dataclass
class HassInsteonMotionDetectorBatteryState( HassInsteonState ):

    sim_entity_fields  : HassInsteonMotionDetectorFields
    sim_state_type     : SimStateType                     = SimStateType.DISCRETE
    sim_state_id       : str                              = 'battery'
    value              : str                              = 'High'

    @property
    def name(self):
        return f'{self.entity_name} Battery'

    @property
    def choices(self) -> List[ Tuple[ str, str ]]:
        return [
            ( 'Low'    , 'Low' ),
            ( 'High' , 'High' ),
        ]

    @property
    def entity_id(self):
        return 'binary_sensor.motion_sensor_%s_battery' % self.insteon_address_id_suffix

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            "device_class": "battery",
            'friendly_name': self.name,
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }

    @property
    def state(self):
        # HA convention for binary_sensor with device_class=battery:
        # "on" means the battery is low (problem signal), "off"
        # means it's healthy. Override the inherited str_to_bool
        # path so the DISCRETE Low/High UI choice maps to the
        # right API output instead of resolving both labels to
        # "off" via str_to_bool.
        return 'on' if self.value == 'Low' else 'off'


@dataclass( frozen = True )
class HassInsteonOpenCloseSensorFields( HassInsteonSimEntityFields ):
    pass


@dataclass
class HassInsteonOpenCloseSensorState( HassInsteonState ):

    sim_entity_fields  : HassInsteonOpenCloseSensorFields
    sim_state_type     : SimStateType                      = SimStateType.OPEN_CLOSE
    sim_state_id       : str                               = 'sensor'
    
    @property
    def entity_id(self):
        return 'binary_sensor.open_close_sensor_%s' % self.insteon_address_id_suffix
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            "device_class": "door",
            'friendly_name': self.entity_name,
            "icon": "mdi:door",
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }

    
@dataclass( frozen = True )
class HassInsteonOutletFields( HassInsteonSimEntityFields ):
    pass

    
@dataclass
class HassInsteonOutletState( HassInsteonState ):

    sim_entity_fields  : HassInsteonOutletFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'outlet'

    @property
    def name(self):
        return f'{self.entity_name} Outlet'
    
    @property
    def entity_id(self):
        return 'switch.outletlinc_relay_%s' % self.insteon_address_id_suffix
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'outlet',
            'friendly_name': self.entity_name,
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }

    
# --------------------------------------------------------------------------
# Non-Insteon HASS device variants
# --------------------------------------------------------------------------
#
# Smart bulbs (Hue-, Lifx-, Wyze-style) are dedicated lighting
# products HA exposes via the ``light`` domain with brightness and
# (for color bulbs) color attributes. They are not switches wired
# to fixtures, so they do NOT inherit from ``HassInsteonState`` —
# bulbs carry no Insteon address / group, and inheriting would
# leak those Insteon-flavored attributes into the API output and
# mask issues in HI's vendor-neutral attribute path.
#
# The simulator's data model is HI-centric: each runtime-mutable
# value HI sees as its own EntityState gets its own SimState here,
# with its own min/max range and slider in the simulator UI. Real
# HA, however, models a color bulb as ONE entity with multiple
# attributes — see ``api_composers.py`` for the per-device-type
# composer that collapses the multi-state HI shape to HA's flat-
# attribute shape on emit.


@dataclass( frozen = True )
class HassSmartBulbFields( SimEntityFields ):
    """A brightness-only smart bulb. No color attributes — that
    variant is ``HassColorSmartBulbFields`` below. One SimState
    per device, so this device uses the default API composer
    (one-state-per-HA-entity)."""
    pass


@dataclass
class HassSmartBulbState( HassState ):
    """Single CONTINUOUS brightness state in HA's 0-255 range.
    ``state`` is derived (``on`` when brightness > 0, else
    ``off``); ``brightness`` is omitted from attributes when off,
    matching HA's typical off-state shape."""

    sim_entity_fields  : HassSmartBulbFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'light'
    value              : str                           = '255'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 255

    @property
    def name(self):
        return f'{self.entity_name} Brightness'

    @property
    def entity_id(self):
        suffix = self.entity_name.lower().replace( ' ', '_' )
        return f'light.smart_bulb_{suffix}'

    @property
    def state(self):
        return HassBrightnessHelper.value_to_state( self.value )

    @property
    def attributes(self) -> Dict[ str, str ]:
        attrs = {
            'friendly_name': self.entity_name,
            'icon': 'mdi:lightbulb',
            'supported_color_modes': [ 'brightness' ],
        }
        brightness = HassBrightnessHelper.value_to_attr( self.value )
        if brightness is not None:
            attrs[ 'brightness' ] = brightness
            attrs[ 'color_mode' ] = 'brightness'
        return attrs


@dataclass( frozen = True )
class HassColorSmartBulbFields( SimEntityFields ):
    """A color smart bulb. Composed of multiple SimStates
    (brightness, hue, saturation, color temperature) collapsed
    into one HA entity at emit time by ``api_composers``."""
    pass


def _color_bulb_entity_id( name : str ) -> str:
    suffix = name.lower().replace( ' ', '_' )
    return f'light.color_bulb_{suffix}'


@dataclass
class HassColorSmartBulbBrightnessState( HassState ):
    """Brightness component of a color smart bulb (CONTINUOUS,
    0-255). Drives the HA entity's ``state`` (on/off) and the
    ``brightness`` attribute. Designated as the primary state in
    the color-bulb composer (its ``state`` field becomes the
    composed entity's ``state`` field)."""

    sim_entity_fields  : HassColorSmartBulbFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'brightness'
    value              : str                           = '255'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 255

    @property
    def name(self):
        return f'{self.entity_name} Brightness'

    @property
    def entity_id(self):
        return _color_bulb_entity_id( self.entity_name )

    @property
    def state(self):
        return HassBrightnessHelper.value_to_state( self.value )

    @property
    def attributes(self) -> Dict[ str, str ]:
        # The composer combines this state's contributions with
        # those of the other color-bulb states; we return only
        # this state's piece of the attribute dict.
        attrs = {
            'friendly_name': self.entity_name,
            'icon': 'mdi:lightbulb',
            'supported_color_modes': [ 'hs', 'color_temp', 'rgb' ],
        }
        brightness = HassBrightnessHelper.value_to_attr( self.value )
        if brightness is not None:
            attrs[ 'brightness' ] = brightness
        return attrs


@dataclass
class HassColorSmartBulbHueState( HassState ):
    """Hue component (CONTINUOUS, 0-360 degrees). Combined with
    the saturation state into ``hs_color: [hue, saturation]`` by
    the color-bulb composer."""

    sim_entity_fields  : HassColorSmartBulbFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'hue'
    value              : str                           = '60'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 360

    @property
    def name(self):
        return f'{self.entity_name} Hue'

    @property
    def entity_id(self):
        return _color_bulb_entity_id( self.entity_name )

    @property
    def state(self):
        # Composer ignores this state's ``state`` field; only the
        # primary (brightness) state's value drives the entity's
        # state. Returning a placeholder keeps the HassState
        # contract satisfied for any direct callers.
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        # Hue and saturation must compose into ``hs_color: [h, s]``;
        # neither alone has the full pair. Return the hue under a
        # private key the composer combines with the saturation
        # state's contribution into a single ``hs_color`` attribute.
        return { '_partial_hs_hue': float( self.value ) }


@dataclass
class HassColorSmartBulbSaturationState( HassState ):
    """Saturation component (CONTINUOUS, 0-100 percent). Pairs
    with the hue state to compose ``hs_color``."""

    sim_entity_fields  : HassColorSmartBulbFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'saturation'
    value              : str                           = '100'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def name(self):
        return f'{self.entity_name} Saturation'

    @property
    def entity_id(self):
        return _color_bulb_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return { '_partial_hs_saturation': float( self.value ) }


@dataclass
class HassColorSmartBulbColorTempState( HassState ):
    """Color temperature component (CONTINUOUS, 2000-6500 Kelvin
    — HA's typical light range, warm to cool white). Emits
    ``color_temp_kelvin`` directly; no composition needed."""

    sim_entity_fields  : HassColorSmartBulbFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'color_temp'
    value              : str                           = '4000'

    @property
    def min_value(self):
        return 2000

    @property
    def max_value(self):
        return 6500

    @property
    def name(self):
        return f'{self.entity_name} Color Temp'

    @property
    def entity_id(self):
        return _color_bulb_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return { 'color_temp_kelvin': int( float( self.value ) ) }


@dataclass
class HassColorSmartBulbColorModeState( HassState ):
    """Active color mode (DISCRETE). HA reports this as the
    ``color_mode`` attribute and derives it from whichever color
    attribute was most recently written; the simulator's service
    dispatcher mirrors that by writing this state when it sees
    ``hs_color`` or ``color_temp_kelvin`` on a service call. The
    simulator also exposes the dropdown directly so a tester can
    reach edge values (e.g., ``unknown``, ``rgbww``) without
    having to drive every mode through HI's controllers."""

    COLOR_MODE_CHOICES : ClassVar[ List[ Tuple[ str, str ] ] ] = [
        ( 'unknown', 'Unknown' ),
        ( 'onoff', 'On/Off' ),
        ( 'brightness', 'Brightness' ),
        ( 'color_temp', 'Color Temperature' ),
        ( 'hs', 'HS Color' ),
        ( 'rgb', 'RGB Color' ),
        ( 'rgbw', 'RGBW Color' ),
        ( 'rgbww', 'RGBWW Color' ),
        ( 'xy', 'XY Color' ),
        ( 'white', 'White' ),
    ]

    sim_entity_fields  : HassColorSmartBulbFields
    sim_state_type     : SimStateType                  = SimStateType.DISCRETE
    sim_state_id       : str                           = 'color_mode'
    value              : str                           = 'hs'

    @property
    def name(self):
        return f'{self.entity_name} Color Mode'

    @property
    def entity_id(self):
        return _color_bulb_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return self.COLOR_MODE_CHOICES

    @property
    def attributes(self) -> Dict[ str, str ]:
        # Composer reads this state's value as the entity-level
        # ``color_mode`` attribute; emit nothing per-state to
        # avoid duplicate keys when the composer merges.
        return {}


@dataclass( frozen = True )
class HassLockFields( SimEntityFields ):
    """A lock device. Single ON_OFF SimState whose value drives
    HA's domain-specific ``state`` strings (``'locked'`` /
    ``'unlocked'``)."""
    pass


def _lock_entity_id( name : str ) -> str:
    suffix = name.lower().replace( ' ', '_' )
    return f'lock.{suffix}'


@dataclass
class HassLockState( HassState ):
    """A lock's state. Internally ON_OFF (locked == on); the
    ``state`` property maps to HA's domain-specific
    ``'locked'`` / ``'unlocked'`` strings."""

    sim_entity_fields  : HassLockFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'lock'
    value              : str                           = 'on'

    @property
    def name(self):
        return f'{self.entity_name} Lock'

    @property
    def entity_id(self):
        return _lock_entity_id( self.entity_name )

    @property
    def state(self):
        return 'locked' if str_to_bool( self.value ) else 'unlocked'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'friendly_name': self.entity_name,
        }


@dataclass( frozen = True )
class HassGarageCoverFields( SimEntityFields ):
    """Garage door cover. Discrete open/closed; no position
    attribute (real garage doors are typically on/off)."""
    pass


def _cover_entity_id( name : str ) -> str:
    suffix = name.lower().replace( ' ', '_' )
    return f'cover.{suffix}'


@dataclass
class HassGarageCoverState( HassState ):
    """Internally ON_OFF (open == on); the ``state`` property
    maps to HA's cover-domain wire strings ``'open'`` /
    ``'closed'``."""

    sim_entity_fields  : HassGarageCoverFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'cover'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Cover'

    @property
    def entity_id(self):
        return _cover_entity_id( self.entity_name )

    @property
    def state(self):
        return 'open' if str_to_bool( self.value ) else 'closed'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'friendly_name': self.entity_name,
            'device_class': 'garage',
        }


@dataclass( frozen = True )
class HassGenericCoverFields( SimEntityFields ):
    """Generic cover with no device_class. Discrete
    open/closed, no position attribute. Exercises the
    converter's ``(cover, None, None)`` fall-through mapping
    so future cover device classes that aren't explicitly
    listed get tested by the same fixture path."""
    pass


@dataclass
class HassGenericCoverState( HassState ):
    """Internally ON_OFF (open == on); the ``state`` property
    maps to HA's cover-domain wire strings ``'open'`` /
    ``'closed'``. No ``device_class`` attribute is emitted."""

    sim_entity_fields  : HassGenericCoverFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'cover'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Cover'

    @property
    def entity_id(self):
        return _cover_entity_id( self.entity_name )

    @property
    def state(self):
        return 'open' if str_to_bool( self.value ) else 'closed'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'friendly_name': self.entity_name,
        }


@dataclass( frozen = True )
class HassWindowBlindCoverFields( SimEntityFields ):
    """Window blind cover with position. Single CONTINUOUS
    SimState (0-100 percent). The ``state`` property derives
    open/closed from the position; the ``current_position``
    attribute carries the numeric value."""
    pass


@dataclass
class HassWindowBlindCoverState( HassState ):
    sim_entity_fields  : HassWindowBlindCoverFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'position'
    value              : str                           = '0'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def name(self):
        return f'{self.entity_name} Position'

    @property
    def entity_id(self):
        return _cover_entity_id( self.entity_name )

    @property
    def state(self):
        try:
            position = int( float( self.value ) )
        except ( TypeError, ValueError ):
            position = 0
        return 'open' if position > 0 else 'closed'

    @property
    def attributes(self) -> Dict[ str, str ]:
        try:
            position = int( float( self.value ) )
        except ( TypeError, ValueError ):
            position = 0
        return {
            'friendly_name': self.entity_name,
            'device_class': 'blind',
            'current_position': position,
        }


HASS_SIM_ENTITY_DEFINITION_LIST = [
    SimEntityDefinition(
        class_label = 'Insteon Switch',
        sim_entity_type = SimEntityType.LIGHT,
        sim_entity_fields_class = HassInsteonLightSwitchFields,
        sim_state_class_list = [
            # HAss create duplicate states "switch" and "light" since a
            # switch may be use for a light or something else. We only need
            # one of these since there is only one underlying state.
            HassInsteonLightSwitchState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Insteon Light Switch (dimmer)',
        sim_entity_type = SimEntityType.LIGHT,
        sim_entity_fields_class = HassInsteonDimmerLightSwitchFields,
        sim_state_class_list = [
            HassInsteonDimmerLightLightState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Insteon Switch (dual band)',
        sim_entity_type = SimEntityType.LIGHT,
        sim_entity_fields_class = HassInsteonDualBandLightSwitchFields,
        sim_state_class_list = [
            # HAss create duplicate states "switch" and "light" since a
            # switch may be use for a light or something else. We only need
            # one of these since there is only one underlying state.
            HassInsteonDualBandLightSwitchState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Insteon Motion Detector',
        sim_entity_type = SimEntityType.MOTION_SENSOR,
        sim_entity_fields_class = HassInsteonMotionDetectorFields,
        sim_state_class_list = [
            HassInsteonMotionDetectorMotionState,
            HassInsteonMotionDetectorLightState,
            HassInsteonMotionDetectorBatteryState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Insteon Open/Close Detector',
        sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
        sim_entity_fields_class = HassInsteonOpenCloseSensorFields,
        sim_state_class_list = [
            HassInsteonOpenCloseSensorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Insteon Outlet',
        sim_entity_type = SimEntityType.ELECTRICAL_OUTLET,
        sim_entity_fields_class = HassInsteonOutletFields,
        sim_state_class_list = [
            HassInsteonOutletState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Smart Bulb (brightness)',
        sim_entity_type = SimEntityType.LIGHT,
        sim_entity_fields_class = HassSmartBulbFields,
        sim_state_class_list = [
            HassSmartBulbState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Smart Bulb (color)',
        sim_entity_type = SimEntityType.LIGHT,
        sim_entity_fields_class = HassColorSmartBulbFields,
        sim_state_class_list = [
            # Order matters: ``api_composers`` treats the first
            # state (brightness) as the primary, taking its
            # ``state`` field for the composed HA entity. The
            # other states only contribute attributes.
            HassColorSmartBulbBrightnessState,
            HassColorSmartBulbHueState,
            HassColorSmartBulbSaturationState,
            HassColorSmartBulbColorTempState,
            HassColorSmartBulbColorModeState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Lock',
        sim_entity_type = SimEntityType.DOOR_LOCK,
        sim_entity_fields_class = HassLockFields,
        sim_state_class_list = [
            HassLockState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Cover (garage)',
        sim_entity_type = SimEntityType.OPEN_CLOSE_ACTUATOR,
        sim_entity_fields_class = HassGarageCoverFields,
        sim_state_class_list = [
            HassGarageCoverState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Cover (window blind)',
        sim_entity_type = SimEntityType.OPEN_CLOSE_ACTUATOR,
        sim_entity_fields_class = HassWindowBlindCoverFields,
        sim_state_class_list = [
            HassWindowBlindCoverState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Cover (generic, no device_class)',
        sim_entity_type = SimEntityType.OPEN_CLOSE_ACTUATOR,
        sim_entity_fields_class = HassGenericCoverFields,
        sim_state_class_list = [
            HassGenericCoverState,
        ],
    ),
]
