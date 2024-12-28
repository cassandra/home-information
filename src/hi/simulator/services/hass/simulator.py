from typing import List

from hi.simulator.simulator import Simulator
from hi.simulator.base_models import SimEntityDefinition

from .transient_models import HASS_SIM_ENTITY_DEFINITION_LIST


class HassSimulator( Simulator ):

    @property
    def id(self):
        return 'hass'

    @property
    def label(self):
        return 'Home Assistant'

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        return HASS_SIM_ENTITY_DEFINITION_LIST

    def set_sim_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')

    
