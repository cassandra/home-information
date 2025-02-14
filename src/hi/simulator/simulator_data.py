from dataclasses import dataclass, field
from typing import Dict

from .base_models import SimEntityDefinition
from .simulator import Simulator

    
@dataclass
class SimulatorData:
    
    simulator                  : Simulator
    sim_entity_definition_map  : Dict[ str , SimEntityDefinition ]  = field( default_factory = dict )
