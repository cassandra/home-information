from typing import Dict, List

from hi.apps.common.singleton import Singleton

from .base_models import SimEntityDefinition, SimEntityFields, SimState
from .sim_entity import SimEntity


class Simulator( Singleton ):
    """
    Defining a Simulator

    - Each simulator should subclass this in a file named "simulator.py" in
      its app directory.

    - The simulator's app directory should be located in the "simulator/services"
      subdirectory.

    - The SimulatorManager will auto-discovery all simulators with a
      simulator.py file in that services directopry.

    - The simulator should also define a urls.py and views.py file with the
      needed API endpoints.

    - The urls.py will also be auto-discovered by logic in the
      simulator/urls.py file

    Responsibilities

    - A simulator must provide a list of SimEntityDefinition instances via
      overriding the sim_entity_definition_list() method.  This tells the
      simulator the available types of simulator entities that are
      available to be defined, what extra custrom fields it needs and the
      list of SimState types the entity contains.

    - SimState instances is what the simulator UI shows as manually
      adjustable.  The API views of the simulator should convert those
      entities and current state values into the proper API responses.

    - The SimulatorManager is responsible for creating SimEntity instances
      and for updating the values of then SimState instances.

    - SimEntity definitions are persisted in the database with DbSimEntity,
      but ther SimState definitions and values are not persisted. e.g., A
      simulator server restart will lose any current SimState values.

    - The SimulatorManager also supports defining and switching between
      different simulation profiles, each with its own set of SimEntity
      definitions.  The individual simulator subclasses do not need to be
      aware of this as the SimulatorManager creates a new simulator
      subclass instance for each profile.

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

    def get_sim_entity_by_id( self, sim_entity_id : int ) -> SimEntity:
        if sim_entity_id not in self._sim_entity_map:
            raise KeyError( f'No simulator ewntity found with id = {sim_entity_id}' )
        return self._sim_entity_map.get( sim_entity_id )
        
    def initialize( self ):
        """
        The SimulatorManager stores, hydrates and defines the set of existing
        SimEntity instances a simulator will use.  This initialization will
        occur at start up and if/when the simulation profile changes
        (requiring a new list of SimEntity instances).
        """
        self._sim_entity_map : Dict[ id, SimEntity ] = dict()
        return
    
    def validate_new_sim_entity_fields( self, new_sim_entity_fields : SimEntityFields ):
        """
        Subclasses should override this if there are additional validation
        checks needed before adding a SimEntity. This is called
        before persisting the data so can raise SimEntityValidationError if
        there are any validation issue.
        """
        return
        
    def validate_updated_sim_entity( self, updated_sim_entity : SimEntity ):
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
                       sim_state_id   : str,
                       value_str      : str ) -> SimState:
        sim_entity = self.get_sim_entity_by_id( sim_entity_id = sim_entity_id )
        return sim_entity.set_sim_state(
            sim_state_id = sim_state_id,
            value_str = value_str,
        )


        
    
