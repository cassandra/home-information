from typing import List

from hi.simulator.base_models import SimEntityDefinition
from hi.simulator.simulator import Simulator

from .sim_models import (
    HOMEBOX_SIM_ENTITY_DEFINITION_LIST,
    HomeBoxInventoryItemFields,
    HomeBoxItemArchivedState,
)


class HomeBoxSimulator( Simulator ):

    @property
    def id(self):
        return 'hb'

    @property
    def label(self):
        return 'HomeBox'

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        return HOMEBOX_SIM_ENTITY_DEFINITION_LIST

    def get_sim_entity_pairs(self):
        """
        Iterate (sim_entity_id, fields, archived_state) tuples for every
        configured HomeBox inventory item in the active profile. Used by
        the API views to build item responses.
        """
        for sim_entity in self._sim_entity_map.values():
            fields = sim_entity.sim_entity_fields
            if not isinstance( fields, HomeBoxInventoryItemFields ):
                continue
            archived_state = sim_entity._sim_state_map.get( 'archived' )
            if not isinstance( archived_state, HomeBoxItemArchivedState ):
                continue
            yield ( sim_entity.id, fields, archived_state )
