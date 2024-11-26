from typing import Dict, List, Set

from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.enums import LocationViewType
from hi.apps.location.models import LocationView
from hi.apps.monitor.status_display_data import StatusDisplayData
from hi.apps.sense.sensor_response_manager import SensorResponseManager


class StatusDisplayLocationHelper:

    def __init__( self, location_view : LocationView ):
        self._location_view_type = location_view.location_view_type
        self._entity_state_type_priority_list = self._location_view_type.entity_state_type_priority_list
        return

    def get_status_entity_state_map( self, entities  : Set[ Entity ] ) -> Dict[ Entity, EntityState ]:
        if self._location_view_type == LocationViewType.SUPPRESS:
            return dict()
        
        entity_to_entity_state_data = dict()
        for entity in entities:
            entity_state = self.get_status_entity_state( entity = entity )
            if entity_state:
                entity_to_entity_state_data[entity] = entity_state
            continue
        
        return entity_to_entity_state_data

    def get_status_entity_state( self, entity : Entity ) -> EntityState:

        entity_state_type_map = dict()

        # Delegate entities include will include all their principal entity
        # states, though any direct state will take precendence
        
        delegations_queryset = entity.entity_state_delegations.select_related('entity_state').all()
        for entity_state_delegation in delegations_queryset:
            entity_state = entity_state_delegation.entity_state
            entity_state_type_map[entity_state.entity_state_type] = entity_state
            continue

        states_queryset = entity.states.all()
        for entity_state in states_queryset:
            entity_state_type_map[entity_state.entity_state_type] = entity_state
            continue

        if not entity_state_type_map:
            return None

        entity_state_type_for_status = self._get_entity_state_type_for_status(
            entity_states = entity_state_type_map.values(),
        )

        return entity_state_type_map.get( entity_state_type_for_status )

    def _get_entity_state_type_for_status( self, entity_states : List[ EntityState ] ) -> EntityStateType:
        entity_state_type_list = [ x.entity_state_type for x in entity_states ]

        for priority_entity_state_type in self._entity_state_type_priority_list:
            if priority_entity_state_type in entity_state_type_list:
                return priority_entity_state_type
            continue

        # If no prioritizes state type matches, then fallback to an
        # arbitrary, but deterministic choice by using all defined values.
        #
        for default_entity_state_type in EntityStateType:
            if default_entity_state_type in entity_state_type_list:
                return default_entity_state_type
            continue

        # This code should not really be reachable. Should always match one in fallback case.
        return None
    

class StatusDisplayStatusViewHelper:
    
    def get_status_display_data( self ) -> List[ StatusDisplayData ]:

        sensor_response_list_map = SensorResponseManager().get_all_latest_sensor_responses()

        # Since a given EntityState can have zero or more sensors, for each
        # EntityState, we need to collate all the sensor values to find the
        # latest status.
        
        entity_state_sensor_response_list_map = dict()
        for sensor, sensor_response_list in sensor_response_list_map.items():
            if sensor.entity_state not in entity_state_sensor_response_list_map:
                entity_state_sensor_response_list_map[sensor.entity_state] = list()
                entity_state_sensor_response_list_map[sensor.entity_state].extend( sensor_response_list )
            continue

        status_display_data_list = list()
        for entity_state, sensor_response_list in entity_state_sensor_response_list_map.items():
            sensor_response_list.sort( key = lambda item: item.timestamp, reverse = True )
            status_display_data = StatusDisplayData(
                entity_state = entity_state,
                sensor_response_list = sensor_response_list,
            )
            status_display_data_list.append( status_display_data )
            continue

        return status_display_data_list
