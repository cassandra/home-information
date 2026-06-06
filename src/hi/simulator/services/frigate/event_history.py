"""Per-camera event history for the Frigate simulator.

Per-camera ring buffer of events. Events are synthesized from the
operator's ObjectPresence sim-state changes — no DB row, no CRUD UI.
"""
import re
from collections import deque
from datetime import datetime
from typing import Callable, List, Optional

import hi.apps.common.datetimeproxy as datetimeproxy

from .sim_models import FrigateSimCamera, FrigateSimEvent


# Simulator event ids encode the camera name so the event-media endpoints
# (clip.mp4 / snapshot.jpg) — which receive only an event id — can resolve the
# camera, and thus its selected clip, even for historical events the ephemeral
# in-memory manager no longer holds (e.g. after a restart). Real Frigate ids
# are opaque, so any unique, URL-safe format is fine. Format is
# ``<camera_name>-<sequence>``; decoding peels the trailing ``-<digits>``, so a
# camera name containing ``-`` (or even a trailing ``-<digits>``) round-trips.
_EVENT_ID_RE = re.compile( r'^(?P<camera_name>.+)-(?P<sequence>\d+)$' )


def make_event_id( camera_name : str, sequence : str ) -> str:
    return f'{camera_name}-{sequence}'


def camera_name_from_event_id( event_id : str ) -> Optional[ str ]:
    match = _EVENT_ID_RE.match( event_id or '' )
    return match.group( 'camera_name' ) if match else None


class FrigateSimEventHistory:
    """Per-camera ring buffer of events.

    The state machine is driven by ``set_current_object(label)``:
    transitioning to a different non-none label closes the current
    event and opens a new one; transitioning to ``none`` closes
    the current event; transitioning to the same label is a no-op.
    """

    DEFAULT_MAX_EVENTS = 500

    def __init__( self,
                  frigate_sim_camera  : FrigateSimCamera,
                  event_id_allocator  : Callable[ [], str ],
                  none_label          : str = 'none',
                  max_events          : int = DEFAULT_MAX_EVENTS ):
        self._frigate_sim_camera = frigate_sim_camera
        self._event_id_allocator = event_id_allocator
        self._none_label = none_label
        self._events : deque = deque( maxlen = max_events )
        return

    def __len__(self) -> int:
        return len( self._events )

    def set_current_object( self, object_label : str ) -> Optional[ FrigateSimEvent ]:
        """Drive the camera's event lifecycle from the current
        ObjectPresence value.

        Returns the event that was touched (the newly-opened event
        on START or label switch, the just-closed event on transition
        to none, or None if no transition was needed)."""
        latest = self._events[-1] if self._events else None
        currently_open = latest if ( latest is not None and latest.is_open ) else None

        if object_label == self._none_label:
            if currently_open is None:
                return None
            currently_open.close()
            return currently_open

        if currently_open is None:
            return self._open_event( object_label = object_label )

        if currently_open.label == object_label:
            return None

        # Label change while an event is open — close current, open new.
        currently_open.close()
        return self._open_event( object_label = object_label )

    def _open_event( self, object_label : str ) -> FrigateSimEvent:
        event = FrigateSimEvent(
            event_id = make_event_id(
                self._frigate_sim_camera.camera_name,
                self._event_id_allocator(),
            ),
            camera_name = self._frigate_sim_camera.camera_name,
            label = object_label,
            start_datetime = datetimeproxy.now(),
        )
        self._events.append( event )
        return event

    def get_events_after( self, start_datetime : datetime ) -> List[ FrigateSimEvent ]:
        """All events whose start time is STRICTLY after ``start_datetime``.

        Mirrors Frigate's own ``/api/events?after=T`` semantics
        (``Event.start_time > T``). The HI monitor depends on this
        strict-``>`` behavior — it advances the cursor past each
        observed event's ``start_time`` and tracks open events by id,
        so an inclusive filter here would let stale events leak back
        into cursor scans and mask bugs that real Frigate would
        surface."""
        return [ e for e in self._events if e.start_datetime > start_datetime ]

    def all_events( self ) -> List[ FrigateSimEvent ]:
        return list( self._events )

    def find_event_by_id( self, event_id : str ) -> Optional[ FrigateSimEvent ]:
        for event in self._events:
            if event.event_id == event_id:
                return event
            continue
        return None
