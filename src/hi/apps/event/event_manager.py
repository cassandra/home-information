from asgiref.sync import sync_to_async
from cachetools import TTLCache
from collections import deque
import logging
from typing import List

from hi.apps.alert.alert_mixins import AlertMixin
import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton
from hi.apps.control.control_mixins import ControllerMixin
from hi.apps.security.security_manager import SecurityManager

from .models import EventDefinition, EventHistory
from .transient_models import Event, EntityStateTransition

logger = logging.getLogger(__name__)


class EventManager( Singleton, AlertMixin, ControllerMixin ):

    RECENT_EVENT_CACHE_SIZE = 1000
    RECENT_EVENT_CACHE_TTL_SECS = 3600
    RECENT_TRANSITION_QUEUE_MAX_WINDOW_SECS = 300

    # We need to put some bounds to keep memory/cpu requirements for
    # managing events managable, but this will put impose bounds on how the
    # EventDefinitions parameters.
    #
    MAX_EVENT_WINDOW_SECS = RECENT_EVENT_CACHE_TTL_SECS
    MAX_DEDUPE_WINDOW_SECS = RECENT_TRANSITION_QUEUE_MAX_WINDOW_SECS
    
    def __init_singleton__(self):
        self._recent_transitions = deque()
        self._recent_events = TTLCache( maxsize = self.RECENT_EVENT_CACHE_SIZE,
                                        ttl = self.RECENT_EVENT_CACHE_TTL_SECS )
        self._was_initialized = False
        return
    
    def ensure_initialized(self):
        if self._was_initialized:
            return
        self.reload()
        self._was_initialized = True
        return

    def reload(self):
        """ Called when integration models are changed (via signals below). """
        logger.debug( 'Reloading event definitions' )
        self._event_definitions = list( EventDefinition.objects.prefetch_related(
            'event_clauses',
            'event_clauses__entity_state',
            'alarm_actions',
            'control_actions',
        ).filter( enabled = True ))
        return
    
    async def add_entity_state_transitions( self,
                                            entity_state_transition_list : List[ EntityStateTransition ] ):
        if not entity_state_transition_list:
            return
        logger.debug( f'Adding state transitions: {entity_state_transition_list}' )

        self._recent_transitions.extend( entity_state_transition_list )
        self._purge_old_transitions()
        new_event_list = self._get_new_events()

        logger.debug( f'New events found: {new_event_list}' )

        await self._do_new_event_action( event_list = new_event_list )
        await self._add_to_event_history( event_list = new_event_list )        
        return
                                      
    def _get_new_events( self ):
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

        return new_event_list

    def _has_recent_event( self, event_definition : EventDefinition ) -> bool:
        recent_event = self._recent_events.get( event_definition.id )
        if not recent_event:
            return False
        recent_event_timedelta = datetimeproxy.now() - recent_event.timestamp
        return bool( recent_event_timedelta.total_seconds() <= event_definition.dedupe_window_secs )
    
    def _create_event_if_detected( self, event_definition : EventDefinition ) -> bool:
        if not event_definition.event_clauses.exists():
            return False

        current_timestamp = datetimeproxy.now()
        sensor_response_list = list()
        
        for event_clause in event_definition.event_clauses.all():
            matches = False
            for transition in self._recent_transitions:
                if transition.entity_state != event_clause.entity_state:
                    continue
                if transition.latest_sensor_response.value != event_clause.value:
                    continue
                transition_timedelta = current_timestamp - transition.timestamp
                if transition_timedelta.total_seconds() > event_definition.event_window_secs:
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

        # Pop from front those that are too old until encounter one that is not too old.
        while True:
            if not self._recent_transitions:
                return
            transition_age = current_timestamp - self._recent_transitions[0].timestamp
            if transition_age.seconds < self.RECENT_TRANSITION_QUEUE_MAX_WINDOW_SECS:
                return
            self._recent_transitions.popleft()
            continue
        return

    async def _do_new_event_action( self, event_list : List[ Event ] ):
        alert_manager = await self.alert_manager_async()
        controller_manager = await self.controller_manager_async()
        
        current_security_level = SecurityManager().security_level

        for event in event_list:

            for alarm_action in event.event_definition.alarm_actions.all():
                if alarm_action.security_level != current_security_level:
                    continue
                alarm = event.to_alarm( alarm_action = alarm_action )
                await alert_manager.add_alarm( alarm )
                continue
            
            for control_action in event.event_definition.control_actions.all():
                await controller_manager.do_control_async(
                    controller = control_action.controller,
                    control_value = control_action.value,
                )
                continue
            continue
        return
    
    async def _add_to_event_history( self, event_list : List[ Event ] ):
        event_history_list = [ x.to_event_history() for x in event_list ]
        await self._bulk_create_event_history_async( event_history_list )
        return
    
    async def _bulk_create_event_history_async( self, event_history_list : List[ EventHistory ] ):
        await sync_to_async( EventHistory.objects.bulk_create)( event_history_list )
        return

