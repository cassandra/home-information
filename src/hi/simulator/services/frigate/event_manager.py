"""Singleton coordinator for synthesized Frigate-simulator events.

Per-camera ``FrigateSimEventHistory`` instances live here, keyed by
camera_name (Frigate's identifier is a string, unlike ZM's integer
monitor id). Mirrors ``ZmSimEventManager`` in role.
"""
from datetime import datetime
import threading
from typing import Dict, List, Optional

from hi.apps.common.singleton import Singleton

from .event_history import FrigateSimEventHistory
from .sim_models import FrigateSimCamera, FrigateSimEvent


class FrigateSimEventManager( Singleton ):

    def __init_singleton__(self):
        self._histories : Dict[ str, FrigateSimEventHistory ] = dict()
        self._data_lock = threading.Lock()
        # Frigate's wire event_id space is opaque — real Frigate uses
        # ``<epoch>.<microseconds>-<hash>`` strings. For the simulator
        # we use a process-wide monotonic counter, stringified. Stable
        # round-trip is all the integration needs.
        self._next_event_id = 0
        return

    def _allocate_event_id( self ) -> str:
        self._next_event_id += 1
        return str( self._next_event_id )

    def set_current_object( self,
                            frigate_sim_camera  : FrigateSimCamera,
                            object_label        : str,
                            none_label          : str ) -> Optional[ FrigateSimEvent ]:
        """Driven by the camera ObjectPresence sim-state. Routes to
        the per-camera history, allocating one on first use. Returns
        the event the transition touched (or ``None`` when no
        transition was needed). ``none_label`` is the wire value that
        means "no current detection" (e.g. ``'none'``)."""
        with self._data_lock:
            camera_name = frigate_sim_camera.camera_name
            history = self._histories.get( camera_name )
            if history is None:
                history = FrigateSimEventHistory(
                    frigate_sim_camera = frigate_sim_camera,
                    event_id_allocator = self._allocate_event_id,
                    none_label = none_label,
                )
                self._histories[ camera_name ] = history
            return history.set_current_object( object_label = object_label )

    def get_events_after( self, start_datetime : datetime ) -> List[ FrigateSimEvent ]:
        """All events across all cameras with start time at or after
        ``start_datetime``. Used by the simulator's
        ``GET /api/events?after=`` endpoint."""
        results : List[ FrigateSimEvent ] = []
        with self._data_lock:
            for history in self._histories.values():
                results.extend( history.get_events_after(
                    start_datetime = start_datetime,
                ))
                continue
        return results

    def all_events( self ) -> List[ FrigateSimEvent ]:
        """All events across all cameras, regardless of time. Used by
        unfiltered ``GET /api/events`` requests."""
        results : List[ FrigateSimEvent ] = []
        with self._data_lock:
            for history in self._histories.values():
                results.extend( history.all_events() )
                continue
        return results

    def find_event_by_id( self, event_id : str ) -> Optional[ FrigateSimEvent ]:
        with self._data_lock:
            for history in self._histories.values():
                match = history.find_event_by_id( event_id = event_id )
                if match is not None:
                    return match
                continue
        return None
