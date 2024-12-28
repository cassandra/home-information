from dataclasses import dataclass, field
from typing import Dict, List

from .base_models import SimEntityDefinition
from .simulator import Simulator
from .sim_entity import SimEntity

    
@dataclass
class SimulatorData:
    
    simulator                  : Simulator
    sim_entity_definition_map  : Dict[ str , SimEntityDefinition ]  = field( default_factory = dict )
    sim_entity_instance_list   : List[ SimEntity ]                  = field( default_factory = list )
