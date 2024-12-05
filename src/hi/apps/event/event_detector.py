from asgiref.sync import sync_to_async
from cachetools import TTLCache
from collections import deque
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton

from .models import EventDefinition
from .transient_models import Event, EntityStateTransition


class EventDetector(Singleton):

    def __init_singleton__(self):
        self._recent_transitions = deque()
        self._recent_events = TTLCache( maxsize = 1000, ttl = 300 )
        self.reload()
        return

    def reload(self):
        sync_to_async( self._reload_helper )()
        return

    def _reload_helper(self):
        self._event_definitions = EventDefinition.objects.prefetch_related('clauses').filter( enabled = True )
        self._max_event_window_secs = max([ x.event_window_secs for x in self._event_definitions ])
        return
    
    def add_entity_state_transitions( self, entity_state_transition_list : List[ EntityStateTransition ] ):
        if not entity_state_transition_list:
            return
        self._recent_transitions.extend( entity_state_transition_list )
        self._purge_old_transitions()
        self._check_for_new_events()
        return
                                      
    def _check_for_new_events( self ):
        new_event_list = list()
        for event_definition in self._event_definitions:
            if self._has_recent_event( event_definition ):
                continue
            event = self._create_event_if_detected( event_definition )
            if not event:
                continue
            self._recent_events[event_definition.id] = event
            new_event_list.append( event )
            continue

        self._handle_new_events( event_list = new_event_list )
        self._add_to_event_history( event_list = new_event_list )        
        return

    def _has_recent_event( self, event_definition : EventDefinition ) -> bool:
        recent_event = self._recent_events.get( event_definition.id )
        if not recent_event:
            return False
        recent_event_timedelta = datetimeproxy.now() - recent_event.timestamp
        return bool( recent_event_timedelta <= event_definition.event_window_secs )
    
    def _create_event_if_detected( self, event_definition : EventDefinition ) -> bool:
        if not event_definition.clauses.exists():
            return False

        current_timestamp = datetimeproxy.now()
        sensor_response_list = list()
        
        for event_clause in event_definition.clauses.all():
            matches = False
            for transition in self._recent_transitions:
                if transition.entity_state != event_clause.entity_state:
                    continue
                if transition.latest_sensor_response.value != event_clause.value:
                    continue
                transition_timedelta = current_timestamp - transition.timestamp
                if transition_timedelta.seconds > event_definition.event_window_secs:
                    continue
                matches = True
                sensor_response_list.append( transition.latest_sensor_response )
                break
            if not matches:
                return False
            continue
        
        return Event(
            event_definition = event_definition,
            sensor_response_list = sensor_response_list,
        )
    
    def _purge_old_transitions( self ):
        current_timestamp = datetimeproxy.now()
        while ( self._recent_transitions
                and (( current_timestamp - self._recent_transitions[0].timestamp )
                     > self._max_event_window_secs )):
            self._recent_transitions.popleft()
            continue
        return

    def _handle_new_events( self, event_list : List[ Event ] ):
        raise NotImplementedError()

    def _add_to_event_history( self, event_list : List[ Event ] ):
        raise NotImplementedError()
    
