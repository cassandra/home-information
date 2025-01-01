from dataclasses import dataclass
from typing import List

from .models import DbSimEntity
from .base_models import SimEntityDefinition, SimEntityFields, SimState


@dataclass
class SimEntity:
    """
    These are the run-time instances created and managed by the
    SimulatorManager and Simulator classes.  These are the simulator
    entities chosen by the user from the provided SimEntityDefinition
    instances to define the run-time configuration of the simulator.
    """
    db_sim_entity          : DbSimEntity
    sim_entity_definition  : SimEntityDefinition

    def __post_init__(self):

        SimEntityFieldsSubclass = self.sim_entity_definition.sim_entity_fields_class
        self._sim_entity_fields = SimEntityFieldsSubclass.from_json_dict(
            self.db_sim_entity.sim_entity_fields_json,
        )
        self._sim_state_map = dict()
        for SimStateSubclass in self.sim_entity_definition.sim_state_class_list:
            sim_state = SimStateSubclass(
                simulator_id = self.db_sim_entity.simulator_id,
                sim_entity_id = self.db_sim_entity.id,
                sim_entity_fields = self._sim_entity_fields,
            )
            self._sim_state_map[sim_state.sim_state_id] = sim_state
            continue
        return
        
    @property
    def id(self):
        assert self.db_sim_entity.pk is not None
        return self.db_sim_entity.id

    @property
    def name(self):
        return self.sim_entity_fields.name
    
    @property
    def sim_entity_fields(self) -> SimEntityFields:
        return self._sim_entity_fields

    @property
    def sim_state_list(self) -> List[ SimState ]:
        sim_state_list = list( self._sim_state_map.values() )
        sim_state_list.sort( key = lambda item : item.name )
        return sim_state_list
    
    def set_sim_state( self,
                       sim_state_id   : str,
                       value_str      : str ) -> SimState:
        sim_state = self._sim_state_map.get( sim_state_id )
        sim_state.set_value_from_string( value_str = value_str )
        return sim_state
    
    def copy_state_values( self, other_sim_entity : 'SimEntity' ):
        for sim_state_id, self_sim_state in self._sim_state_map.items():
            other_sim_state = other_sim_entity._sim_state_map.get( sim_state_id )
            if other_sim_state:
                self_sim_state.value = other_sim_state.value
            continue
        return
