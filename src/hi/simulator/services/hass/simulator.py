from typing import List, Type

from hi.simulator.simulator import Simulator
from hi.simulator.transient_models import SimEntity

from .transient_models import HASS_SIM_ENTITY_LIST


class HassSimulator( Simulator ):

    @property
    def id(self):
        return 'hass'

    @property
    def label(self):
        return 'Home Assistant'

    def get_sim_entity_class_list(self) -> List[ Type[ SimEntity ]]:
        return HASS_SIM_ENTITY_LIST

    def set_sim_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')

    def validate_new_sim_entity( self, sim_entity : SimEntity ):
        # TODO: Ensure no duplicate Insteon addresses
        return

    
