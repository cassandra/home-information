from typing import Dict


class HassState:

    def __init__( self, api_dict : Dict ):
        self._api_dict = api_dict
        return

    def __str__(self):
        return f'HassState: {self.entity_id}'
    
    def __repr__(self):
        return self.__str__()

    @property
    def entity_id(self):
        return self._api_dict.get( 'entity_id' )
    
    @property
    def attributes(self):
        attributes = self._api_dict.get( 'attributes' )
        if not attributes:
            attributes = dict()
        return attributes
    
    @property
    def insteon_address(self):
        return self.attributes.get( 'insteon_address' )

    @property
    def is_insteon(self):
        return bool( self.insteon_address is not None )
        
