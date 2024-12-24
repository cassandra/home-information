from typing import List, Type

from hi.simulator.transient_models import SimEntity
from hi.simulator.simulator import Simulator

from .transient_models import ZONEMINDER_SIM_ENTITY_LIST


class ZoneMinderSimulator( Simulator ):
    
    @property
    def id(self):
        return 'zm'

    @property
    def label(self) -> str:
        return 'ZoneMinder'

    def get_sim_entity_class_list(self) -> List[ Type[ SimEntity ]]:
        return ZONEMINDER_SIM_ENTITY_LIST

    def set_sim_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')
        
