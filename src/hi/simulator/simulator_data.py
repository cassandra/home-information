from dataclasses import dataclass, field
from typing import Dict, Type

from .models import DbSimEntity
from .simulator import Simulator
from .transient_models import SimEntity

    
@dataclass
class SimulatorData:
    
    simulator                : Simulator
    sim_entity_class_map     : Dict[ str , Type[ SimEntity ]]  = field( default_factory = dict )
    sim_entity_instance_map  : Dict[ SimEntity, DbSimEntity ]  = field( default_factory = dict )
