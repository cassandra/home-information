import base64
from dataclasses import dataclass, field
from datetime import datetime
import os
import time
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy


@dataclass
class HassEntity:

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
    

@dataclass
class HassDevice:

    friendly_name   : str

    def to_api_list(self) -> List[ HassEntity ]:
        raise NotImplementedError('Subclasses must override this.')

    
@dataclass
class HassInsteonDevice( HassDevice ):

    insteon_address  : str

    
@dataclass
class HassInsteonLightSwitch( HassInsteonDevice ):

    def entity_list(self):
        dummy_datetime_iso = datetimeproxy.now().isoformat()
        
        hass_entity = HassEntity(
            entity_id = 'light.switchlinc_relay_%s' % self.insteon_address.replace( '.', '_' ),
            attributes = {
                'color_mode': 'onoff',
                'friendly_name': self.friendly_name,
                'supported_color_modes': [
                    'onoff',
                ],
                'supported_features': 0,
            },
            last_changed = dummy_datetime_iso,
            last_reported = dummy_datetime_iso,
            last_updated = dummy_datetime_iso,
        )
        return [ hass_entity ]
    
    def to_api_list(self):
        return [ x.to_api_dict() for x in self.entity_list() ]
