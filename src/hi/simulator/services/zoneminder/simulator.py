from typing import List

from hi.simulator.base_models import SimEntityDefinition
from hi.simulator.simulator import Simulator

from .sim_models import ZONEMINDER_SIM_ENTITY_DEFINITION_LIST


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
    
