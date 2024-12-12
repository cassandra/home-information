from cachetools import TTLCache
from typing import Dict, List, Set, Sequence

from hi.apps.control.transient_models import ControllerData
from hi.apps.common.singleton import Singleton
from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.enums import LocationViewType
from hi.apps.location.models import LocationView
from hi.apps.sense.models import Sensor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse

from .status_display_data import StatusDisplayData
from .transient_models import EntityStatusData, EntityStateStatusData


class StatusDisplayManager( Singleton, SensorResponseMixin ):

    STATUS_VALUE_OVERRIDES_SECS = 11

    def __init_singleton__( self ):
        self._status_value_overrides = TTLCache(
            maxsize = 100,
            ttl = self.STATUS_VALUE_OVERRIDES_SECS,
        )
        return

    def get_status_css_class_update_map( self ) -> Dict[ str, str ]:

        entity_state_status_data_list = self.get_all_entity_state_status_data_list()
        status_display_data_list = [ StatusDisplayData(x) for x in entity_state_status_data_list ]

        css_class_update_map = dict()
        for status_display_data in status_display_data_list:
            if status_display_data.should_skip:
                continue
            css_class_update_map[status_display_data.css_class] = status_display_data.attribute_dict
            continue

        return css_class_update_map
        
    def get_all_entity_state_status_data_list( self ) -> List[ EntityStateStatusData ]:
        """
        Gets the latest sensor responses for all EntityStates.  Used by client
        background polling to refresh the UI visual display of the current
        state.
        """
        
        sensor_to_sensor_response_list = self._get_latest_sensor_responses_helper()
        
        # Since a given EntityState can have zero or more sensors, for each
        # EntityState, we need to collate all the sensor values to find the
        # latest status.
        #
        # For a given EntityState, we do not display multiple sensors if it
        # has them. The display for the state uses an amalgam of all those
        # sensors where the most recent response determines the current
        # state.

        # Collate latest sensor responses by EntityState.
        #
        entity_state_to_sensor_response_list = dict()
        for sensor, sensor_response_list in sensor_to_sensor_response_list.items():
            if sensor.entity_state not in entity_state_to_sensor_response_list:
                entity_state_to_sensor_response_list[sensor.entity_state] = list()
            entity_state_to_sensor_response_list[sensor.entity_state].extend( sensor_response_list )
            continue

        # Find the latest sensor response for each EntityState and create
        # the EntityStateStatusData instance for each.
        #
        entity_state_status_data_list = list()
        for entity_state, sensor_response_list in entity_state_to_sensor_response_list.items():
            sensor_response_list.sort( key = lambda item: item.timestamp, reverse = True )
            latest_sensor_response = sensor_response_list[0]

            controller_data_list = [
                ControllerData(
                    controller = controller,
                    latest_sensor_response = latest_sensor_response,
                )
                for controller in entity_state.controllers.all()
            ]
            entity_state_status_data = EntityStateStatusData(
                entity_state = entity_state,
                sensor_response_list = sensor_response_list,
                controller_data_list = controller_data_list,
            )
            entity_state_status_data_list.append( entity_state_status_data )
            continue

        return entity_state_status_data_list

    def get_entity_status_data( self, entity : Entity ) -> EntityStatusData:

        # The set of entity states used to define the state includes the
        # principals when the entity is a delegate.
        #
        entity_state_set = set( entity.states.all() )
        for entity_state_delegation in entity.entity_state_delegations.all():
            entity_state_set.add( entity_state_delegation.entity_state )
            continue

        entity_state_to_status_data = self._get_entity_state_to_entity_state_status_data(
            entity_states = entity_state_set,
        )
        return EntityStatusData(
            entity = entity,
            entity_state_status_data_list = list( entity_state_to_status_data.values() ),
        )

    def get_entity_status_data_list(
            self,
            entities : Sequence[ Entity ] ) -> List[ EntityStatusData ]:
        """ 
        Same as _get_entity_to_entity_status_data() but returns a List instead of a Dict.
        Preserves the ordering so resulting list in same order as input list.
        """
        
        entity_to_entity_status_data = self._get_entity_to_entity_status_data(
            entities = entities,
        )

        # Reform dict values as a list matching input list order and ensure
        # each entity has EntityStatusData (even if there are no latest
        # sensor responses).
        #
        entity_status_data_list = list()
        for entity in entities:
            entity_status_data = entity_to_entity_status_data.get( entity )
            if not entity_status_data:
                entity_status_data = EntityStatusData(
                    entity = entity,
                    entity_state_status_data_list = list()
                )
            entity_status_data_list.append( entity_status_data )
            continue
        return entity_status_data_list
    
    def _get_entity_to_entity_status_data(
            self,
            entities : Sequence[ Entity ] ) -> Dict[ Entity, EntityStatusData ]:

        # Gather all EntityStates for all Entities so we can issue a single
        # fetch of the latest SensorResponses.
        #
        entity_to_entity_state_set = { x: set( x.states.all() ) for x in entities }
        all_entity_states = set()
        for entity, entity_state_set in entity_to_entity_state_set.items():
            all_entity_states.update( entity_state_set )
            for entity_state_delegation in entity.entity_state_delegations.all():
                entity_state_set.add( entity_state_delegation.entity_state )
                all_entity_states.add( entity_state_delegation.entity_state )
                continue
            continue

        # Includes a single fetch for getting all latest sensor data.
        #
        entity_state_to_status_data = self._get_entity_state_to_entity_state_status_data(
            entity_states = all_entity_states,
        )
        
        # Collate EntityStateStatusData by Entity
        #
        entity_to_entity_status_data = dict()
        for entity_state, entity_state_status_data in entity_state_to_status_data.items():
            entity = entity_state.entity
            if entity not in entity_to_entity_status_data:
                entity_status_data = EntityStatusData(
                    entity = entity,
                    entity_state_status_data_list = list()
                )
                entity_to_entity_status_data[entity] = entity_status_data
            entity_to_entity_status_data[entity].entity_state_status_data_list.append(
                entity_state_status_data
            )
            continue

        return entity_to_entity_status_data

    def _get_entity_state_to_entity_state_status_data(
            self,
            entity_states : Sequence[ EntityState ] ) -> Dict[ EntityState, EntityStateStatusData ]:

        # Collect all the sensors for al the input EntityStates, so we can
        # issue one fetch of the latest SensorData.
        #
        entity_state_to_sensor_list = dict()
        all_sensor_list = list()
        for entity_state in entity_states:
            entity_state_sensor_list = list( entity_state.sensors.all() )
            entity_state_to_sensor_list[entity_state] = entity_state_sensor_list
            all_sensor_list.extend( entity_state_sensor_list )
            continue
        
        # Single fetch for getting all latest sensor data.
        #
        sensor_to_sensor_response_list = self._get_latest_sensor_responses_helper(
            sensor_list = all_sensor_list,
        )

        # Collates SensorResponses by EntityState, finds latest
        # SensorResponse and creates the EntityStateStatusData instances.
        #
        entity_state_to_entity_state_status_data_map = dict()
        for entity_state in entity_states:
            entity_state_sensor_response_list = list()
            for sensor in entity_state_to_sensor_list.get( entity_state ):
                sensor_response_list = sensor_to_sensor_response_list.get( sensor )
                if sensor_response_list:
                    entity_state_sensor_response_list.extend( sensor_response_list )
                continue
            entity_state_sensor_response_list.sort( key = lambda item: item.timestamp, reverse = True )

            if entity_state_sensor_response_list:
                latest_sensor_response = entity_state_sensor_response_list[0]
            else:
                latest_sensor_response = None
                
            controller_data_list = list()
            for controller in entity_state.controllers.all():
                controller_data = ControllerData(
                    controller = controller,
                    latest_sensor_response = latest_sensor_response,
                )
                controller_data_list.append( controller_data )
                continue
            
            entity_state_status_data = EntityStateStatusData(
                entity_state = entity_state,
                sensor_response_list = entity_state_sensor_response_list,
                controller_data_list = controller_data_list,
            )
            entity_state_to_entity_state_status_data_map[entity_state] = entity_state_status_data
            continue
        
        return entity_state_to_entity_state_status_data_map

    def get_entity_to_entity_state_status_data_list(
            self,
            location_view  : LocationView,
            entities       : Set[ Entity ] ) -> Dict[ Entity, List[ EntityStateStatusData ] ]:
        """
        Builds a map from Entity to EntityStateStatusData for the single EntityState
        that is the highest display priority for the given
        LocationView. i.e., Picks a single EntityState for each Entity to
        define the visual display used in the LocationView where we can
        really only represent one thing at a time (visually).
        """
        
        location_view_type = location_view.location_view_type
        if location_view_type == LocationViewType.SUPPRESS:
            return dict()
        
        entity_to_entity_state_list = self._get_entity_to_entity_state_list(
            location_view = location_view,
            entities = entities,
        )
        all_entity_states = set()
        for entity_state_list in entity_to_entity_state_list.values():
            all_entity_states.update( entity_state_list )
            continue
        
        entity_state_to_status_data = self._get_entity_state_to_entity_state_status_data(
            entity_states = all_entity_states,
        )

        entity_to_entity_state_status_data_list = dict()
        for entity, entity_state_list in entity_to_entity_state_list.items():
            if entity not in entity_to_entity_state_status_data_list:
                entity_to_entity_state_status_data_list[entity] = list()
            for entity_state in entity_state_list:
                entity_state_status_data = entity_state_to_status_data.get( entity_state )
                if entity_state_status_data:
                    entity_to_entity_state_status_data_list[entity].append( entity_state_status_data )
                continue
            continue

        return entity_to_entity_state_status_data_list

    def _get_entity_to_entity_state_list(
            self,
            location_view  : LocationView,
            entities       : Set[ Entity ] ) -> Dict[ Entity, List[ EntityState ] ]:
        """
        A map from Entity to EntityState for the list of EntityState with
        EntityStateTyoe that is the highest display priority for the given
        LocationView.
        """
        location_view_type = location_view.location_view_type
        if location_view_type == LocationViewType.SUPPRESS:
            return dict()
        
        entity_state_type_priority_list = location_view_type.entity_state_type_priority_list
        
        entity_to_entity_state_list = dict()
        for entity in entities:
            entity_state_list = self._get_entity_state_list_for_status(
                entity = entity,
                entity_state_type_priority_list = entity_state_type_priority_list,
            )
            if entity_state_list:
                entity_to_entity_state_list[entity] = entity_state_list
            continue
        
        return entity_to_entity_state_list

    def _get_entity_state_list_for_status(
            self,
            entity                           : Entity,
            entity_state_type_priority_list  : List[ EntityStateType ] ) -> List[ EntityState ]:
        """
        Finds all EntityState for the highest priority EntityStateType.
        """

        # Delegate entities include will include all their principal entity
        # states, though any direct state will take precendence

        delegations_queryset = entity.entity_state_delegations.select_related('entity_state').all()
        all_entity_states = [ x.entity_state for x in delegations_queryset ]
        all_entity_states.extend( entity.states.all() )

        # Gather all possible EntityStateType for the Entity and its pricipals.
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
            entity_state_type_priority_list = entity_state_type_priority_list,
        )
        entity_state_list = entity_state_list_map.get( entity_state_type_for_status )

        return entity_state_list

    def _get_entity_state_type_for_status(
            self,
            entity_state_types               : Sequence[ EntityStateType ],
            entity_state_type_priority_list  : List[ EntityStateType ] ) -> EntityStateType:
        """
        Determines the single EntityStateType that is the highest display priority
        from the given priority list.
        """

        for priority_entity_state_type in entity_state_type_priority_list:
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

    def get_latest_sensor_response( self, entity_state : EntityState ) -> SensorResponse:
        sensor_list = list( entity_state.sensors.all() )
        
        sensor_to_sensor_response_list = self._get_latest_sensor_responses_helper(
            sensor_list = sensor_list,
        )
        entity_state_sensor_response_list = list()
        for sensor in sensor_list:
            sensor_response_list = sensor_to_sensor_response_list.get( sensor )
            if sensor_response_list:
                entity_state_sensor_response_list.extend( sensor_response_list )
            continue
        entity_state_sensor_response_list.sort( key = lambda item: item.timestamp, reverse = True )

        if entity_state_sensor_response_list:
            return entity_state_sensor_response_list[0]

        return None

    def _get_latest_sensor_responses_helper(
            self,
            sensor_list : List[ Sensor ] = None ) -> Dict[ Sensor, List[ SensorResponse ] ] :
        sensor_response_manager = self.sensor_response_manager()
        
        if sensor_list is None:
            sensor_to_sensor_response_list = sensor_response_manager.get_all_latest_sensor_responses()
        else:
            sensor_to_sensor_response_list = sensor_response_manager.get_latest_sensor_responses(
                sensor_list = sensor_list,
            )

        for sensor, sensor_response_list in sensor_to_sensor_response_list.items():
            if ( not sensor_response_list
                 or ( sensor.entity_state.id not in self._status_value_overrides )):
                continue
            sensor_response_list[0].value = self._status_value_overrides[sensor.entity_state.id]
            continue

        return sensor_to_sensor_response_list
        
    def add_entity_state_value_override( self,
                                         entity_state    : EntityState,
                                         override_value  : str ):
        """
        Add a temporary override when values is explicitly chnaged by a controller to
        compensate for the delays in value updates from the polling intervals.
        """
        self._status_value_overrides[entity_state.id] = override_value
        return
