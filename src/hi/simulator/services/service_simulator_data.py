from dataclasses import dataclass, field
from typing import Dict

from .base_models import SimEntityDefinition
from .service_simulator import ServiceSimulator

    
@dataclass
class ServiceSimulatorData:
    
    simulator                  : ServiceSimulator
    sim_entity_definition_map  : Dict[ str , SimEntityDefinition ]  = field( default_factory = dict )
