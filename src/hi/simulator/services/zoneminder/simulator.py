from typing import List, Set

from hi.simulator.base_models import SimEntityDefinition, SimEntityFields, SimState
from hi.simulator.exceptions import SimEntityValidationError
from hi.simulator.simulator import Simulator
from hi.simulator.sim_entity import SimEntity

from .enums import ZmMonitorFunction, ZmRunStateType
from .sim_models import (
    ZONEMINDER_SIM_ENTITY_DEFINITION_LIST,
    ZmSimMonitor,
    ZmMonitorFunctionState,
    ZmMonitorSimEntityFields,
    ZmMonitorMotionState,
    ZmSimServer,
    ZmServerSimEntityFields,
    ZmSimRunState,
    ZmSimRunStateDefinition,
)
from .zm_event_manager import ZmSimEventManager


class ZoneMinderSimulator( Simulator ):

    @property
    def id(self):
        return 'zm'

    @property
    def label(self) -> str:
        return 'ZoneMinder'

    def get_zm_monitor_sim_entity_list( self ) -> List[ ZmSimMonitor ]:
        return [ ZmSimMonitor( sim_entity = x ) for x in self.sim_entities
                 if x.sim_entity_definition.sim_entity_fields_class == ZmMonitorSimEntityFields ]

    def get_zm_server_sim_entity( self ) -> ZmSimServer:
        for sim_entity in self.sim_entities:
            if sim_entity.sim_entity_definition.sim_entity_fields_class == ZmServerSimEntityFields:
                return ZmSimServer( sim_entity = sim_entity )
            continue
        raise ValueError( 'No ZM server entity has been created.' )

    def get_zm_sim_run_state_list(self) -> List[ ZmSimRunState ]:

        # TODO: ZM allows run state states and its monitor functions to be
        # user-defined.  Changing the run state affects the monitor
        # function state(s), so it is non-trivial to add this to the
        # simulator. Deferring this work until there more need for this and
        # just using fixed list of run states and default monitor functions
        # for now.

        zm_server_sim_entity = self.get_zm_server_sim_entity()
        current_zm_run_state_value = zm_server_sim_entity.run_state_value
        zm_monitor_sim_entity_list = self.get_zm_monitor_sim_entity_list()

        zm_sim_run_state_list = list()
        for zm_run_state_idx, zm_run_state_type in enumerate( ZmRunStateType ):
            is_active = bool( current_zm_run_state_value == zm_run_state_type.name )
            definition_list = [
                ZmSimRunStateDefinition(
                    monitor_id = x.monitor_id,
                    monitor_function = ZmMonitorFunction.default_value(),
                ) for x in zm_monitor_sim_entity_list ]
            zm_sim_run_state = ZmSimRunState(
                zm_run_state_id = zm_run_state_idx,
                name = zm_run_state_type.name,
                definition_list = definition_list,
                is_active = is_active,
            )
            zm_sim_run_state_list.append( zm_sim_run_state )
            continue
        
        return zm_sim_run_state_list

    def set_monitor_function( self,
                              monitor_id           : int,
                              zm_monitor_function  : ZmMonitorFunction ) -> SimState:
        for sim_entity in self.sim_entities:
            if sim_entity.sim_entity_definition.sim_entity_fields_class == ZmMonitorSimEntityFields:
                zm_sim_monitor = ZmSimMonitor( sim_entity = sim_entity )
                if zm_sim_monitor.monitor_id == monitor_id:
                    return sim_entity.set_sim_state(
                        sim_state_id = ZmMonitorFunctionState.FUNCTION_SIM_STATE_ID,
                        value_str = zm_monitor_function.value,
                    )
            continue
        raise KeyError( f'ZM monitor with id "{monitor_id}" does not exist.' )
    
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
    
    def set_sim_state( self,
                       sim_entity_id  : int,
                       sim_state_id   : str,
                       value_str      : str ) -> SimState:
        """ Need to override this so we can track ZM events based on simulated motion changes. """
        
        sim_state = super().set_sim_state(
            sim_entity_id = sim_entity_id,
            sim_state_id = sim_state_id,
            value_str = value_str,
        )
        if isinstance( sim_state, ZmMonitorMotionState ):
            sim_entity = self.get_sim_entity_by_id( sim_entity_id = sim_entity_id )
            ZmSimEventManager().add_motion_value(
                zm_sim_monitor = ZmSimMonitor( sim_entity = sim_entity ),
                motion_value = sim_state.value,
            )
        return sim_state
        
