from typing import List, Set

from hi.simulator.base_models import SimEntityDefinition, SimEntityFields
from hi.simulator.exceptions import SimEntityValidationError
from hi.simulator.simulator import Simulator
from hi.simulator.sim_entity import SimEntity

from .sim_models import HASS_SIM_ENTITY_DEFINITION_LIST, HassInsteonSimEntityFields, HassState


class HassSimulator( Simulator ):

    @property
    def id(self):
        return 'hass'

    @property
    def label(self):
        return 'Home Assistant'

    def get_hass_sim_state_list( self ) -> List[ HassState ]:
        sim_state_list = list()
        for sim_entity in self.sim_entities:
            sim_state_list.extend( sim_entity.sim_state_list )
            continue
        return sim_state_list

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        return HASS_SIM_ENTITY_DEFINITION_LIST

    def validate_new_sim_entity_fields( self, new_sim_entity_fields : SimEntityFields ):
        if isinstance( new_sim_entity_fields, HassInsteonSimEntityFields ):
            self._validate_insteon_fields(
                candidate_sim_entity_fields = new_sim_entity_fields,
                exclude_sim_entity_ids = set(),
            )
        return
    
    def validate_updated_sim_entity( self, updated_sim_entity : SimEntity ):
        sim_entity_fields = updated_sim_entity.sim_entity_fields
        if isinstance( sim_entity_fields, HassInsteonSimEntityFields ):
            self._validate_insteon_fields(
                candidate_sim_entity_fields = updated_sim_entity.sim_entity_fields,
                exclude_sim_entity_ids = { updated_sim_entity.id },
            )
        return

    def _validate_insteon_fields( self,
                                  candidate_sim_entity_fields  : HassInsteonSimEntityFields,
                                  exclude_sim_entity_ids       : Set[ int ] ):

        existing_insteon_addresses = set()
        for sim_entity in self.sim_entities:
            if sim_entity.id in exclude_sim_entity_ids:
                continue
            sim_entity_fields = sim_entity.sim_entity_fields
            if isinstance( sim_entity_fields, HassInsteonSimEntityFields ):
                existing_insteon_addresses.add( sim_entity_fields.insteon_address )
            continue

        candidate_insteon_address = candidate_sim_entity_fields.insteon_address
        if candidate_insteon_address in existing_insteon_addresses:
            raise SimEntityValidationError(
                f'Insteon address "{candidate_insteon_address}" already used.'
            )
        return
