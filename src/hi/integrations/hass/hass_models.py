from dataclasses import dataclass
from typing import Dict


@dataclass
class HassState:
    """ Wraps the JSON object from the API """

    api_dict                 : Dict
    entity_id                : str
    entity_id_prefix         : str
    entity_name_sans_prefix  : str
    entity_name_sans_suffix  : str

    def __str__(self):
        return f'HassState: {self._entity_id}'
    
    def __repr__(self):
        return self.__str__()

    @property
    def attributes(self):
        attributes = self._api_dict.get( 'attributes' )
        if not attributes:
            attributes = dict()
        return attributes

    @property
    def friendly_name(self):
        return self.attributes.get( 'friendly_name' )

    @property
    def device_class(self):
        return self.attributes.get( 'device_class' )

    @property
    def insteon_address(self):
        return self.attributes.get( 'insteon_address' )
    
    @property
    def unit_of_measurement(self):
        return self.attributes.get( 'unit_of_measurement' )

    @property
    def options(self):
        return self.attributes.get( 'options' )

    @property
    def is_insteon(self):
        return bool( self.insteon_address is not None )
        

class HassDevice:
    """ An aggregate of one or more HassStates associated with a single device. """
    
    def __init__( self, device_id : str ):
        self._device_id = device_id
        self._state_list = list()
        return

    def __str__(self):
        return f'HassDevice: {self.device_id}'
    
    def __repr__(self):
        return self.__str__()

    @property
    def device_id(self):
        return self._device_id

    def add_state( self, hass_state : HassState ):
        self._state_list.append( hass_state )
        return

    def to_dict(self):
        return {
            'device_id': self.device_id,
            'num_states': len(self._state_list),
            'prefixes': [ x.entity_id_prefix for x in self._state_list ],
            'states': [ x.api_dict for x in self._state_list ],
        }
