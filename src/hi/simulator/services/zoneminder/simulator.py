from typing import List, Type

from hi.simulator.transient_models import SimEntity, SimEntityDefinition
from hi.simulator.simulator import Simulator

from .transient_models import ZONEMINDER_SIM_ENTITY_DEFINITION_LIST


class ZoneMinderSimulator( Simulator ):
    
    @property
    def id(self):
        return 'zm'

    @property
    def label(self) -> str:
        return 'ZoneMinder'

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        return ZONEMINDER_SIM_ENTITY_DEFINITION_LIST

    def set_sim_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')

    def validate_new_sim_entity( self, sim_entity : SimEntity ):
        return
    
