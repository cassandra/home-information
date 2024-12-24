from typing import List, Type

from hi.apps.common.singleton import Singleton

from .transient_models import SimEntity, SimEntityClassWrapper


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
    
    def initialize( self, sim_entity_list : List[ SimEntity ] ):
        """
        The SimulatorManager stores, hydrates and defines the set of existing
        SimEntity instances a simulator will use.  This initialization will
        occur at start up and if/when the simulation profile changes
        (requiring a new list of SimEntity instances).
        """
        self._sim_entity_list = sim_entity_list
    
    @property
    def sim_entities(self) -> List[ SimEntity ]:
        return self._sim_entity_list

    def set_sim_state( self, device_id : int, value : str ):
        raise NotImplementedError('Subclasses must override this method.')
        
    @property
    def sim_entity_class_wrapper_list(self) -> List[ SimEntityClassWrapper ]:
        return [ SimEntityClassWrapper( sim_entity_class = x )
                 for x in self.get_sim_entity_class_list() ]
    
    def add_sim_entity( self, sim_entity : SimEntity ):
        self._sim_entity_list.append( sim_entity )    
    
