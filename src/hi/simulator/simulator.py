from typing import List, Type

from hi.apps.common.singleton import Singleton

from .transient_models import SimEntity, SimEntityClassData


class Simulator( Singleton ):

    def __init_singleton__( self ):
        self._sim_entity_list = list()
        return
    
    @property
    def id(self) -> str:
        raise NotImplementedError('Subclasses must override this method.')
        
    @property
    def label(self) -> str:
        raise NotImplementedError('Subclasses must override this method.')

    def get_sim_entity_class_list(self) -> List[ Type[ SimEntity ]]:
        raise NotImplementedError('Subclasses must override this method.')        
    
    def validate_new_sim_entity( self, sim_entity : SimEntity ):
        """
        Called before adding a new SimEntity to allow simulator to validate
        before addition. Should raise SimEntityValidationError if there is an
        issue.
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
        
    @property
    def sim_entity_class_data_list(self) -> List[ SimEntityClassData ]:
        return [ SimEntityClassData( sim_entity_class = x ) for x in self.get_sim_entity_class_list() ]

    def add_sim_entity( self, sim_entity : SimEntity ):
        self.validate_new_sim_entity( sim_entity = sim_entity )
        self._sim_entity_list.append( sim_entity )    
        return
    
    def remove_sim_entity( self, sim_entity : SimEntity ):
        try:
            self._sim_entity_list.remove(sim_entity)
        except ValueError:
            pass
        return
