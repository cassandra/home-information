import base64
from dataclasses import dataclass, field
from datetime import datetime
import os
import time
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.entity.enums import EntityStateType, EntityStateValue, EntityType

from hi.simulator.transient_models import SimEntity, SimState, SimEntityDefinition


@dataclass
class HassState( SimState ):

    entity_id      : str
    last_changed   : datetime
    last_reported  : datetime
    last_updated   : datetime
    state          : str                  = "unknown"
    attributes     : Dict[ str, object ]  = field( default_factory = dict )
    context        : Dict[ str, object ]  = field( default_factory = dict )

    def __post_init__(self):
        self.context['id'] = self.generate_ksuid()
        self.context['parent_id'] = None
        self.context['user_id'] = None
        return
    
    def generate_ksuid(self):
        timestamp = int(time.time()).to_bytes(4, 'big')
        random_data = os.urandom(16)
        raw_ksuid = timestamp + random_data
        return base64.b64encode(raw_ksuid).decode('utf-8').replace('=', '').replace('/', '').replace('+', '')
        
    def to_api_dict(self):
        return {
            'attributes': self.attributes,
            'context': self.context,
            'entity_id': self.entity_id,
            'last_changed': self.last_changed,
            'last_reported': self.last_reported,
            'last_updated': self.last_updated,
            'state' : self.state,
        }
    

@dataclass( frozen = True )
class HassEntity( SimEntity ):

    def to_api_list(self) -> List[ HassState ]:
        raise NotImplementedError('Subclasses must override this.')

    
@dataclass( frozen = True )
class HassInsteonEntity( HassEntity ):

    insteon_address  : str  = None

    
@dataclass( frozen = True )
class HassInsteonLightSwitch( HassInsteonEntity ):

    @property
    def entity_type(self):
        return EntityType.LIGHT
    
    @property
    def sim_state_list(self) -> List[ SimState ]:
        pass
    
    def hass_state_list(self):
        dummy_datetime_iso = datetimeproxy.now().isoformat()
        
        hass_light_state = HassState(
            entity_id = 'light.switchlinc_relay_%s' % self.insteon_address.replace( '.', '_' ),
            attributes = {
                'friendly_name': self.name,
                "icon": "mdi:lightbulb",
                "insteon_address": self.insteon_address,
                "insteon_group": 1,
            },
            last_changed = dummy_datetime_iso,
            last_reported = dummy_datetime_iso,
            last_updated = dummy_datetime_iso,
        )
        hass_color_state = HassState(
            entity_id = 'light.switchlinc_relay_%s' % self.insteon_address.replace( '.', '_' ),
            attributes = {
                'color_mode': 'onoff',
                'friendly_name': self.name,
                'supported_color_modes': [
                    'onoff',
                ],
                'supported_features': 0,
            },
            last_changed = dummy_datetime_iso,
            last_reported = dummy_datetime_iso,
            last_updated = dummy_datetime_iso,
        )
        return [ hass_light_state,
                 hass_color_state ]
    
    def to_api_list(self):
        return [ x.to_api_dict() for x in self.hass_state_list() ]

    
@dataclass( frozen = True )
class HassInsteonMotionDetector( HassInsteonEntity ):

    @property
    def entity_type(self):
        return EntityType.MOTION_SENSOR
    
    def sim_state_list(self) -> List[ SimState ]:
        pass
    
    def hass_state_list(self):
        dummy_datetime_iso = datetimeproxy.now().isoformat()
        
        hass_motion_state = HassState(
            entity_id = 'binary_sensor.motion_sensor_%s_motion' % self.insteon_address.replace( '.', '_' ),
            attributes = {
                "device_class": "motion",
                'friendly_name': f'{self.name} Motion',
                "insteon_address": self.insteon_address,
                "insteon_group": 1,
            },
            last_changed = dummy_datetime_iso,
            last_reported = dummy_datetime_iso,
            last_updated = dummy_datetime_iso,
        )
        hass_light_state = HassState(
            entity_id = 'binary_sensor.motion_sensor_%s_light' % self.insteon_address.replace( '.', '_' ),
            attributes = {
                "device_class": "light",
                'friendly_name': f'{self.name} Light',
                "insteon_address": self.insteon_address,
                "insteon_group": 1,
            },
            last_changed = dummy_datetime_iso,
            last_reported = dummy_datetime_iso,
            last_updated = dummy_datetime_iso,
        )
        hass_battery_state = HassState(
            entity_id = 'binary_sensor.motion_sensor_%s_battery' % self.insteon_address.replace( '.', '_' ),
            attributes = {
                "device_class": "battery",
                'friendly_name': f'{self.name} Battery',
                "insteon_address": self.insteon_address,
                "insteon_group": 1,
            },
            last_changed = dummy_datetime_iso,
            last_reported = dummy_datetime_iso,
            last_updated = dummy_datetime_iso,
        )
        return [ hass_motion_state,
                 hass_light_state,
                 hass_battery_state ]
    
    def to_api_list(self):
        return [ x.to_api_dict() for x in self.hass_state_list() ]

    
@dataclass( frozen = True )
class HassInsteonOpenCloseSensor( HassInsteonEntity ):

    @property
    def entity_type(self):
        return EntityType.OPEN_CLOSE_SENSOR

    def sim_state_list(self) -> List[ SimState ]:
        pass
    
    def hass_state_list(self):
        dummy_datetime_iso = datetimeproxy.now().isoformat()
        
        hass_state = HassState(
            entity_id = 'binary_sensor.open_close_sensor_%s' % self.insteon_address.replace( '.', '_' ),
            attributes = {
                "device_class": "door",
                'friendly_name': self.name,
                "icon": "mdi:door",
                "insteon_address": self.insteon_address,
                "insteon_group": 1,
            },
            last_changed = dummy_datetime_iso,
            last_reported = dummy_datetime_iso,
            last_updated = dummy_datetime_iso,
        )
        return [ hass_state ]
    
    def to_api_list(self):
        return [ x.to_api_dict() for x in self.hass_state_list() ]

    
HASS_SIM_ENTITY_DEFINITION_LIST = [
    SimEntityDefinition(
        sim_entity_class = HassInsteonLightSwitch,
        class_label = 'Insteon Light Switch',
    ),
    SimEntityDefinition(
        sim_entity_class = HassInsteonMotionDetector,
        class_label = 'Insteon Motion Detector',
    ),
    SimEntityDefinition(
        sim_entity_class = HassInsteonOpenCloseSensor,
        class_label = 'Insteon Open/Close Sensor',
    ),
]
