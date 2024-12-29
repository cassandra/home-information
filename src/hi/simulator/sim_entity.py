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
        self._sim_state_list = list()
        for sim_state_idx, SimStateSubclass in enumerate( self.sim_entity_definition.sim_state_class_list ):
            sim_state = SimStateSubclass(
                simulator_id = self.db_sim_entity.simulator_id,
                sim_entity_id = self.db_sim_entity.id,
                sim_state_idx = sim_state_idx,
                sim_entity_fields = self._sim_entity_fields,
            )
            self._sim_state_list.append( sim_state )
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
        return self._sim_state_list
    
    def set_sim_state( self,
                       sim_state_idx   : int,
                       value_str      : str ) -> SimState:
        sim_state = self._sim_state_list[sim_state_idx]
        sim_state.set_value_from_string( value_str = value_str )
        return sim_state
    
    def copy_state_values( self, other_sim_entity : 'SimEntity' ):
        for self_sim_state, other_sim_state in zip( self.sim_state_list,
                                                    other_sim_entity.sim_state_list ):
            assert self_sim_state.sim_state_idx == other_sim_state.sim_state_idx
            self_sim_state.value = other_sim_state.value
            continue
        return
