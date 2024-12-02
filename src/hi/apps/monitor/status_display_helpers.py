from typing import Dict, List, Set, Sequence

from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.enums import LocationViewType
from hi.apps.location.models import LocationView
from hi.apps.sense.models import Sensor
from hi.apps.sense.sensor_response_manager import SensorResponseManager

from .status_display_data import StatusDisplayData
from .transient_models import EntityStatusData, EntityStateStatusData


class StatusDisplayLocationHelper:

    def __init__( self, location_view : LocationView ):
        self._location_view_type = location_view.location_view_type
        self._entity_state_type_priority_list = self._location_view_type.entity_state_type_priority_list
        return

    def get_status_entity_states_map( self, entities  : Set[ Entity ] ) -> Dict[ Entity, EntityState ]:
        if self._location_view_type == LocationViewType.SUPPRESS:
            return dict()
        
        entity_to_entity_states_data = dict()
        for entity in entities:
            entity_states = self.get_status_entity_states( entity = entity )
            if entity_states:
                entity_to_entity_states_data[entity] = entity_states
            continue
        
        return entity_to_entity_states_data

    def get_status_entity_states( self, entity : Entity ) -> List[ EntityState ]:

        # Delegate entities include will include all their principal entity
        # states, though any direct state will take precendence

        delegations_queryset = entity.entity_state_delegations.select_related('entity_state').all()
        all_entity_states = [ x.entity_state for x in delegations_queryset ]
        all_entity_states.extend( entity.states.all() )

        entity_state_list_map = dict()
        for entity_state in all_entity_states:
            if entity_state.entity_state_type not in entity_state_list_map:
                entity_state_list_map[entity_state.entity_state_type] = list()
            entity_state_list_map[entity_state.entity_state_type].append( entity_state )
            continue

        if not entity_state_list_map:
            return None

        entity_state_type_for_status = self._get_entity_state_type_for_status(
            entity_state_types = entity_state_list_map.keys(),
        )
        entity_state_list = entity_state_list_map.get( entity_state_type_for_status )

        return entity_state_list

    def _get_entity_state_type_for_status(
            self,
            entity_state_types : Sequence[ EntityStateType ] ) -> EntityStateType:

        for priority_entity_state_type in self._entity_state_type_priority_list:
            if priority_entity_state_type in entity_state_types:
                return priority_entity_state_type
            continue

        # If no prioritizes state type matches, then fallback to an
        # arbitrary, but deterministic choice by using all defined values.
        #
        for default_entity_state_type in EntityStateType:
            if default_entity_state_type in entity_state_types:
                return default_entity_state_type
            continue

        # This code should not really be reachable. Should always match one in fallback case.
        return None
    

class StatusDisplayStatusViewHelper:
    
    def get_status_display_data( self ) -> List[ StatusDisplayData ]:

        sensor_to_sensor_response_list = SensorResponseManager().get_all_latest_sensor_responses()
        
        # Since a given EntityState can have zero or more sensors, for each
        # EntityState, we need to collate all the sensor values to find the
        # latest status.
        
        entity_state_to_sensor_response_list = dict()
        for sensor, sensor_response_list in sensor_to_sensor_response_list.items():
            if sensor.entity_state not in entity_state_to_sensor_response_list:
                entity_state_to_sensor_response_list[sensor.entity_state] = list()
                entity_state_to_sensor_response_list[sensor.entity_state].extend( sensor_response_list )
            continue

        status_display_data_list = list()
        for entity_state, sensor_response_list in entity_state_to_sensor_response_list.items():
            sensor_response_list.sort( key = lambda item: item.timestamp, reverse = True )
            status_display_data = StatusDisplayData(
                entity_state = entity_state,
                sensor_response_list = sensor_response_list,
            )
            status_display_data_list.append( status_display_data )
            continue

        return status_display_data_list


class StatusDisplayEntityHelper:
    
    def get_entity_status_data( self,
                                entity      : Entity,
                                is_editing  : bool ) -> EntityStatusData:

        entity_state_set = set( entity.states.all() )

        for entity_state_delegation in entity.entity_state_delegations.all():
            entity_state_set.add( entity_state_delegation.entity_state )
            continue
        
        entity_state_to_sensor_list = dict()
        
        sensor_list = list()
        for entity_state in entity_state_set:
            entity_state_sensor_list = list( entity_state.sensors.all() )
            entity_state_to_sensor_list[entity_state] = entity_state_sensor_list
            sensor_list.extend( entity_state_sensor_list )
            continue
        
        if not is_editing:
            sensor_response_list_map = SensorResponseManager().get_latest_sensor_responses(
                sensor_list = sensor_list,
            )
        else:
            sensor_response_list_map = dict()
        
        entity_state_status_data_list = list()
        for entity_state in entity_state_set:
            entity_state_sensor_response_list = list()
            for sensor in entity_state_to_sensor_list.get( entity_state ):
                sensor_response_list = sensor_response_list_map.get( sensor )
                if sensor_response_list:
                    entity_state_sensor_response_list.extend( sensor_response_list )
                continue
            entity_state_sensor_response_list.sort( key = lambda item: item.timestamp, reverse = True )

            controller_list = list( entity_state.controllers.all() )
            
            entity_state_status_data = EntityStateStatusData(
                entity_state = entity_state,
                sensor_response_list = entity_state_sensor_response_list,
                controller_list = controller_list,
            )
            entity_state_status_data_list.append( entity_state_status_data )
            continue

        return EntityStatusData(
            entity = entity,
            entity_state_status_data_list = entity_state_status_data_list,
        )

