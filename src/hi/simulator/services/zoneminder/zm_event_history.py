from collections import deque
from datetime import datetime
from typing import List

import hi.apps.common.datetimeproxy as datetimeproxy

from .sim_models import ZmSimEvent, ZmSimMonitor


class ZmSimEventHistory:

    event_counter = 0
    
    def __init__( self, zm_sim_monitor : ZmSimMonitor, max_events: int = 500 ):
        self._zm_sim_monitor = zm_sim_monitor
        self._zm_sim_events = deque( maxlen = max_events )
        return

    def __len__(self):
        return len(self._zm_sim_events)
    
    def add_motion_value( self, motion_value : bool ) -> ZmSimEvent:
        
        if ( len(self) == 0 ):
            if motion_value:
                return self.add_zm_sim_event()
            else:
                return None

        latest_zm_sim_event = self._zm_sim_events[-1]
        if motion_value:
            if latest_zm_sim_event.is_active:
                return latest_zm_sim_event
            else:
                return self.add_zm_sim_event()

        latest_zm_sim_event.end_datetime = datetimeproxy.now()
        return latest_zm_sim_event

    def add_zm_sim_event( self ) -> ZmSimEvent:
        self.event_counter += 1
        zm_sim_event = ZmSimEvent(
            zm_sim_monitor = self._zm_sim_monitor,
            event_id = self.event_counter,
            start_datetime = datetimeproxy.now(),
            end_datetime = None,
            name = f'Event {self.event_counter}',
        )
        self._zm_sim_events.append( zm_sim_event )
        return zm_sim_event

    def close_zm_sim_event( self, zm_sim_event: ZmSimEvent ):
        zm_sim_event.end_datetime = datetimeproxy.now()
        zm_sim_event.update_score_properties()
        return
        
    def get_events_by_start_datetime( self, start_datetime : datetime ) -> List[ ZmSimEvent ]:
        # N.B.: This could be made more efficient by looping backwards over
        # list and stopping when a non-matching item is found.

        return [ x for x in self._zm_sim_events if x.start_datetime >= start_datetime]
