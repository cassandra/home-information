from typing import Dict, List

from hi.apps.common.singleton import Singleton

from .base_models import SimEntityDefinition, SimEntityFields, SimState
from .sim_entity import SimEntity


class Simulator( Singleton ):
    """
    The class that each simulator should subclass and include in a
    simulator.py file in its app directory.  This is how the
    SimulatorManager discovers the types of simulator entities and states
    provided by the simulator.  This is also used by the simulators to get
    the current satte of which entities, states and state values currently
    are defined.
    """
    
    def __init_singleton__( self ):
        self.initialize()
        return
    
    @property
    def id(self) -> str:
        """ A unique identifier for referencing this simulator implementation. """
        raise NotImplementedError('Subclasses must override this method.')
        
    @property
    def label(self) -> str:
        """ A human-friendly label for this simulatior. """
        raise NotImplementedError('Subclasses must override this method.')

    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        """
        A return a list of SimEntity subclasses that define the different types
        of entities that can be define for the simulator.
        """
        raise NotImplementedError('Subclasses must override this method.')        

    @property
    def sim_entities(self) -> List[ SimEntity ]:
        sim_entity_list = [ x for x in self._sim_entity_map.values() ]
        sim_entity_list.sort( key = lambda item : item.name )
        return sim_entity_list

    def initialize( self ):
        """
        The SimulatorManager stores, hydrates and defines the set of existing
        SimEntity instances a simulator will use.  This initialization will
        occur at start up and if/when the simulation profile changes
        (requiring a new list of SimEntity instances).
        """
        self._sim_entity_map : Dict[ id, SimEntity ] = dict()
        return
    
    def validate_sim_entity_fields( self, sim_entity_fields : SimEntityFields ):
        """
        Subclasses should override this if there are additional validation
        checks needed before adding a SimEntity. This is called
        before persisting the data so can raise SimEntityValidationError if
        there are any validation issue.
        """
        return
        
    def validate_sim_entity( self, sim_entity : SimEntity ):
        """
        Subclasses should override this if there are additional validation
        checks needed before updating a SimEntity. This is called
        before persisting the data so can raise SimEntityValidationError if
        there are any validation issue.
        """
        return
        
    def add_sim_entity( self, sim_entity : SimEntity ):
        previous_sim_entity = self._sim_entity_map.get( sim_entity.id )
        if previous_sim_entity:
            sim_entity.copy_state_values( previous_sim_entity )
        self._sim_entity_map[sim_entity.id] = sim_entity
        return

    def remove_sim_entity_by_id( self, sim_entity_id : int ):
        del self._sim_entity_map[sim_entity_id]
        return

    def set_sim_state( self,
                       sim_entity_id  : int,
                       sim_state_idx  : int,
                       value_str      : str ) -> SimState:
        sim_entity = self._sim_entity_map[sim_entity_id]
        return sim_entity.set_sim_state(
            sim_state_idx = sim_state_idx,
            value_str = value_str,
        )


        
    
