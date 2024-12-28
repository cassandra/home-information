import base64
from dataclasses import dataclass
import os
import time
from typing import Dict

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.entity.enums import EntityStateType, EntityType

from hi.simulator.base_models import SimEntityFields, SimState, SimEntityDefinition


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
class HassInsteonState( SimState ):
    """ Base class for all HAss Insteon device states """
    
    sim_entity_fields  : HassInsteonSimEntityFields
        
    @property
    def insteon_address(self):
        return self.sim_entity_fields.insteon_address

    
@dataclass( frozen = True )
class HassInsteonLightSwitchFields( HassInsteonSimEntityFields ):
    pass

    
@dataclass
class HassInsteonLightSwitchLightState( HassInsteonState ):

    sim_entity_fields  : HassInsteonLightSwitchFields
    entity_state_type  : EntityStateType  = EntityStateType.ON_OFF
    
    @property
    def entity_id(self):
        return 'light.switchlinc_relay_%s' % self.insteon_address.replace( '.', '_' )
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'friendly_name': self.entity_name,
            "icon": "mdi:lightbulb",
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }
    
    @property
    def state(self):
        # TODO: Do translation to HAss state values
        return 'unknown'

    
@dataclass
class HassInsteonLightSwitchColorState( HassInsteonState ):

    sim_entity_fields  : HassInsteonLightSwitchFields
    entity_state_type  : EntityStateType  = EntityStateType.ON_OFF
    
    @property
    def entity_id(self):
        return 'light.switchlinc_relay_%s' % self.insteon_address.replace( '.', '_' )
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            'color_mode': 'onoff',
            'friendly_name': self.entity_name,
            'supported_color_modes': [
                'onoff',
            ],
            'supported_features': 0,
        }
    
    @property
    def state(self):
        # TODO: Do translation to HAss state values
        return 'unknown'


@dataclass( frozen = True )
class HassInsteonMotionDetectorFields( HassInsteonSimEntityFields ):
    pass


@dataclass
class HassInsteonMotionDetectorMotionState( HassInsteonState ):

    sim_entity_fields  : HassInsteonMotionDetectorFields
    entity_state_type  : EntityStateType  = EntityStateType.MOVEMENT
    
    @property
    def entity_id(self):
        return 'binary_sensor.motion_sensor_%s_motion' % self.insteon_address.replace( '.', '_' )
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            "device_class": "motion",
            'friendly_name': f'{self.entity_name} Motion',
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }
    
    @property
    def state(self):
        # TODO: Do translation to HAss state values
        return 'unknown'

    
@dataclass
class HassInsteonMotionDetectorLightState( HassInsteonState ):

    sim_entity_fields  : HassInsteonMotionDetectorFields
    entity_state_type  : EntityStateType  = EntityStateType.ON_OFF
    
    @property
    def entity_id(self):
        return 'binary_sensor.motion_sensor_%s_light' % self.insteon_address.replace( '.', '_' )
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            "device_class": "light",
            'friendly_name': f'{self.entity_name} Light',
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }
    
    @property
    def state(self):
        # TODO: Do translation to HAss state values
        return 'unknown'

    
@dataclass
class HassInsteonMotionDetectorBatteryState( HassInsteonState ):

    sim_entity_fields  : HassInsteonMotionDetectorFields
    entity_state_type  : EntityStateType  = EntityStateType.DISCRETE
    
    @property
    def entity_id(self):
        return 'binary_sensor.motion_sensor_%s_battery' % self.insteon_address.replace( '.', '_' )
    
    @property
    def attributes(self) -> Dict[ str, str ]:
        return {
            "device_class": "battery",
            'friendly_name': f'{self.entity_name} Battery',
            "insteon_address": self.insteon_address,
            "insteon_group": 1,
        }
    
    @property
    def state(self):
        # TODO: Do translation to HAss state values
        return 'unknown'


@dataclass( frozen = True )
class HassInsteonOpenCloseSensorFields( HassInsteonSimEntityFields ):
    pass


@dataclass
class HassInsteonOpenCloseSensorState( HassInsteonState ):

    sim_entity_fields  : HassInsteonOpenCloseSensorFields
    entity_state_type  : EntityStateType  = EntityStateType.OPEN_CLOSE
    
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
    
    @property
    def state(self):
        # TODO: Do translation to HAss state values
        return 'unknown'

    
HASS_SIM_ENTITY_DEFINITION_LIST = [
    SimEntityDefinition(
        class_label = 'Insteon Light Switch',
        entity_type = EntityType.LIGHT,
        sim_entity_fields_class = HassInsteonLightSwitchFields,
        sim_state_class_list = [
            HassInsteonLightSwitchLightState,
            HassInsteonLightSwitchColorState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Insteon Motion Detector',
        entity_type = EntityType.MOTION_SENSOR,
        sim_entity_fields_class = HassInsteonMotionDetectorFields,
        sim_state_class_list = [
            HassInsteonMotionDetectorMotionState,
            HassInsteonMotionDetectorLightState,
            HassInsteonMotionDetectorBatteryState,
        ],
    ),
    SimEntityDefinition(
        class_label = 'Insteon Open/Close Sensor',
        entity_type = EntityType.OPEN_CLOSE_SENSOR,
        sim_entity_fields_class = HassInsteonOpenCloseSensorFields,
        sim_state_class_list = [
            HassInsteonOpenCloseSensorState,
        ],
    ),
]
