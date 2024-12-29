from typing import List, Set

from hi.simulator.base_models import SimEntityDefinition, SimEntityFields
from hi.simulator.exceptions import SimEntityValidationError
from hi.simulator.simulator import Simulator
from hi.simulator.sim_entity import SimEntity

from .sim_models import (
    ZONEMINDER_SIM_ENTITY_DEFINITION_LIST,
    ZmMonitorSimEntityFields,
    ZmServerSimEntityFields,
)


class ZoneMinderSimulator( Simulator ):
    
    @property
    def id(self):
        return 'zm'

    @property
    def label(self) -> str:
        return 'ZoneMinder'

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        return ZONEMINDER_SIM_ENTITY_DEFINITION_LIST
    
    def validate_new_sim_entity_fields( self, new_sim_entity_fields : SimEntityFields ):
        if isinstance( new_sim_entity_fields, ZmMonitorSimEntityFields ):
            self._validate_monitor_fields(
                candidate_sim_entity_fields = new_sim_entity_fields,
                exclude_sim_entity_ids = set(),
            )
        elif isinstance( new_sim_entity_fields, ZmServerSimEntityFields ):
            self._validate_server_fields(
                candidate_sim_entity_fields = new_sim_entity_fields,
                exclude_sim_entity_ids = set(),
            )
        return
    
    def validate_updated_sim_entity( self, updated_sim_entity : SimEntity ):
        sim_entity_fields = updated_sim_entity.sim_entity_fields
        if isinstance( sim_entity_fields, ZmMonitorSimEntityFields ):
            self._validate_monitor_fields(
                candidate_sim_entity_fields = sim_entity_fields,
                exclude_sim_entity_ids = { updated_sim_entity.id },
            )
        elif isinstance( sim_entity_fields, ZmServerSimEntityFields ):
            self._validate_server_fields(
                candidate_sim_entity_fields = sim_entity_fields,
                exclude_sim_entity_ids = { updated_sim_entity.id },
            )
        return

    def _validate_monitor_fields( self,
                                  candidate_sim_entity_fields  : ZmMonitorSimEntityFields,
                                  exclude_sim_entity_ids       : Set[ int ] ):
        existing_monitor_ids = set()
        existing_hosts = set()
        for sim_entity in self.sim_entities:
            if sim_entity.id in exclude_sim_entity_ids:
                continue
            sim_entity_fields = sim_entity.sim_entity_fields
            if isinstance( sim_entity_fields, ZmMonitorSimEntityFields ):
                existing_monitor_ids.add( sim_entity_fields.monitor_id )
                existing_hosts.add( sim_entity_fields.host )
            continue

        candidate_monitor_id = candidate_sim_entity_fields.monitor_id
        if candidate_monitor_id in existing_monitor_ids:
            raise SimEntityValidationError(
                f'Monitor id "{candidate_monitor_id}" already used.'
            )

        candidate_host = candidate_sim_entity_fields.host
        if candidate_host in existing_hosts:
            raise SimEntityValidationError(
                f'Host "{candidate_host}" already used.'
            )
        return

    def _validate_server_fields( self,
                                 candidate_sim_entity_fields  : ZmServerSimEntityFields,
                                 exclude_sim_entity_ids       : Set[ int ] ):
        for sim_entity in self.sim_entities:
            if sim_entity.id in exclude_sim_entity_ids:
                continue
            sim_entity_fields = sim_entity.sim_entity_fields
            if isinstance( sim_entity_fields, ZmServerSimEntityFields ):
                raise SimEntityValidationError(
                    'Only one ZM server should be defined.'
                )
            continue
        return
    
