import base64
from dataclasses import dataclass
import os
import time
from typing import Dict, List, Tuple

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
        return 'switch.switchlinc_relay_%s' % self.insteon_address.replace( '.', '_' )
    
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
    sim_state_type     : SimStateType                  = SimStateType.ON_OFF
    sim_state_id       : str                           = 'light'

    @property
    def name(self):
        return f'{self.entity_name} Light'
        
    @property
    def entity_id(self):
        return 'light.switchlinc_dimmer_%s' % self.insteon_address.replace( '.', '_' )
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'friendly_name': self.entity_name,
            "icon": "mdi:lightbulb",
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }

    
@dataclass( frozen = True )
class HassInsteonDualBandLightSwitchFields( HassInsteonLightSwitchFields ):
    pass

    
@dataclass
class HassInsteonDualBandLightSwitchState( HassInsteonLightSwitchState ):
    """Dual-band variant (can use powerline or RF) """

    sim_entity_fields  : HassInsteonDualBandLightSwitchFields

    @property
    def entity_id(self):
        return 'switch.switchlinc_relay_dual_band_%s' % self.insteon_address.replace( '.', '_' )


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
        return 'binary_sensor.motion_sensor_%s_motion' % self.insteon_address.replace( '.', '_' )
    
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
        return 'binary_sensor.motion_sensor_%s_light' % self.insteon_address.replace( '.', '_' )
    
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
        return 'binary_sensor.motion_sensor_%s_battery' % self.insteon_address.replace( '.', '_' )
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            "device_class": "battery",
            'friendly_name': self.name,
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }


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
        return 'binary_sensor.open_close_sensor_%s' % self.insteon_address.replace( '.', '_' )
    
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
        return 'switch.outletlinc_relay_%s' % self.insteon_address.replace( '.', '_' )
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'device_class': 'outlet',
            'friendly_name': self.entity_name,
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
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
]
