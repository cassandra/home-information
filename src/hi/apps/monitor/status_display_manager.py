import dataclasses
from cachetools import TTLCache
from typing import Dict, List, Set, Sequence

from django.conf import settings
from django.db.models import prefetch_related_objects

from hi.apps.control.transient_models import ControllerData
from hi.apps.common.singleton import Singleton
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.sense.models import Sensor
from hi.apps.sense.sensor_response_manager import SensorResponseMixin
from hi.apps.sense.transient_models import SensorResponse
from hi.testing.dev_injection import DevInjectionManager
from hi.testing.dev_overrides import DevOverrideManager

from .display_data import EntityStateDisplayData
from .status_data import EntityStatusData, EntityStateStatusData


class StatusDisplayManager( Singleton, SensorResponseMixin ):

    STATUS_VALUE_OVERRIDES_SECS = 11

    def __init_singleton__( self ):
        self._status_value_overrides = TTLCache(
            maxsize = 100,
            ttl = self.STATUS_VALUE_OVERRIDES_SECS,
        )
        return
        
    def get_entity_state_status_map( self ) -> Dict[ str, dict ]:
        """Build the per-EntityState polling-update map consumed by
        the client. Keyed by the EntityState id (as a string, since
        JSON object keys are always strings). The value shape is
        defined by ``EntityStateDisplayData.to_polling_update_dict``."""

        entity_state_status_data_list = self.get_all_entity_state_status_data_list()

        status_map : Dict[ str, dict ] = {}
        for entity_state_status_data in entity_state_status_data_list:
            status_display_data = EntityStateDisplayData( entity_state_status_data )
            state_id_key = str( status_display_data.entity_state.id )
            status_map[ state_id_key ] = status_display_data.to_polling_update_dict()
            if settings.DEBUG and settings.DEBUG_TRACE_STATE:
                latest = status_display_data.sensor_response_list[ 0 ]
                DevOverrideManager.trace_state(
                    'hi.ui_poll.entity_state.out',
                    integration_name = latest.integration_key.integration_name,
                    hi_entity_state_id = status_display_data.entity_state.id,
                    hi_value = latest.value,
                    row = status_map[ state_id_key ],
                )
            continue

        return status_map

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
                # This branch only sees EntityStates that produced
                # responses, so a sensor must exist; controllers
                # are explicitly known via the list above.
                has_sensor = True,
                has_controller = bool( controller_data_list ),
            )
            entity_state_status_data_list.append( entity_state_status_data )
            continue

        return entity_state_status_data_list

    def get_entity_status_data( self, entity : Entity ) -> EntityStatusData:

        # The set of entity states used to define the state includes the
        # principals when the entity is a delegate.
        #
        entity_for_video = None
        if entity.has_live_feed:
            entity_for_video = entity

        entity_state_set = set( entity.states.all() )
        for entity_state_delegation in entity.entity_state_delegations.all():
            entity_state_set.add( entity_state_delegation.entity_state )
            if ( not entity_for_video
                 and entity_state_delegation.entity_state.entity.has_live_feed ):
                entity_for_video = entity_state_delegation.entity_state.entity
            continue

        entity_state_to_status_data = self._get_entity_state_to_entity_state_status_data(
            entity_states = entity_state_set,
        )

        svg_item_factory = SvgItemFactory()
        svg_icon_item = svg_item_factory.get_display_only_svg_icon_item(
            entity = entity,
        )
        return EntityStatusData(
            entity = entity,
            entity_state_status_data_list = list( entity_state_to_status_data.values() ),
            entity_for_video = entity_for_video,  # Possibly principal entity via delegation
            display_only_svg_icon_item = svg_icon_item,
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
        svg_item_factory = SvgItemFactory()
        entity_status_data_list = list()
        for entity in entities:
            svg_icon_item = svg_item_factory.get_display_only_svg_icon_item(
                entity = entity,
            )
            entity_status_data = entity_to_entity_status_data.get( entity )
            if not entity_status_data:
                entity_status_data = EntityStatusData(
                    entity = entity,
                    entity_state_status_data_list = list(),
                    display_only_svg_icon_item = svg_icon_item,
                    # entity_for_video not looking for delegations here
                )
            else:
                entity_status_data.display_only_svg_icon_item = svg_icon_item
                
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
                    # entity_for_video not looking for delegations here
                    # display_only_svg_icon_item is filled in later
                )
                entity_to_entity_status_data[entity] = entity_status_data
            else:
                entity_status_data = entity_to_entity_status_data[entity]
                
            entity_status_data.entity_state_status_data_list.append(
                entity_state_status_data
            )
            continue

        return entity_to_entity_status_data

    def _get_entity_state_to_entity_state_status_data(
            self,
            entity_states : Sequence[ EntityState ] ) -> Dict[ EntityState, EntityStateStatusData ]:

        # Collect all the sensors for all the input EntityStates, so we can
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
                has_sensor = bool( entity_state_to_sensor_list.get( entity_state ) ),
                has_controller = bool( controller_data_list ),
            )
            entity_state_to_entity_state_status_data_map[entity_state] = entity_state_status_data
            continue
        
        return entity_state_to_entity_state_status_data_map

    def get_entity_to_entity_state_status_data_list(
            self,
            entities       : Set[ Entity ] ) -> Dict[ Entity, List[ EntityStateStatusData ] ]:
        """Builds a map from Entity to its EntityStateStatusData list
        (covering all of the entity's states, including any delegated
        principal states). Per-entity primary-state selection happens
        downstream in ``LocationViewData`` via
        ``ENTITY_PRIMARY_STATE_ORDERING`` — no EntityStateType
        pre-filter is applied here."""

        # Batch-prefetch the relations this flow will walk so the
        # per-entity loop below doesn't issue 2N delegation/states
        # queries and the downstream sensor/controller fetches don't
        # add 2M more.
        prefetch_related_objects(
            list( entities ),
            'states__sensors',
            'states__controllers',
            'entity_state_delegations__entity_state__sensors',
            'entity_state_delegations__entity_state__controllers',
        )

        entity_to_entity_state_list = dict()
        all_entity_states = set()
        for entity in entities:
            entity_states = self.all_entity_states_including_delegations( entity )
            if not entity_states:
                continue
            entity_to_entity_state_list[entity] = entity_states
            all_entity_states.update( entity_states )
            continue

        entity_state_to_status_data = self._get_entity_state_to_entity_state_status_data(
            entity_states = all_entity_states,
        )

        entity_to_entity_state_status_data_list = dict()
        for entity, entity_state_list in entity_to_entity_state_list.items():
            entity_to_entity_state_status_data_list[entity] = list()
            for entity_state in entity_state_list:
                entity_state_status_data = entity_state_to_status_data.get( entity_state )
                if entity_state_status_data:
                    entity_to_entity_state_status_data_list[entity].append( entity_state_status_data )
                continue
            continue

        return entity_to_entity_state_status_data_list

    def all_entity_states_including_delegations(
            self, entity : Entity ) -> List[ EntityState ]:
        """All EntityStates the entity exposes for status display:
        its own ``states`` plus any states delegated from principals
        via ``EntityStateDelegation``. Deduplicated to guard against
        the unusual case of an entity delegating one of its own
        states or two delegations resolving to the same state.

        ``.all()`` is used (not ``.select_related(...).all()``) so
        callers that have prefetched ``entity_state_delegations__
        entity_state`` use the cache. For single-entity callers with
        no prefetch, the additional FK fetch per delegation is
        bounded and acceptable."""
        seen = set()
        result = []
        for d in entity.entity_state_delegations.all():
            if d.entity_state.id in seen:
                continue
            seen.add( d.entity_state.id )
            result.append( d.entity_state )
        for state in entity.states.all():
            if state.id in seen:
                continue
            seen.add( state.id )
            result.append( state )
        return result

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

        # Dev-only: let the simulator's 'Clear States' drop pre-cutoff
        # responses so lingering recent/past visuals don't block re-runs.
        if settings.DEBUG and getattr( settings, 'DEBUG_FORCE_SENSOR_RESPONSE_CUTOFF', False ):
            sensor_to_sensor_response_list = DevInjectionManager.apply_sensor_response_cutoff(
                sensor_to_sensor_response_list,
            )

        # Apply overrides into a fresh dict so neither the
        # SensorResponse objects nor the response lists owned by
        # SensorResponseManager's cache are touched. Mutating
        # them would persist the override past its TTL.
        result = dict()
        for sensor, sensor_response_list in sensor_to_sensor_response_list.items():
            if ( not sensor_response_list
                 or ( sensor.entity_state.id not in self._status_value_overrides )):
                result[ sensor ] = sensor_response_list
                continue
            overridden = dataclasses.replace(
                sensor_response_list[ 0 ],
                value = self._status_value_overrides[ sensor.entity_state.id ],
            )
            result[ sensor ] = [ overridden, *sensor_response_list[ 1: ] ]
            continue

        return result
        
    def add_entity_state_value_override( self,
                                         entity_state    : EntityState,
                                         override_value  : str ):
        """
        Add a temporary override when values is explicitly chnaged by a controller to
        compensate for the delays in value updates from the polling intervals.
        """
        self._status_value_overrides[entity_state.id] = override_value
        return
