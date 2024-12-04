import logging
from typing import Dict, List

from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity

from .models import Controller, ControllerHistory

logger = logging.getLogger(__name__)


class ControllerHistoryManager( Singleton ):
    
    ENTITY_STATE_HISTORY_ITEM_MAX = 5
    
    def __init_singleton__( self ):
        return
    
    def add_to_controller_history( self, controller : Controller, value : str ):
        if not controller.persist_history:
            return

        return ControllerHistory.objects.create(
            controller = controller,
            value = value,
        )
        
    def get_latest_entity_controller_history(
            self,
            entity     : Entity,
            max_items  : int    = 5 ) -> Dict[ Controller, List[ ControllerHistory ] ]:

        entity_state_list = list( entity.states.all() )
        entity_state_delegations = entity.entity_state_delegations.select_related('entity_state').all()
        entity_state_list.extend([ x.entity_state for x in entity_state_delegations ])

        controller_list = list()
        for entity_state in entity_state_list:
            controller_list.extend( entity_state.controllers.all() )
            continue

        controller_history_list_map = dict()
        for controller in controller_list:
            controller_history_list = ControllerHistory.objects.filter( controller = controller )[0:max_items]
            controller_history_list_map[controller] = controller_history_list
            continue

        return controller_history_list_map
