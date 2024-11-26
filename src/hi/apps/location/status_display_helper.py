from typing import Dict, List, Set

from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.sensor_response_manager import SensorResponseManager

from .enums import LocationViewType
from .models import LocationView
from .transient_models import StatusDisplayData


class StatusDisplayLocationHelper:

    def __init__( self, location_view : LocationView ):
        self._location_view_type = location_view.location_view_type
        self._entity_state_type_priority_list = self._location_view_type.entity_state_type_priority_list
        self._latest_sensor_response_list_map = SensorResponseManager().get_all_latest_sensor_responses()
        return

    def get_status_display_data_map(
            self,
            displayed_entities  : Set[ Entity ] ) -> Dict[ Entity, StatusDisplayData ]:
        if self._location_view_type == LocationViewType.SUPPRESS:
            return dict()
        
        entity_to_status_display_data = dict()
        for entity in displayed_entities:
            status_display_data = self.get_status_display_data( entity = entity )
            if not status_display_data:
                continue
            entity_to_status_display_data[entity] = status_display_data
            continue
        
        return entity_to_status_display_data

    def get_status_display_data( self, entity : Entity ) -> StatusDisplayData:

        entity_state_list = list( entity.states.all() )

        # Delegate entities include all their principal entity states as well.
        entity_state_delegations = entity.entity_state_delegations.select_related('entity_state').all()
        entity_state_list.extend([ x.entity_state for x in entity_state_delegations ])
        if not entity_state_list:
            return None

        entity_state_type_for_status = self._get_entity_state_type_for_status(
            entity_state_list = entity_state_list,
        )
        
        # N.B. An entity is not limited to a single EntityState per
        # EntityStateType, nor is a single EnttyStateType limited to a
        # single sensor.  In the (rare) cases there are multiples of these,
        # we will always use the most recent sensor response.
        
        candidate_sensors_for_status = set()
        for entity_state in entity_state_list:
            if entity_state.entity_state_type == entity_state_type_for_status:
                candidate_sensors_for_status.update( entity_state.sensors.all() )
            continue
        
        latest_sensor_response_list_list = list()
        sensor_map = dict()
        for sensor in candidate_sensors_for_status:
            latest_sensor_response_list = self._latest_sensor_response_list_map.get( sensor.integration_key )
            if latest_sensor_response_list:
                latest_sensor_response_list_list.append( latest_sensor_response_list )
                sensor_map[sensor.integration_key] = sensor
            continue
        
        if not latest_sensor_response_list_list:
            return None
        
        latest_sensor_response_list_list.sort( key = lambda item: item[0].timestamp, reverse = True )
        sensor_response_list_for_status = latest_sensor_response_list_list[0]
        sensor_for_status = sensor_map.get( sensor_response_list_for_status[0].integration_key )
        
        return StatusDisplayData(
            entity = entity,
            sensor = sensor_for_status,
            sensor_response_list = sensor_response_list_for_status,
        )

    def _get_entity_state_type_for_status( self, entity_state_list : List[ EntityState ] ) -> EntityStateType:
        entity_state_type_list = [ x.entity_state_type for x in entity_state_list ]

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
