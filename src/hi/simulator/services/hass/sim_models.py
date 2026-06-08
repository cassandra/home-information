import base64
from dataclasses import dataclass, field
import hashlib
import os
import time
from typing import ClassVar, Dict, List, Tuple

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.utils import str_to_bool

from hi.simulator.services.base_models import SimEntityFields, SimState, SimEntityDefinition
from hi.simulator.services.enums import SimEntityType, SimStateType


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
    # Default off (brightness 0); operator raises it via the slider.
    value              : str                           = '0'

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
    # Default off (brightness 0); operator raises it via the slider.
    value              : str                           = '0'

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
    # Default off (brightness 0); operator raises it via the slider.
    value              : str                           = '0'

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
            'min_color_temp_kelvin': 2200,
            'max_color_temp_kelvin': 6500,
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


# --------------------------------------------------------------------------
# Binary sensors (non-Insteon, explicit device_class)
# --------------------------------------------------------------------------
#
# Door / window contact sensors and smoke detectors are
# ``binary_sensor.x`` entities differentiated by their
# ``device_class`` attribute. Per HA convention the alarm state
# is ``'on'`` (door/window open, smoke detected); ``'off'`` is
# the normal state. The three classes are structurally similar
# but kept parallel because the underlying SimStateType differs
# (OPEN_CLOSE for door/window, ON_OFF for smoke) which drives a
# different simulator-side UI control.


def _binary_sensor_entity_id( name : str, suffix : str = '' ) -> str:
    slug = name.lower().replace( ' ', '_' )
    if suffix:
        return f'binary_sensor.{slug}{suffix}'
    return f'binary_sensor.{slug}'


@dataclass( frozen = True )
class HassDoorContactSensorFields( SimEntityFields ):
    """A door contact sensor (``binary_sensor`` with
    ``device_class=door``). Single OPEN_CLOSE SimState whose
    value drives HA's ``state`` (``'on'`` = open, ``'off'`` =
    closed, per HA convention)."""
    pass


@dataclass
class HassDoorContactSensorState( HassState ):
    sim_entity_fields  : HassDoorContactSensorFields
    sim_state_type     : SimStateType                  = SimStateType.OPEN_CLOSE
    sim_state_id       : str                           = 'contact'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Contact'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'door',
            'friendly_name': self.entity_name,
            'icon': 'mdi:door',
        }


@dataclass( frozen = True )
class HassWindowContactSensorFields( SimEntityFields ):
    """A window contact sensor (``binary_sensor`` with
    ``device_class=window``). Wire shape mirrors the door variant
    aside from the device_class string."""
    pass


@dataclass
class HassWindowContactSensorState( HassState ):
    sim_entity_fields  : HassWindowContactSensorFields
    sim_state_type     : SimStateType                  = SimStateType.OPEN_CLOSE
    sim_state_id       : str                           = 'contact'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Contact'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'window',
            'friendly_name': self.entity_name,
            'icon': 'mdi:window-closed-variant',
        }


@dataclass( frozen = True )
class HassSmokeDetectorFields( SimEntityFields ):
    """A smoke detector (``binary_sensor`` with
    ``device_class=smoke``). Single ON_OFF SimState — ``'on'``
    means smoke detected (alarm), ``'off'`` is clear, per HA
    convention."""
    pass


@dataclass
class HassSmokeDetectorState( HassState ):
    sim_entity_fields  : HassSmokeDetectorFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'smoke'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Smoke'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'smoke',
            'friendly_name': self.entity_name,
            'icon': 'mdi:smoke-detector',
        }


@dataclass( frozen = True )
class HassSmokeDetectorWithBatteryFields( SimEntityFields ):
    """Smoke detector that also reports a battery percentage —
    common shape for battery-powered Zigbee / Z-Wave smoke alarms."""
    pass


@dataclass
class HassSmokeDetectorWithBatterySmokeState( HassState ):
    sim_entity_fields  : HassSmokeDetectorWithBatteryFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'smoke'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Smoke'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'smoke',
            'friendly_name': self.entity_name,
            'icon': 'mdi:smoke-detector',
        }


@dataclass
class HassSmokeDetectorWithBatteryBatteryState( HassState ):
    sim_entity_fields  : HassSmokeDetectorWithBatteryFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'battery'
    value              : str                           = '85'

    @property
    def name(self):
        return f'{self.entity_name} Battery'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_battery' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'battery',
            'friendly_name'      : f'{self.entity_name} Battery',
            'unit_of_measurement': '%',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def display_unit(self) -> str:
        return '%'


@dataclass( frozen = True )
class HassCarbonMonoxideDetectorFields( SimEntityFields ):
    """A carbon monoxide detector (``binary_sensor`` with
    ``device_class=carbon_monoxide``). Single ON_OFF SimState —
    ``'on'`` means CO detected (alarm), ``'off'`` is clear."""
    pass


@dataclass
class HassCarbonMonoxideDetectorState( HassState ):
    sim_entity_fields  : HassCarbonMonoxideDetectorFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'carbon_monoxide'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Carbon Monoxide'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'carbon_monoxide',
            'friendly_name': self.entity_name,
            'icon': 'mdi:molecule-co',
        }


@dataclass( frozen = True )
class HassGasDetectorFields( SimEntityFields ):
    """A combustible-gas detector (``binary_sensor`` with
    ``device_class=gas``). Single ON_OFF SimState — ``'on'``
    means gas detected (alarm), ``'off'`` is clear."""
    pass


@dataclass
class HassGasDetectorState( HassState ):
    sim_entity_fields  : HassGasDetectorFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'gas'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Gas'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'gas',
            'friendly_name': self.entity_name,
            'icon': 'mdi:gas-cylinder',
        }


@dataclass( frozen = True )
class HassMotionSensorFields( SimEntityFields ):
    """A motion sensor (``binary_sensor`` with
    ``device_class=motion``). Single ON_OFF SimState whose value
    drives HA's ``state`` (``'on'`` = motion detected, ``'off'`` =
    idle, per HA convention)."""
    pass


@dataclass
class HassMotionSensorState( HassState ):
    sim_entity_fields  : HassMotionSensorFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'motion'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Motion'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'motion',
            'friendly_name': self.entity_name,
            'icon': 'mdi:motion-sensor',
        }


@dataclass( frozen = True )
class HassComboMotionSensorFields( SimEntityFields ):
    """Multi-feature motion sensor (Z-Wave / Zigbee shape): a
    ``binary_sensor.x`` for motion plus ``sensor.x`` entities for
    battery percentage and ambient illuminance. Real devices
    expose these as three separate entities sharing a device
    group; HI's converter collapses them via the suffix-strip
    grouping into one Entity with three EntityStates."""
    pass


@dataclass
class HassComboMotionSensorMotionState( HassState ):
    sim_entity_fields  : HassComboMotionSensorFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'motion'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Motion'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name, suffix = '_motion' )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'motion',
            'friendly_name': f'{self.entity_name} Motion',
            'icon': 'mdi:motion-sensor',
        }


@dataclass
class HassComboMotionSensorBatteryState( HassState ):
    sim_entity_fields  : HassComboMotionSensorFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'battery'
    value              : str                           = '85'

    @property
    def name(self):
        return f'{self.entity_name} Battery'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_battery' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'battery',
            'friendly_name'      : f'{self.entity_name} Battery',
            'unit_of_measurement': '%',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def display_unit(self) -> str:
        return '%'


@dataclass
class HassComboMotionSensorIlluminanceState( HassState ):
    sim_entity_fields  : HassComboMotionSensorFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'illuminance'
    value              : str                           = '120'

    @property
    def name(self):
        return f'{self.entity_name} Illuminance'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_illuminance' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'illuminance',
            'friendly_name'      : f'{self.entity_name} Illuminance',
            'unit_of_measurement': 'lx',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 10000

    @property
    def display_unit(self) -> str:
        return 'lx'


# --------------------------------------------------------------------------
# Switch domain (non-Insteon)
# --------------------------------------------------------------------------
#
# HA ``switch.x`` entities. Two shapes:
#
# 1. Generic switch (no ``device_class``) — maps to
#    ``EntityType.ON_OFF_SWITCH`` or one of the name-inferred
#    types (LIGHT / CEILING_FAN / ELECTRICAL_OUTLET).
# 2. Outlet (``device_class=outlet``) — maps directly to
#    ``EntityType.ELECTRICAL_OUTLET``.


def _switch_entity_id( name : str ) -> str:
    suffix = name.lower().replace( ' ', '_' )
    return f'switch.{suffix}'


@dataclass( frozen = True )
class HassSwitchFields( SimEntityFields ):
    """Generic on/off switch (``switch.x`` with no
    ``device_class``)."""
    pass


@dataclass
class HassSwitchState( HassState ):
    sim_entity_fields  : HassSwitchFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'switch'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Switch'

    @property
    def entity_id(self):
        return _switch_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'friendly_name': self.entity_name,
            'icon': 'mdi:toggle-switch',
        }


@dataclass( frozen = True )
class HassOutletFields( SimEntityFields ):
    """Electrical outlet (``switch.x`` with
    ``device_class=outlet``)."""
    pass


@dataclass
class HassOutletState( HassState ):
    sim_entity_fields  : HassOutletFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'outlet'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Outlet'

    @property
    def entity_id(self):
        return _switch_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'outlet',
            'friendly_name': self.entity_name,
            'icon': 'mdi:power-socket-us',
        }


# --------------------------------------------------------------------------
# Numeric sensors (``sensor.x`` with explicit device_class)
# --------------------------------------------------------------------------
#
# Read-only HA ``sensor`` entities whose ``state`` is a numeric
# string and whose ``unit_of_measurement`` attribute drives HI's
# units-aware display path. Three shapes are provided:
#
# 1. Temperature sensor (single ``sensor.x`` with
#    ``device_class=temperature``).
# 2. Humidity sensor (single ``sensor.x`` with
#    ``device_class=humidity``).
# 3. Combo temp+humidity sensor (two ``sensor.x`` entities
#    sharing a short_name so HI's converter groups them into one
#    HI Entity with two EntityStates — mirrors real-world combo
#    sensors like Aqara / BME280 / SHT3x).
#
# Each SimState is CONTINUOUS so the operator can drive the
# value from the simulator UI. No HA-side controllability —
# real ``sensor.x`` entities are read-only.


_DEFAULT_FAHRENHEIT_VALUE = '70'
_DEFAULT_CELSIUS_VALUE = '21'
_FAHRENHEIT_MIN = 30
_FAHRENHEIT_MAX = 100
_CELSIUS_MIN = 0
_CELSIUS_MAX = 40


def _sensor_entity_id( name : str, suffix : str = '' ) -> str:
    """``sensor.<slug>[_suffix]``. Combo states pass
    ``_temperature`` / ``_humidity`` as the suffix so the
    short_name (after HI strips known suffixes) is the same for
    both states, which is what groups them into one HassDevice."""
    slug = name.lower().replace( ' ', '_' )
    if suffix:
        return f'sensor.{slug}{suffix}'
    return f'sensor.{slug}'


@dataclass( frozen = True )
class HassTemperatureSensorFields( SimEntityFields ):
    """Standalone temperature sensor (``sensor.x`` with
    ``device_class=temperature``). ``temperature_unit`` toggles
    °F vs °C end-to-end so HI's unit pass-through can be
    exercised in both directions."""
    temperature_unit : str = '°F'


@dataclass
class HassTemperatureSensorState( HassState ):
    sim_entity_fields  : HassTemperatureSensorFields
    sim_state_type     : SimStateType                       = SimStateType.CONTINUOUS
    sim_state_id       : str                                = 'temperature'
    value              : str                                = _DEFAULT_FAHRENHEIT_VALUE

    def __post_init__(self):
        super().__post_init__()
        # Class-level default is Fahrenheit-shaped (``'70'``); on
        # °C-configured profiles swap it for a sensible Celsius
        # default so first-load values don't read as ``70°C``.
        # Only swaps when ``value`` still equals the class default,
        # so operator-set values survive.
        if self.sim_entity_fields.temperature_unit != '°C':
            return
        class_default = type( self ).__dataclass_fields__[ 'value' ].default
        if self.value == class_default:
            self.value = _DEFAULT_CELSIUS_VALUE

    @property
    def name(self):
        return f'{self.entity_name} Temperature'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name )

    @property
    def state(self):
        # For ``sensor.x`` entities the wire ``state`` IS the
        # numeric reading — HA encodes it as a string.
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'temperature',
            'friendly_name'      : self.entity_name,
            'unit_of_measurement': self.sim_entity_fields.temperature_unit,
        }

    @property
    def min_value(self):
        if self.sim_entity_fields.temperature_unit == '°C':
            return _CELSIUS_MIN
        return _FAHRENHEIT_MIN

    @property
    def max_value(self):
        if self.sim_entity_fields.temperature_unit == '°C':
            return _CELSIUS_MAX
        return _FAHRENHEIT_MAX

    @property
    def display_unit(self) -> str:
        return self.sim_entity_fields.temperature_unit


@dataclass( frozen = True )
class HassHumiditySensorFields( SimEntityFields ):
    """Standalone humidity sensor (``sensor.x`` with
    ``device_class=humidity``). Unit is always ``%`` so no
    per-device toggle is needed."""
    pass


@dataclass
class HassHumiditySensorState( HassState ):
    sim_entity_fields  : HassHumiditySensorFields
    sim_state_type     : SimStateType                    = SimStateType.CONTINUOUS
    sim_state_id       : str                             = 'humidity'
    value              : str                             = '45'

    @property
    def name(self):
        return f'{self.entity_name} Humidity'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'humidity',
            'friendly_name'      : self.entity_name,
            'unit_of_measurement': '%',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100


@dataclass( frozen = True )
class HassTempHumiditySensorFields( SimEntityFields ):
    """Combo sensor that reports both temperature and humidity
    (e.g., Aqara / BME280 / SHT3x). HA represents this as two
    separate ``sensor.x`` entities; HI's converter collapses
    them back into one Entity with two EntityStates via
    suffix-strip grouping (``sensor.<name>_temperature`` and
    ``sensor.<name>_humidity`` share short_name ``<name>``)."""
    temperature_unit : str = '°F'


@dataclass
class HassTempHumiditySensorTemperatureState( HassState ):
    sim_entity_fields  : HassTempHumiditySensorFields
    sim_state_type     : SimStateType                          = SimStateType.CONTINUOUS
    sim_state_id       : str                                   = 'temperature'
    value              : str                                   = _DEFAULT_FAHRENHEIT_VALUE

    def __post_init__(self):
        super().__post_init__()
        if self.sim_entity_fields.temperature_unit != '°C':
            return
        class_default = type( self ).__dataclass_fields__[ 'value' ].default
        if self.value == class_default:
            self.value = _DEFAULT_CELSIUS_VALUE

    @property
    def name(self):
        return f'{self.entity_name} Temperature'

    @property
    def entity_id(self):
        # ``_temperature`` suffix is in ``STATE_SUFFIXES``, so
        # HI strips it to the short_name for grouping.
        return _sensor_entity_id( self.entity_name, suffix = '_temperature' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'temperature',
            'friendly_name'      : f'{self.entity_name} Temperature',
            'unit_of_measurement': self.sim_entity_fields.temperature_unit,
        }

    @property
    def min_value(self):
        if self.sim_entity_fields.temperature_unit == '°C':
            return _CELSIUS_MIN
        return _FAHRENHEIT_MIN

    @property
    def max_value(self):
        if self.sim_entity_fields.temperature_unit == '°C':
            return _CELSIUS_MAX
        return _FAHRENHEIT_MAX

    @property
    def display_unit(self) -> str:
        return self.sim_entity_fields.temperature_unit


@dataclass
class HassTempHumiditySensorHumidityState( HassState ):
    sim_entity_fields  : HassTempHumiditySensorFields
    sim_state_type     : SimStateType                          = SimStateType.CONTINUOUS
    sim_state_id       : str                                   = 'humidity'
    value              : str                                   = '45'

    @property
    def name(self):
        return f'{self.entity_name} Humidity'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_humidity' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'humidity',
            'friendly_name'      : f'{self.entity_name} Humidity',
            'unit_of_measurement': '%',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100


# --------------------------------------------------------------------------
# Stand-alone binary sensors (presence, opening)
# --------------------------------------------------------------------------


@dataclass( frozen = True )
class HassPresenceSensorFields( SimEntityFields ):
    """A presence sensor (``binary_sensor`` with
    ``device_class=presence``). Maps to ``EntityType.PRESENCE_SENSOR``
    in HI, distinct from motion sensors (PRESENCE has its own
    decay styling)."""
    pass


@dataclass
class HassPresenceSensorState( HassState ):
    sim_entity_fields  : HassPresenceSensorFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'presence'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Presence'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'presence',
            'friendly_name': self.entity_name,
            'icon': 'mdi:home-account',
        }


@dataclass( frozen = True )
class HassOpeningSensorFields( SimEntityFields ):
    """A generic-opening sensor (``binary_sensor`` with
    ``device_class=opening``). HA's catch-all for any
    open/closed binary not specifically door / window / garage."""
    pass


@dataclass
class HassOpeningSensorState( HassState ):
    sim_entity_fields  : HassOpeningSensorFields
    sim_state_type     : SimStateType                  = SimStateType.OPEN_CLOSE
    sim_state_id       : str                           = 'opening'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Opening'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'opening',
            'friendly_name': self.entity_name,
            'icon': 'mdi:gesture-tap',
        }


# --------------------------------------------------------------------------
# Power meter (numeric ``sensor.x`` with ``device_class=power``)
# --------------------------------------------------------------------------


@dataclass( frozen = True )
class HassPowerMeterFields( SimEntityFields ):
    """A power meter — single ``sensor.x`` with
    ``device_class=power``. Operator-drivable so the simulator
    UI exposes a numeric slider; the unit ('W') passes through
    to HI's display path."""
    pass


@dataclass
class HassPowerMeterState( HassState ):
    sim_entity_fields  : HassPowerMeterFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'power'
    value              : str                           = '350'

    @property
    def name(self):
        return f'{self.entity_name} Power'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'power',
            'friendly_name'      : self.entity_name,
            'unit_of_measurement': 'W',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 5000

    @property
    def display_unit(self) -> str:
        return 'W'


# --------------------------------------------------------------------------
# Weather station (5-state combo: temperature + humidity + pressure +
# wind_speed + illuminance)
# --------------------------------------------------------------------------
#
# Five ``sensor.x`` entities sharing one device, exercising HI's
# multi-state grouping with mixed device classes. Each state's
# entity_id carries the matching ``_<device_class>`` suffix so
# HI's converter strips them to the same short_name and groups
# all five under one HassDevice / one HI Entity.


@dataclass( frozen = True )
class HassWeatherStationFields( SimEntityFields ):
    """Multi-quantity outdoor sensor (Netatmo / Bresser shape).
    ``temperature_unit`` toggles °F vs °C so the simulator can
    exercise the unit pass-through path for the temperature
    component."""
    temperature_unit : str = '°F'


@dataclass
class HassWeatherStationTemperatureState( HassState ):
    sim_entity_fields  : HassWeatherStationFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'temperature'
    value              : str                           = '68'

    @property
    def name(self):
        return f'{self.entity_name} Temperature'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_temperature' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'temperature',
            'friendly_name'      : f'{self.entity_name} Temperature',
            'unit_of_measurement': self.sim_entity_fields.temperature_unit,
        }

    @property
    def min_value(self):
        if self.sim_entity_fields.temperature_unit == '°C':
            return -20
        return 0

    @property
    def max_value(self):
        if self.sim_entity_fields.temperature_unit == '°C':
            return 50
        return 120

    @property
    def display_unit(self) -> str:
        return self.sim_entity_fields.temperature_unit


@dataclass
class HassWeatherStationHumidityState( HassState ):
    sim_entity_fields  : HassWeatherStationFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'humidity'
    value              : str                           = '55'

    @property
    def name(self):
        return f'{self.entity_name} Humidity'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_humidity' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'humidity',
            'friendly_name'      : f'{self.entity_name} Humidity',
            'unit_of_measurement': '%',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def display_unit(self) -> str:
        return '%'


@dataclass
class HassWeatherStationPressureState( HassState ):
    sim_entity_fields  : HassWeatherStationFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'pressure'
    value              : str                           = '1013'

    @property
    def name(self):
        return f'{self.entity_name} Pressure'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_pressure' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'pressure',
            'friendly_name'      : f'{self.entity_name} Pressure',
            'unit_of_measurement': 'hPa',
        }

    @property
    def min_value(self):
        return 950

    @property
    def max_value(self):
        return 1050

    @property
    def display_unit(self) -> str:
        return 'hPa'


@dataclass
class HassWeatherStationWindSpeedState( HassState ):
    sim_entity_fields  : HassWeatherStationFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'wind_speed'
    value              : str                           = '12'

    @property
    def name(self):
        return f'{self.entity_name} Wind Speed'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_wind_speed' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'wind_speed',
            'friendly_name'      : f'{self.entity_name} Wind Speed',
            'unit_of_measurement': 'km/h',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 150

    @property
    def display_unit(self) -> str:
        return 'km/h'


@dataclass
class HassWeatherStationIlluminanceState( HassState ):
    sim_entity_fields  : HassWeatherStationFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'illuminance'
    value              : str                           = '8500'

    @property
    def name(self):
        return f'{self.entity_name} Illuminance'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_illuminance' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'illuminance',
            'friendly_name'      : f'{self.entity_name} Illuminance',
            'unit_of_measurement': 'lx',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100000

    @property
    def display_unit(self) -> str:
        return 'lx'


# --------------------------------------------------------------------------
# Occupancy + light sensor (2-state combo)
# --------------------------------------------------------------------------
#
# A room-presence sensor with ambient light measurement —
# common in smart-home automation devices (Aqara P1 etc.).


@dataclass( frozen = True )
class HassOccupancyLightSensorFields( SimEntityFields ):
    """Combo occupancy + illuminance sensor."""
    pass


@dataclass
class HassOccupancyLightSensorOccupancyState( HassState ):
    sim_entity_fields  : HassOccupancyLightSensorFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'occupancy'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Occupancy'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name, suffix = '_occupancy' )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'occupancy',
            'friendly_name': f'{self.entity_name} Occupancy',
            'icon': 'mdi:home-account',
        }


@dataclass
class HassOccupancyLightSensorIlluminanceState( HassState ):
    sim_entity_fields  : HassOccupancyLightSensorFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'illuminance'
    value              : str                           = '180'

    @property
    def name(self):
        return f'{self.entity_name} Illuminance'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_illuminance' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'illuminance',
            'friendly_name'      : f'{self.entity_name} Illuminance',
            'unit_of_measurement': 'lx',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 1000

    @property
    def display_unit(self) -> str:
        return 'lx'


# --------------------------------------------------------------------------
# Water leak sensor (2-state combo: moisture + battery)
# --------------------------------------------------------------------------


@dataclass( frozen = True )
class HassWaterLeakSensorFields( SimEntityFields ):
    """Water-leak sensor with battery readout — common shape
    for Zigbee leak sensors."""
    pass


@dataclass
class HassWaterLeakSensorMoistureState( HassState ):
    sim_entity_fields  : HassWaterLeakSensorFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'moisture'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Moisture'

    @property
    def entity_id(self):
        return _binary_sensor_entity_id( self.entity_name, suffix = '_moisture' )

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'moisture',
            'friendly_name': f'{self.entity_name} Moisture',
            'icon': 'mdi:water-alert',
        }


@dataclass
class HassWaterLeakSensorBatteryState( HassState ):
    sim_entity_fields  : HassWaterLeakSensorFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'battery'
    value              : str                           = '85'

    @property
    def name(self):
        return f'{self.entity_name} Battery'

    @property
    def entity_id(self):
        return _sensor_entity_id( self.entity_name, suffix = '_battery' )

    @property
    def state(self):
        return self.value

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class'       : 'battery',
            'friendly_name'      : f'{self.entity_name} Battery',
            'unit_of_measurement': '%',
        }

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def display_unit(self) -> str:
        return '%'


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


@dataclass( frozen = True )
class HassFanFields( SimEntityFields ):
    """Speed-only fan. Single CONTINUOUS SimState (0-100
    percentage). The ``state`` property derives ``'on'`` /
    ``'off'`` from the percentage; ``percentage`` and
    ``percentage_step`` attributes carry the numeric value and
    granularity."""
    pass


def _fan_entity_id( name : str ) -> str:
    suffix = name.lower().replace( ' ', '_' )
    return f'fan.{suffix}'


@dataclass
class HassFanState( HassState ):
    sim_entity_fields  : HassFanFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'percentage'
    value              : str                           = '0'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def name(self):
        return f'{self.entity_name} Speed'

    @property
    def entity_id(self):
        return _fan_entity_id( self.entity_name )

    @property
    def state(self):
        try:
            percentage = int( float( self.value ) )
        except ( TypeError, ValueError ):
            percentage = 0
        return 'on' if percentage > 0 else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        try:
            percentage = int( float( self.value ) )
        except ( TypeError, ValueError ):
            percentage = 0
        # 25%-step granularity (low/medium/high/max). Real fans
        # vary; this is a representative middle-of-the-road shape.
        return {
            'friendly_name': self.entity_name,
            'percentage': percentage,
            'percentage_step': 25,
        }


@dataclass( frozen = True )
class HassMultiFeatureFanFields( SimEntityFields ):
    """A multi-feature ceiling fan: speed plus oscillating,
    direction, and preset_mode axes. Composed of multiple
    SimStates collapsed into one HA ``fan.x`` entity at emit
    time by ``api_composers``. HI imports this as four peer
    substate EntityStates (~speed, ~oscillating, ~direction,
    ~preset)."""
    pass


def _multi_feature_fan_entity_id( name : str ) -> str:
    suffix = name.lower().replace( ' ', '_' )
    return f'fan.{suffix}'


@dataclass
class HassMultiFeatureFanPercentageState( HassState ):
    """Speed component (CONTINUOUS, 0-100). Primary state of the
    composed entity (drives the entity's ``state`` field)."""

    sim_entity_fields  : HassMultiFeatureFanFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'percentage'
    value              : str                           = '0'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def name(self):
        return f'{self.entity_name} Speed'

    @property
    def entity_id(self):
        return _multi_feature_fan_entity_id( self.entity_name )

    @property
    def state(self):
        try:
            percentage = int( float( self.value ) )
        except ( TypeError, ValueError ):
            percentage = 0
        return 'on' if percentage > 0 else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        try:
            percentage = int( float( self.value ) )
        except ( TypeError, ValueError ):
            percentage = 0
        return {
            'friendly_name': self.entity_name,
            'percentage': percentage,
            'percentage_step': 25,
        }


@dataclass
class HassMultiFeatureFanOscillatingState( HassState ):
    """Oscillation component (ON_OFF). Composed into the entity's
    ``oscillating`` attribute as a real Python bool (HA expects
    bool, not the simulator's internal ``'on'``/``'off'``
    string)."""

    sim_entity_fields  : HassMultiFeatureFanFields
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'oscillating'
    value              : str                           = 'off'

    @property
    def name(self):
        return f'{self.entity_name} Oscillation'

    @property
    def entity_id(self):
        return _multi_feature_fan_entity_id( self.entity_name )

    @property
    def state(self):
        # Composer ignores; primary state drives entity-level state.
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return { 'oscillating': str_to_bool( self.value ) }


@dataclass
class HassMultiFeatureFanDirectionState( HassState ):
    """Direction component (DISCRETE). Two-value enum;
    contributes the entity's ``direction`` attribute."""

    DIRECTION_CHOICES : ClassVar[ List[ Tuple[ str, str ] ] ] = [
        ( 'forward', 'Forward' ),
        ( 'reverse', 'Reverse' ),
    ]

    sim_entity_fields  : HassMultiFeatureFanFields
    sim_state_type     : SimStateType                  = SimStateType.DISCRETE
    sim_state_id       : str                           = 'direction'
    value              : str                           = 'forward'

    @property
    def name(self):
        return f'{self.entity_name} Direction'

    @property
    def entity_id(self):
        return _multi_feature_fan_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return self.DIRECTION_CHOICES

    @property
    def attributes(self) -> Dict[ str, str ]:
        return { 'direction': self.value }


@dataclass
class HassMultiFeatureFanPresetState( HassState ):
    """Preset component (DISCRETE). Three representative HA
    presets — actual fan vendors expose varying lists; the
    simulator picks a small standard set so HI's import path
    sees the per-fan ``preset_modes`` declaration without
    overreaching into vendor-specific ones. Contributes the
    entity's ``preset_mode`` (current selection) and
    ``preset_modes`` (available list) attributes."""

    PRESET_CHOICES : ClassVar[ List[ Tuple[ str, str ] ] ] = [
        ( 'auto', 'Auto' ),
        ( 'sleep', 'Sleep' ),
        ( 'eco', 'Eco' ),
    ]

    sim_entity_fields  : HassMultiFeatureFanFields
    sim_state_type     : SimStateType                  = SimStateType.DISCRETE
    sim_state_id       : str                           = 'preset'
    value              : str                           = 'auto'

    @property
    def name(self):
        return f'{self.entity_name} Preset'

    @property
    def entity_id(self):
        return _multi_feature_fan_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return self.PRESET_CHOICES

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'preset_mode': self.value,
            'preset_modes': [ choice for choice, _label in self.PRESET_CHOICES ],
        }


# Per-mode display labels for the operator-facing dropdown in
# the simulator UI. Per-instance ``hvac_modes`` (set on the
# fields) is filtered against this map to build the choices
# list — so each thermostat advertises only the modes its
# fields declare.
_THERMOSTAT_HVAC_MODE_LABELS = {
    'heat'      : 'Heat',
    'cool'      : 'Cool',
    'heat_cool' : 'Heat/Cool',
    'off'       : 'Off',
    'auto'      : 'Auto',
    'dry'       : 'Dry',
    'fan_only'  : 'Fan Only',
}
_THERMOSTAT_HVAC_ACTION_CHOICES = [
    ( 'heating', 'Heating' ),
    ( 'cooling', 'Cooling' ),
    ( 'idle', 'Idle' ),
    ( 'off', 'Off' ),
]


# Closed value sets for the multi-axis thermostat's mode lists. Rendered as
# checkbox pickers in the simulator edit form (via the ``csv_choices`` hook);
# the dataclass fields stay plain lists of the selected wire values.
HASS_HVAC_MODE_CHOICES = [
    ( 'off', 'Off' ),
    ( 'heat', 'Heat' ),
    ( 'cool', 'Cool' ),
    ( 'heat_cool', 'Heat/Cool' ),
    ( 'auto', 'Auto' ),
    ( 'dry', 'Dry' ),
    ( 'fan_only', 'Fan only' ),
]
HASS_FAN_MODE_CHOICES = [
    ( 'auto', 'Auto' ),
    ( 'low', 'Low' ),
    ( 'medium', 'Medium' ),
    ( 'high', 'High' ),
    ( 'on', 'On' ),
    ( 'off', 'Off' ),
]
HASS_PRESET_MODE_CHOICES = [
    ( 'none', 'None' ),
    ( 'eco', 'Eco' ),
    ( 'away', 'Away' ),
    ( 'home', 'Home' ),
    ( 'sleep', 'Sleep' ),
    ( 'comfort', 'Comfort' ),
    ( 'boost', 'Boost' ),
    ( 'activity', 'Activity' ),
]


@dataclass( frozen = True )
class HassThermostatFields( SimEntityFields ):
    """A multi-axis thermostat. Composed of multiple SimStates
    (current_temperature, target_temperature, target_temp_low,
    target_temp_high, hvac_mode, hvac_action, fan_mode,
    current_humidity) collapsed into one HA ``climate.x``
    entity at emit time.

    ``hvac_modes`` declares the modes this thermostat supports —
    a heat-only thermostat omits ``heat_cool`` (and HI
    accordingly creates only the single-setpoint substate, not
    the low/high pair). ``fan_modes`` declares the available
    fan settings (when empty, the thermostat doesn't expose a
    fan-mode axis). ``temperature_unit`` controls °F vs °C
    handling end-to-end so HI's unit passthrough can be
    exercised for both."""

    hvac_modes       : list = field(
        default_factory = lambda : [ 'heat', 'cool', 'heat_cool', 'off' ],
        metadata = {
            'csv_choices': HASS_HVAC_MODE_CHOICES,
            'help_text': 'HVAC modes this thermostat exposes.',
        },
    )
    fan_modes        : list = field(
        default_factory = lambda : [ 'auto', 'low', 'medium', 'high' ],
        metadata = {
            'csv_choices': HASS_FAN_MODE_CHOICES,
            'help_text': 'Fan modes (leave empty to omit the fan-mode axis).',
        },
    )
    preset_modes     : list = field(
        default_factory = lambda : [ 'eco', 'away', 'home', 'sleep' ],
        metadata = {
            'csv_choices': HASS_PRESET_MODE_CHOICES,
            'help_text': 'Preset modes this thermostat exposes.',
        },
    )
    temperature_unit : str  = '°F'


def _thermostat_entity_id( name : str ) -> str:
    suffix = name.lower().replace( ' ', '_' )
    return f'climate.{suffix}'


class _ThermostatTemperatureDefaultMixin:
    """Mixin for thermostat temperature SimStates that swaps the
    Fahrenheit-style class default (e.g., ``'70'``) for a sensible
    Celsius value when the parent entity is configured °C-native.

    Without this, °C-native profiles (e.g., Zoo Heater) would
    initialize ``current_temperature = 70`` meaning 70°C — over
    150°F, which makes the simulator's value confusing on first
    load. Subclasses set ``_CELSIUS_DEFAULT_VALUE``; the mixin
    detects the dataclass field default and swaps it in. User-
    overridden values (set via the simulator UI) bypass the swap
    because they no longer match the class default."""

    _CELSIUS_DEFAULT_VALUE : str = ''

    # Slider bounds used when temperature_unit is °F (the seed
    # default) and °C respectively. Picked so both ranges cover
    # roughly the same physical span (−1°C / 30°F at the low end,
    # ~38°C / 100°F at the high end), with round numbers in each
    # unit so the slider looks natural.
    _FAHRENHEIT_MIN = 30
    _FAHRENHEIT_MAX = 100
    _CELSIUS_MIN = 0
    _CELSIUS_MAX = 40

    def _apply_celsius_default_if_native(self):
        if not self._CELSIUS_DEFAULT_VALUE:
            return
        if getattr( self.sim_entity_fields, 'temperature_unit', None ) != '°C':
            return
        class_default = type( self ).__dataclass_fields__[ 'value' ].default
        if self.value == class_default:
            self.value = self._CELSIUS_DEFAULT_VALUE

    def _is_celsius_native(self) -> bool:
        return getattr(
            self.sim_entity_fields, 'temperature_unit', None,
        ) == '°C'

    @property
    def min_value(self):
        return self._CELSIUS_MIN if self._is_celsius_native() else self._FAHRENHEIT_MIN

    @property
    def max_value(self):
        return self._CELSIUS_MAX if self._is_celsius_native() else self._FAHRENHEIT_MAX

    @property
    def display_unit(self) -> str:
        """The profile-defined temperature unit. The simulator UI
        shows ``self.value`` directly — and the SimState always
        stores in the profile's unit (the runtime override only
        applies at the wire boundary in the composer/dispatcher).
        So the slider label should be the profile unit too,
        regardless of any active override."""
        return getattr(
            self.sim_entity_fields, 'temperature_unit', '',
        ) or ''


@dataclass
class HassThermostatCurrentTemperatureState(
        _ThermostatTemperatureDefaultMixin, HassState ):
    """Current temperature reading. Sensor-only in HA terms but
    operator-controllable in the simulator UI so a tester can
    drive temperature changes (otherwise there's nothing to
    test)."""

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'current_temperature'
    value              : str                           = '70'

    _CELSIUS_DEFAULT_VALUE = '21'

    def __post_init__(self):
        super().__post_init__()
        self._apply_celsius_default_if_native()

    @property
    def name(self):
        return f'{self.entity_name} Current Temperature'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        # Composer overrides; entity-level state is the hvac_mode.
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        try:
            temp = float( self.value )
        except ( TypeError, ValueError ):
            temp = 0.0
        return { 'current_temperature': temp }


@dataclass
class HassThermostatTargetTemperatureState(
        _ThermostatTemperatureDefaultMixin, HassState ):
    """Single setpoint (used when hvac_mode is heat / cool / off
    / etc., not heat_cool). Composer emits this only when the
    active mode isn't ``heat_cool``."""

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'target_temperature'
    value              : str                           = '72'

    _CELSIUS_DEFAULT_VALUE = '22'

    def __post_init__(self):
        super().__post_init__()
        self._apply_celsius_default_if_native()

    @property
    def name(self):
        return f'{self.entity_name} Setpoint'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        try:
            temp = float( self.value )
        except ( TypeError, ValueError ):
            temp = 0.0
        # Marked partial so the composer can decide whether to
        # emit it based on the active hvac_mode.
        return { '_partial_target_temperature': temp }


@dataclass
class HassThermostatTargetTempLowState(
        _ThermostatTemperatureDefaultMixin, HassState ):
    """Low setpoint of the heat_cool pair. Emitted by the composer
    only when the active mode is heat_cool."""

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'target_temp_low'
    value              : str                           = '68'

    _CELSIUS_DEFAULT_VALUE = '20'

    def __post_init__(self):
        super().__post_init__()
        self._apply_celsius_default_if_native()

    @property
    def name(self):
        return f'{self.entity_name} Setpoint Low'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        try:
            temp = float( self.value )
        except ( TypeError, ValueError ):
            temp = 0.0
        return { '_partial_target_temp_low': temp }


@dataclass
class HassThermostatTargetTempHighState(
        _ThermostatTemperatureDefaultMixin, HassState ):
    """High setpoint of the heat_cool pair. Emitted by the composer
    only when the active mode is heat_cool."""

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'target_temp_high'
    value              : str                           = '75'

    _CELSIUS_DEFAULT_VALUE = '24'

    def __post_init__(self):
        super().__post_init__()
        self._apply_celsius_default_if_native()

    @property
    def name(self):
        return f'{self.entity_name} Setpoint High'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        try:
            temp = float( self.value )
        except ( TypeError, ValueError ):
            temp = 0.0
        return { '_partial_target_temp_high': temp }


@dataclass
class HassThermostatHvacModeState( HassState ):
    """HVAC mode (DISCRETE, controllable). Active mode drives
    the entity-level ``state`` field; the composer pulls this
    state's value into the primary api_dict's state. The
    available choices and the emitted ``hvac_modes`` attribute
    both come from the per-thermostat fields, so a heat-only
    thermostat naturally exposes only ``heat`` / ``off``."""

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.DISCRETE
    sim_state_id       : str                           = 'hvac_mode'
    value              : str                           = 'heat'

    @property
    def name(self):
        return f'{self.entity_name} HVAC Mode'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        # Carries the mode for the composer to lift into the
        # entity-level ``state`` field.
        return self.value

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return [
            ( mode, _THERMOSTAT_HVAC_MODE_LABELS.get( mode, mode ) )
            for mode in self.sim_entity_fields.hvac_modes
        ]

    @property
    def attributes(self) -> Dict[ str, str ]:
        # The mode is the entity's primary state, not an
        # attribute. Emit the supported-modes list as the
        # entity's ``hvac_modes`` attribute so HI's converter
        # can build the substate value range.
        return {
            'hvac_modes': list( self.sim_entity_fields.hvac_modes ),
        }


@dataclass
class HassThermostatFanModeState( HassState ):
    """Fan mode (DISCRETE, controllable). Choices come from the
    per-thermostat ``fan_modes`` field — a thermostat with
    ``fan_modes=[]`` exposes no choices and the composer drops
    the attribute. Common HA values: auto / low / medium / high
    / on / off."""

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.DISCRETE
    sim_state_id       : str                           = 'fan_mode'
    value              : str                           = 'auto'

    @property
    def name(self):
        return f'{self.entity_name} Fan Mode'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return [
            ( mode, mode.title() )
            for mode in self.sim_entity_fields.fan_modes
        ]

    @property
    def attributes(self) -> Dict[ str, str ]:
        if not self.sim_entity_fields.fan_modes:
            return {}
        return {
            'fan_mode': self.value,
            'fan_modes': list( self.sim_entity_fields.fan_modes ),
        }


@dataclass
class HassThermostatPresetState( HassState ):
    """Preset mode (DISCRETE, controllable). Choices come from
    the per-thermostat ``preset_modes`` field. HA's built-in
    preset vocabulary includes eco / away / home / sleep /
    boost / comfort / activity; thermostats with
    ``preset_modes=[]`` skip the attribute entirely."""

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.DISCRETE
    sim_state_id       : str                           = 'preset_mode'
    value              : str                           = 'home'

    @property
    def name(self):
        return f'{self.entity_name} Preset'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return [
            ( mode, mode.title() )
            for mode in self.sim_entity_fields.preset_modes
        ]

    @property
    def attributes(self) -> Dict[ str, str ]:
        if not self.sim_entity_fields.preset_modes:
            return {}
        return {
            'preset_mode': self.value,
            'preset_modes': list( self.sim_entity_fields.preset_modes ),
        }


@dataclass
class HassThermostatCurrentHumidityState( HassState ):
    """Current humidity reading (CONTINUOUS, sensor-only). The
    simulator UI lets the operator drive it for testing."""

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.CONTINUOUS
    sim_state_id       : str                           = 'current_humidity'
    value              : str                           = '45'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 100

    @property
    def name(self):
        return f'{self.entity_name} Current Humidity'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def attributes(self) -> Dict[ str, str ]:
        try:
            humidity = float( self.value )
        except ( TypeError, ValueError ):
            humidity = 0.0
        return { 'current_humidity': humidity }


@dataclass
class HassThermostatHvacActionState( HassState ):
    """What the HVAC system is currently doing (heating /
    cooling / idle / off). Sensor-only in HA terms; the
    simulator exposes the dropdown directly so a tester can
    drive action transitions without simulating the underlying
    physics."""

    HVAC_ACTION_CHOICES : ClassVar[ List[ Tuple[ str, str ] ] ] = list(
        _THERMOSTAT_HVAC_ACTION_CHOICES,
    )

    sim_entity_fields  : HassThermostatFields
    sim_state_type     : SimStateType                  = SimStateType.DISCRETE
    sim_state_id       : str                           = 'hvac_action'
    value              : str                           = 'idle'

    @property
    def name(self):
        return f'{self.entity_name} HVAC Action'

    @property
    def entity_id(self):
        return _thermostat_entity_id( self.entity_name )

    @property
    def state(self):
        return 'on'

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return self.HVAC_ACTION_CHOICES

    @property
    def attributes(self) -> Dict[ str, str ]:
        return { 'hvac_action': self.value }


# ===== Generic Camera =====
#
# Universal-feature HA camera: snapshot via
# ``entity_picture`` / ``access_token``, discrete camera mode, and
# (in the full variant) a paired motion ``binary_sensor.X_motion``.
# See ``api_composers._camera`` for the multi-state-to-HA-entity
# collapse.


def _camera_access_token( entity_id_suffix : str ) -> str:
    """Per-entity stable access token in HA's 32-hex-char shape.
    Stable across simulator restarts so HI integrations holding a
    previously-issued URL still resolve; real HA rotates the token
    on state change, which the simulator deliberately doesn't model
    until the HA integration's token-rotation handling needs an
    explicit test surface."""
    seed = f'hi-sim-camera::{entity_id_suffix}'
    return hashlib.sha256( seed.encode() ).hexdigest()[ :32 ]


@dataclass( frozen = True )
class HassCameraSimEntityFields( SimEntityFields ):
    """Operator-configurable fields for a Generic Camera. The
    ``entity_id_suffix`` becomes the entity's HA identifier stem
    (e.g., ``front_door`` → ``camera.front_door`` +
    ``binary_sensor.front_door_motion``)."""

    entity_id_suffix : str = 'sim_camera_1'
    brand            : str = 'Generic'
    model_name       : str = 'SimCam'


@dataclass( frozen = True )
class HassCameraNoMotionSimEntityFields( HassCameraSimEntityFields ):
    """Variant of the generic camera with no paired motion
    ``binary_sensor``. Some HA camera integrations don't expose one
    (basic MJPEG cameras, certain doorbells); modeling both shapes
    lets HI's integration logic be exercised against either."""
    pass


@dataclass
class HassCameraState( HassState ):
    """Camera-mode primary state. Renders as ``camera.X`` with HA's
    canonical camera attributes (``access_token``, ``entity_picture``,
    ``frontend_stream_type``, brand/model). The ``motion_detection``
    attribute is contributed by the sibling
    ``HassCameraMotionDetectionState`` via the composer; not added
    here."""

    sim_entity_fields  : HassCameraSimEntityFields
    sim_state_type     : SimStateType                 = SimStateType.DISCRETE
    sim_state_id       : str                          = 'camera_mode'
    value              : str                          = 'idle'

    CAMERA_MODE_CHOICES : ClassVar[ List[ Tuple[ str, str ] ] ] = [
        ( 'idle'      , 'Idle' ),
        ( 'streaming' , 'Streaming' ),
        ( 'recording' , 'Recording' ),
    ]

    @property
    def name(self):
        return f'{self.entity_name} Mode'

    @property
    def entity_id(self):
        return f'camera.{self.sim_entity_fields.entity_id_suffix}'

    @property
    def state(self):
        return self.value

    @property
    def choices(self) -> List[ Tuple[ str, str ] ]:
        return self.CAMERA_MODE_CHOICES

    @property
    def attributes(self) -> Dict[ str, str ]:
        token = _camera_access_token( self.sim_entity_fields.entity_id_suffix )
        return {
            'access_token'         : token,
            'entity_picture'       : f'/api/camera_proxy/{self.entity_id}?token={token}',
            'frontend_stream_type' : 'mjpeg',
            'brand'                : self.sim_entity_fields.brand,
            'model_name'           : self.sim_entity_fields.model_name,
            'friendly_name'        : self.entity_name,
        }


@dataclass
class HassCameraMotionDetectionState( HassState ):
    """Toggleable motion-detection flag on the camera. Not emitted as
    its own HA entity — the composer folds its value into the parent
    camera entity's ``motion_detection`` attribute. ``entity_id`` is a
    placeholder used only for the framework's per-state book-keeping;
    it never reaches the ``/api/states`` response."""

    sim_entity_fields  : HassCameraSimEntityFields
    sim_state_type     : SimStateType                 = SimStateType.ON_OFF
    sim_state_id       : str                          = 'motion_detection'
    value              : str                          = 'on'

    @property
    def name(self):
        return f'{self.entity_name} Motion Detection'

    @property
    def entity_id(self):
        # Composer-only placeholder; never emitted.
        return f'_internal.camera_motion_detection.{self.sim_entity_fields.entity_id_suffix}'

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        # Camera composer reads this and merges it into the camera's
        # attributes as ``motion_detection``.
        return { 'motion_detection': str_to_bool( self.value ) }


@dataclass
class HassCameraMotionState( HassState ):
    """Paired motion ``binary_sensor.X_motion``. Renders as its own HA
    entity (the composer does NOT fold it into the camera), mirroring
    HA's reality where the camera and motion sensor are paired but
    separate entities."""

    sim_entity_fields  : HassCameraSimEntityFields
    sim_state_type     : SimStateType                 = SimStateType.MOVEMENT
    sim_state_id       : str                          = 'motion'

    @property
    def name(self):
        return f'{self.entity_name} Motion'

    @property
    def entity_id(self):
        return f'binary_sensor.{self.sim_entity_fields.entity_id_suffix}_motion'

    @property
    def state(self):
        return 'on' if str_to_bool( self.value ) else 'off'

    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class' : 'motion',
            'friendly_name': self.name,
        }


HASS_SIM_ENTITY_DEFINITION_LIST = [
    SimEntityDefinition(
        class_label = 'Generic Camera',
        sim_entity_type = SimEntityType.CAMERA,
        sim_entity_fields_class = HassCameraSimEntityFields,
        sim_state_class_list = [
            HassCameraState,
            HassCameraMotionDetectionState,
            HassCameraMotionState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Generic Camera (no motion sensor)',
        sim_entity_type = SimEntityType.CAMERA,
        sim_entity_fields_class = HassCameraNoMotionSimEntityFields,
        sim_state_class_list = [
            HassCameraState,
        ],
    ),
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
        class_label = 'Door Contact Sensor',
        sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
        sim_entity_fields_class = HassDoorContactSensorFields,
        sim_state_class_list = [
            HassDoorContactSensorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Window Contact Sensor',
        sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
        sim_entity_fields_class = HassWindowContactSensorFields,
        sim_state_class_list = [
            HassWindowContactSensorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Smoke Detector',
        sim_entity_type = SimEntityType.SMOKE_DETECTOR,
        sim_entity_fields_class = HassSmokeDetectorFields,
        sim_state_class_list = [
            HassSmokeDetectorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Smoke Detector (smoke + battery)',
        sim_entity_type = SimEntityType.SMOKE_DETECTOR,
        sim_entity_fields_class = HassSmokeDetectorWithBatteryFields,
        sim_state_class_list = [
            HassSmokeDetectorWithBatterySmokeState,
            HassSmokeDetectorWithBatteryBatteryState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Carbon Monoxide Detector',
        sim_entity_type = SimEntityType.CARBON_MONOXIDE_DETECTOR,
        sim_entity_fields_class = HassCarbonMonoxideDetectorFields,
        sim_state_class_list = [
            HassCarbonMonoxideDetectorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Gas Detector',
        sim_entity_type = SimEntityType.GAS_DETECTOR,
        sim_entity_fields_class = HassGasDetectorFields,
        sim_state_class_list = [
            HassGasDetectorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Motion Sensor',
        sim_entity_type = SimEntityType.MOTION_SENSOR,
        sim_entity_fields_class = HassMotionSensorFields,
        sim_state_class_list = [
            HassMotionSensorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Motion Sensor (combo with battery + illuminance)',
        sim_entity_type = SimEntityType.MOTION_SENSOR,
        sim_entity_fields_class = HassComboMotionSensorFields,
        sim_state_class_list = [
            HassComboMotionSensorMotionState,
            HassComboMotionSensorBatteryState,
            HassComboMotionSensorIlluminanceState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Presence Sensor',
        sim_entity_type = SimEntityType.PRESENCE_SENSOR,
        sim_entity_fields_class = HassPresenceSensorFields,
        sim_state_class_list = [
            HassPresenceSensorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Opening Sensor',
        sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
        sim_entity_fields_class = HassOpeningSensorFields,
        sim_state_class_list = [
            HassOpeningSensorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Power Meter',
        sim_entity_type = SimEntityType.ELECTRICY_METER,
        sim_entity_fields_class = HassPowerMeterFields,
        sim_state_class_list = [
            HassPowerMeterState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Weather Station (temperature + humidity + pressure + wind + illuminance)',
        sim_entity_type = SimEntityType.BAROMETER,
        sim_entity_fields_class = HassWeatherStationFields,
        sim_state_class_list = [
            HassWeatherStationTemperatureState,
            HassWeatherStationHumidityState,
            HassWeatherStationPressureState,
            HassWeatherStationWindSpeedState,
            HassWeatherStationIlluminanceState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Occupancy + Light Sensor',
        sim_entity_type = SimEntityType.PRESENCE_SENSOR,
        sim_entity_fields_class = HassOccupancyLightSensorFields,
        sim_state_class_list = [
            HassOccupancyLightSensorOccupancyState,
            HassOccupancyLightSensorIlluminanceState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Water Leak Sensor (moisture + battery)',
        sim_entity_type = SimEntityType.LEAK_SENSOR,
        sim_entity_fields_class = HassWaterLeakSensorFields,
        sim_state_class_list = [
            HassWaterLeakSensorMoistureState,
            HassWaterLeakSensorBatteryState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Switch',
        sim_entity_type = SimEntityType.WALL_SWITCH,
        sim_entity_fields_class = HassSwitchFields,
        sim_state_class_list = [
            HassSwitchState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Outlet',
        sim_entity_type = SimEntityType.ELECTRICAL_OUTLET,
        sim_entity_fields_class = HassOutletFields,
        sim_state_class_list = [
            HassOutletState,
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
    SimEntityDefinition(
        class_label = 'Fan (speed-only)',
        sim_entity_type = SimEntityType.CEILING_FAN,
        sim_entity_fields_class = HassFanFields,
        sim_state_class_list = [
            HassFanState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Fan (multi-feature)',
        sim_entity_type = SimEntityType.CEILING_FAN,
        sim_entity_fields_class = HassMultiFeatureFanFields,
        sim_state_class_list = [
            HassMultiFeatureFanPercentageState,
            HassMultiFeatureFanOscillatingState,
            HassMultiFeatureFanDirectionState,
            HassMultiFeatureFanPresetState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Temperature Sensor',
        sim_entity_type = SimEntityType.THERMOMETER,
        sim_entity_fields_class = HassTemperatureSensorFields,
        sim_state_class_list = [
            HassTemperatureSensorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Humidity Sensor',
        sim_entity_type = SimEntityType.HYGROMETER,
        sim_entity_fields_class = HassHumiditySensorFields,
        sim_state_class_list = [
            HassHumiditySensorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Temperature + Humidity Sensor',
        sim_entity_type = SimEntityType.THERMOMETER,
        sim_entity_fields_class = HassTempHumiditySensorFields,
        sim_state_class_list = [
            HassTempHumiditySensorTemperatureState,
            HassTempHumiditySensorHumidityState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Thermostat',
        sim_entity_type = SimEntityType.THERMOSTAT,
        sim_entity_fields_class = HassThermostatFields,
        sim_state_class_list = [
            HassThermostatCurrentTemperatureState,
            HassThermostatTargetTemperatureState,
            HassThermostatTargetTempLowState,
            HassThermostatTargetTempHighState,
            HassThermostatHvacModeState,
            HassThermostatHvacActionState,
            HassThermostatFanModeState,
            HassThermostatPresetState,
            HassThermostatCurrentHumidityState,
        ],
    ),
]
