"""Per-camera event history for the Frigate simulator.

Mirrors ``ZmSimEventHistory`` in structure: a bounded ring buffer of
events that the event manager consults to satisfy ``/api/events``
queries. Events are synthesized from operator motion-state toggles —
no DB row, no CRUD UI.
"""
from collections import deque
from datetime import datetime
from typing import Callable, List, Optional

import hi.apps.common.datetimeproxy as datetimeproxy

from .sim_models import FrigateSimCamera, FrigateSimEvent


class FrigateSimEventHistory:
    """Per-camera ring buffer of events.

    The label on a new event comes from whatever the camera's
    ObjectPresence sim-state currently reads at the moment motion
    toggles ON. ObjectPresence changes during an open event do NOT
    relabel the event — they take effect on the next motion-cycle
    (matching real Frigate's "label fixed at first detection" behavior
    closely enough for the simulator).
    """

    DEFAULT_MAX_EVENTS = 500

    def __init__( self,
                  frigate_sim_camera  : FrigateSimCamera,
                  event_id_allocator  : Callable[ [], str ],
                  max_events          : int = DEFAULT_MAX_EVENTS ):
        self._frigate_sim_camera = frigate_sim_camera
        self._event_id_allocator = event_id_allocator
        self._events : deque = deque( maxlen = max_events )
        return

    def __len__(self) -> int:
        return len( self._events )

    def add_motion_value( self,
                          motion_value  : bool,
                          object_label  : str ) -> Optional[ FrigateSimEvent ]:
        """Driven by the camera's Motion sim-state toggling.

        ``motion_value`` True with no open event → start a new event
        labeled ``object_label``. True with an open event → no-op
        (the existing event stays open). False with an open event
        → close it. Returns the event that was touched (or None when
        nothing changed)."""
        if len( self._events ) == 0:
            if motion_value:
                return self._open_event( object_label = object_label )
            return None

        latest = self._events[-1]
        if motion_value:
            if latest.is_active:
                return latest
            return self._open_event( object_label = object_label )

        if latest.is_active:
            latest.close()
            return latest
        return None

    def _open_event( self, object_label : str ) -> FrigateSimEvent:
        event = FrigateSimEvent(
            event_id = self._event_id_allocator(),
            camera_name = self._frigate_sim_camera.camera_name,
            label = object_label,
            start_datetime = datetimeproxy.now(),
        )
        self._events.append( event )
        return event

    def get_events_after( self, start_datetime : datetime ) -> List[ FrigateSimEvent ]:
        """All events whose start time is at or after ``start_datetime``.
        Inclusive cutoff keeps the polling-cursor pattern simple
        (we can advance the cursor up to the latest event's start
        without losing it on the next query)."""
        return [ e for e in self._events if e.start_datetime >= start_datetime ]

    def all_events( self ) -> List[ FrigateSimEvent ]:
        return list( self._events )

    def find_event_by_id( self, event_id : str ) -> Optional[ FrigateSimEvent ]:
        for event in self._events:
            if event.event_id == event_id:
                return event
            continue
        return None
