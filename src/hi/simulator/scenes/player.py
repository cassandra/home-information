"""Server-side playback of a SimStateSequence.

Singleton. A sequence is *loaded* (its scene baseline applied, playhead at
0) on first PLAY/STEP/SEEK, and a persistent playhead lets the filming
controls drive it across requests:

- ``play``  — run continuously from the playhead to the end.
- ``step``  — run to the next marker (or end), then auto-pause.
- ``pause`` — interrupt the run, leaving the playhead in place.
- ``seek``  — re-apply the baseline, fold steps ``t <= T`` instantly, pause at T.
- ``mark``  — insert a marker at the playhead (paused only); persists to the sequence.
- ``stop``  — halt and rewind the playhead to the start.

The timed walk runs on a daemon thread; ``pause``/``seek``/``stop`` cancel it
via an event. Steps resolve ``(module, name, state_id)`` -> live entity ->
``simulator.set_sim_state``; unresolved steps land in a miss-log surfaced via
status.
"""
import logging
import threading
import time
from typing import List, Optional

from django import db

from hi.apps.common.singleton import Singleton
from hi.simulator.services.service_simulator_manager import ServiceSimulatorManager

from .initial_state import apply_initial_state
from .models import SimStateSequence
from .scene_controller import SceneController

logger = logging.getLogger(__name__)


class SimPlayer( Singleton ):

    def __init_singleton__(self):
        self._lock = threading.Lock()
        self._thread : Optional[ threading.Thread ] = None
        self._cancel_event = threading.Event()
        self._reset_locked()
        return

    def _reset_locked( self ):
        # caller holds self._lock (or single-threaded init)
        self._sequence_id : Optional[ int ] = None
        self._sequence_name : Optional[ str ] = None
        self._steps : List[ dict ] = []
        self._index = 0
        self._playhead_t = 0.0
        self._total = 0.0
        self._mode = 'idle'  # idle | paused | playing | stepping
        self._misses : List[ dict ] = []
        # Wall-clock anchor for the continuous playhead during PLAY: the
        # reported position is _clock_base_t + (now - _clock_base_monotonic),
        # so the playhead glides through inter-event gaps instead of snapping
        # to applied steps.
        self._clock_base_t = 0.0
        self._clock_base_monotonic : Optional[ float ] = None
        return

    def _live_playhead_locked( self ) -> float:
        """The continuous wall-clock position; falls back to the discrete
        playhead when no clock anchor is set. While stepping it is bounded by
        the next marker (the segment's stop point) rather than the full
        duration, so the cursor never runs past the mark. Caller holds the lock."""
        if self._clock_base_monotonic is None:
            return self._playhead_t
        live = self._clock_base_t + ( time.monotonic() - self._clock_base_monotonic )
        ceiling = self._next_marker_t_locked() if self._mode == 'stepping' else self._total
        return round( min( ceiling, max( 0.0, live )), 3 )

    def _next_marker_t_locked( self ) -> float:
        """t of the next marker at/after the playhead — STEP's stop point; the
        full duration if none remain. Caller holds the lock."""
        for step in self._steps[ self._index : ]:
            if 'marker' in step:
                return float( step[ 't' ] ) if 't' in step else self._total
        return self._total

    # ----- status -----

    def is_playing( self ) -> bool:
        with self._lock:
            return self._mode in ( 'playing', 'stepping' )

    def get_status( self ) -> dict:
        with self._lock:
            # PLAY and STEP both report a live wall-clock position (the thread
            # waits real t-deltas in either mode); paused/idle hold the frozen
            # position. Reporting discrete here while the client interpolates
            # makes the cursor jitter (snap back each poll), so they must agree.
            playhead = (
                self._live_playhead_locked() if self._mode in ( 'playing', 'stepping' )
                else self._playhead_t
            )
            # Ceiling for the client's interpolation: the next marker while
            # stepping (so it stops on the mark), else the full duration.
            playhead_limit = (
                self._next_marker_t_locked() if self._mode == 'stepping'
                else self._total
            )
            return {
                'mode': self._mode,
                'playing': self._mode in ( 'playing', 'stepping' ),
                'paused': self._mode == 'paused',
                'loaded': self._sequence_id is not None,
                'sequence_id': self._sequence_id,
                'sequence_name': self._sequence_name,
                'playhead': playhead,
                'playhead_limit': round( playhead_limit, 3 ),
                'total': self._total,
                'step_index': self._index,
                'step_count': len( self._steps ),
                'next_marker': self._next_marker_locked(),
                'misses': list( self._misses ),
            }

    def _next_marker_locked( self ):
        for step in self._steps[ self._index : ]:
            if 'marker' in step:
                return step[ 'marker' ]
        return None

    # ----- transport commands -----

    def play( self, sequence : SimStateSequence ):
        self._cancel_and_join()
        if self._load_if_needed( sequence ):
            SceneController().apply( sequence.scene )
            self._apply_initial_state_locked( sequence )
        self._start_thread( stepping = False )
        return

    def step( self, sequence : SimStateSequence ):
        self._cancel_and_join()
        if self._load_if_needed( sequence ):
            SceneController().apply( sequence.scene )
            self._apply_initial_state_locked( sequence )
        self._start_thread( stepping = True )
        return

    def pause( self ):
        self._cancel_and_join()
        with self._lock:
            if self._sequence_id is not None:
                # Freeze at the true wall-clock position, not the last applied
                # event — so pausing mid-gap holds where you actually paused.
                if self._mode in ( 'playing', 'stepping' ):
                    self._playhead_t = self._live_playhead_locked()
                self._mode = 'paused'
                self._clock_base_monotonic = None
        return

    def stop( self ):
        self._cancel_and_join()
        with self._lock:
            self._index = 0
            self._playhead_t = 0.0
            self._mode = 'idle'
        return

    def seek( self, sequence : SimStateSequence, t : float ):
        self._cancel_and_join()
        self._load_if_needed( sequence )
        # Seeking (incl. backward) always rebuilds from the baseline.
        SceneController().apply( sequence.scene )
        self._apply_initial_state_locked( sequence )
        simulator_by_module = self._simulator_by_module()
        misses : List[ dict ] = []
        with self._lock:
            steps = list( self._steps )
        index = len( steps )
        for i, step in enumerate( steps ):
            if 't' in step and float( step[ 't' ] ) > t:
                index = i
                break
            if 'marker' not in step and not step.get( 'end' ):
                self._apply_step( step, simulator_by_module, misses )
            continue
        with self._lock:
            self._index = index
            self._playhead_t = t
            self._mode = 'paused'
            self._misses = misses
        db.close_old_connections()
        return

    def mark( self, name = None ) -> bool:
        """Insert a timestamped marker at the playhead (paused only) and persist it."""
        with self._lock:
            if self._mode != 'paused' or self._sequence_id is None:
                return False
            self._steps.insert( self._index, {
                'marker': ( name or '' ).strip() or 'mark',
                't': round( self._playhead_t, 3 ),
            })
            self._index += 1  # marker now sits behind the playhead
            steps_copy = list( self._steps )
            sequence_id = self._sequence_id
        SimStateSequence.objects.filter( id = sequence_id ).update( steps_json = steps_copy )
        return True

    # ----- internals -----

    def _load_if_needed( self, sequence : SimStateSequence ) -> bool:
        """Load the sequence unless it's the same one and merely paused
        mid-way (in which case we resume). Returns True if (re)loaded."""
        with self._lock:
            if sequence.id == self._sequence_id and self._mode == 'paused':
                return False
            self._sequence_id = sequence.id
            self._sequence_name = sequence.name
            self._steps = list( sequence.steps_json or [] )
            self._index = 0
            self._playhead_t = 0.0
            self._total = max(
                ( float( s[ 't' ] ) for s in self._steps if 't' in s ), default = 0.0,
            )
            self._misses = []
            self._mode = 'paused'
        return True

    def _start_thread( self, stepping : bool ):
        self._cancel_event = threading.Event()
        with self._lock:
            if self._index >= len( self._steps ):
                self._mode = 'idle'
                return
            self._mode = 'stepping' if stepping else 'playing'
            # Anchor the wall clock at the current playhead so the live
            # position advances from here (the thread waits real t-deltas).
            self._clock_base_t = self._playhead_t
            self._clock_base_monotonic = time.monotonic()
        self._thread = threading.Thread(
            target = self._run,
            args = ( stepping, ),
            name = 'SimPlayer',
            daemon = True,
        )
        self._thread.start()
        return

    def _cancel_and_join( self ):
        self._cancel_event.set()
        thread = self._thread
        if ( thread is not None and thread.is_alive()
             and thread is not threading.current_thread() ):
            thread.join( timeout = 2.0 )
        self._thread = None
        return

    def _run( self, stepping : bool ):
        simulator_by_module = self._simulator_by_module()
        misses : List[ dict ] = []
        reached_marker = False
        try:
            while not self._cancel_event.is_set():
                with self._lock:
                    index = self._index
                    steps = self._steps
                    prev_t = self._playhead_t
                if index >= len( steps ):
                    break
                step = steps[ index ]
                # Uniform timed walk: wait this step's t-delta, then act by
                # kind. State changes apply; the end sentinel just advances
                # (its wait is the trailing time); markers are STEP cue stops.
                step_t = float( step.get( 't', prev_t ))
                delay = step_t - prev_t
                if delay > 0 and self._cancel_event.wait( timeout = delay ):
                    break  # cancelled mid-wait; leave playhead/index for resume
                is_marker = 'marker' in step
                if not is_marker and not step.get( 'end' ):
                    self._apply_step( step, simulator_by_module, misses )
                with self._lock:
                    self._index = index + 1
                    self._playhead_t = step_t
                if is_marker and stepping:
                    reached_marker = True
                    break
                continue
        except Exception:
            logger.exception( 'SimPlayer run failed' )
        finally:
            with self._lock:
                self._misses = misses
                if not self._cancel_event.is_set():
                    if reached_marker:
                        self._mode = 'paused'
                    else:
                        self._mode = 'idle'
                        self._index = len( self._steps )
                        self._playhead_t = self._total
            db.close_old_connections()
        return

    def _simulator_by_module( self ):
        return {
            data.simulator.module_key: data.simulator
            for data in ServiceSimulatorManager().get_simulator_data_list()
        }

    def _apply_initial_state_locked( self, sequence : SimStateSequence ):
        """Overlay the sequence's captured initial state onto the just-applied
        scene baseline. Misses (unloaded entities) are merged into the player's
        miss list so the transport surfaces them like step misses."""
        misses = apply_initial_state( sequence.initial_state_json or [] )
        if misses:
            with self._lock:
                self._misses.extend( misses )
        return

    def _apply_step( self, step, simulator_by_module, misses ):
        module_key = step.get( 'module' )
        entity_name = step.get( 'entity' )
        sim_state_id = step.get( 'state' )
        value_str = step.get( 'value' )
        simulator = simulator_by_module.get( module_key )
        sim_entity = None
        if simulator is not None:
            sim_entity = next(
                ( e for e in simulator.sim_entities if e.name == entity_name ),
                None,
            )
        if simulator is None or sim_entity is None:
            misses.append({ 'module': module_key, 'entity': entity_name, 'state': sim_state_id })
            return
        try:
            simulator.set_sim_state(
                sim_entity_id = sim_entity.id,
                sim_state_id = sim_state_id,
                value_str = value_str,
            )
        except Exception:
            logger.exception(
                f'SimPlayer: failed to apply {module_key}/{entity_name}/{sim_state_id}'
            )
            misses.append({ 'module': module_key, 'entity': entity_name, 'state': sim_state_id })
        return
