from collections import deque
from datetime import datetime
from typing import Callable, List

import hi.apps.common.datetimeproxy as datetimeproxy

from .sim_models import ZmSimEvent, ZmSimMonitor


# Encode the monitor id into the (integer, native-ZM) event id so the
# event-media endpoints — which receive only an event id — can resolve the
# monitor, and thus its selected clip, even for historical events the ephemeral
# in-memory manager no longer holds. ``monitor_id * STRIDE + sequence`` keeps
# the id a plain integer (real ZM ids are integers; HI treats them opaquely and
# orders events by time, not id). Assumes < STRIDE events per simulator session.
_EVENT_ID_MONITOR_STRIDE = 1_000_000


def make_event_id( monitor_id : int, sequence : int ) -> int:
    return monitor_id * _EVENT_ID_MONITOR_STRIDE + sequence


def monitor_id_from_event_id( event_id : int ) -> int:
    return event_id // _EVENT_ID_MONITOR_STRIDE


class ZmSimEventHistory:

    def __init__( self,
                  zm_sim_monitor      : ZmSimMonitor,
                  event_id_allocator  : Callable[[], int],
                  max_events          : int = 500 ):
        self._zm_sim_monitor = zm_sim_monitor
        self._event_id_allocator = event_id_allocator
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
        event_id = make_event_id(
            self._zm_sim_monitor.monitor_id,
            self._event_id_allocator(),
        )
        zm_sim_event = ZmSimEvent(
            zm_sim_monitor = self._zm_sim_monitor,
            event_id = event_id,
            start_datetime = datetimeproxy.now(),
            end_datetime = None,
            name = f'Event {event_id}',
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
