from typing import List

from hi.apps.common.singleton import Singleton

from .transient_models import EntityStateTransition


class EventDetector(Singleton):

    def __init_singleton__(self):
        return

    def add_entity_state_transitions( self, entity_state_transition_list : List[ EntityStateTransition ] ):

        return
                                      
 
