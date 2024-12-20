from typing import List, Type

from hi.simulator.transient_models import SimEntity
from hi.simulator.simulator import Simulator

from .transient_models import HassInsteonLightSwitch


class HassSimulator( Simulator ):

    @property
    def id(self):
        return 'hass'

    @property
    def label(self):
        return 'Home Assistant'

    def get_sim_entity_class_list(self) -> List[ Type[ SimEntity ]]:
        return [
            HassInsteonLightSwitch,
        ]

    def initialize( self, sim_entity_list : List[ SimEntity ] ):
        return
    
    @property
    def sim_entities(self) -> List[ SimEntity ]:
        return []

    def set_sim_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')
        
