from typing import List, Type

from hi.apps.common.singleton import Singleton

from .transient_models import SimEntity, SimEntityDefinition


class Simulator( Singleton ):

    def __init_singleton__( self ):
        self._sim_entity_list = list()
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
    
    def validate_new_sim_entity( self, sim_entity : SimEntity ):
        """
        Called before adding or updating a SimEntity to allow simulator to do
        custom validation checks before add/edit/save. Should raise
        SimEntityValidationError if there is any validation issue.
        """
        raise NotImplementedError('Subclasses must override this method.')        
        
    @property
    def sim_entities(self) -> List[ SimEntity ]:
        return self._sim_entity_list

    def initialize( self, sim_entity_list : List[ SimEntity ] ):
        """
        The SimulatorManager stores, hydrates and defines the set of existing
        SimEntity instances a simulator will use.  This initialization will
        occur at start up and if/when the simulation profile changes
        (requiring a new list of SimEntity instances).
        """
        self._sim_entity_list = sim_entity_list
        return
    
    def set_sim_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')
        
    def add_sim_entity( self, sim_entity : SimEntity ):
        self.validate_new_sim_entity( sim_entity = sim_entity )
        self._sim_entity_list.append( sim_entity )    
        return
    
    def update_sim_entity( self, sim_entity : SimEntity ):
        raise NotImplementedError('Need to work out who owns managing the data: SimulatorManager or Simulator.')
    
    def remove_sim_entity( self, sim_entity : SimEntity ):
        try:
            self._sim_entity_list.remove(sim_entity)
        except ValueError:
            pass
        return
