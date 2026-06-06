"""Operator state-change capture for the simulator.

Singleton. While recording, the ``SimStateSetView`` hook appends a step
per operator state change with an active-time ``t`` (seconds since
start). ``stop()`` finalizes the captured steps into a *working* sequence
held in memory; ``save()`` persists it as a ``SimStateSequence`` under
the scene being recorded.

Capture is operator-only: it runs in the HTTP set-state path. Playback
(SimPlayer) applies state via the simulator method directly, bypassing
that path, so playback is never self-captured.
"""
import logging
import threading
import time
from typing import List, Optional

from hi.apps.common.singleton import Singleton

from .models import SimScene, SimStateSequence

logger = logging.getLogger(__name__)


class SimRecorder( Singleton ):

    def __init_singleton__(self):
        self._lock = threading.Lock()
        self._recording = False
        self._paused = False
        self._scene_id : Optional[ int ] = None
        # Pause-aware clock: active (unpaused) seconds = accumulated + (now -
        # resumed_at) while running, frozen at accumulated while paused. This
        # excludes staging "dead time" from step timestamps.
        self._accumulated : float = 0.0
        self._resumed_at : Optional[ float ] = None
        self._steps : List[ dict ] = []
        # Finalized-but-unsaved steps after stop(), until save()/discard().
        self._working_steps : Optional[ List[ dict ] ] = None
        self._working_scene_id : Optional[ int ] = None
        return

    def is_recording( self ) -> bool:
        return self._recording

    def is_paused( self ) -> bool:
        return self._recording and self._paused

    def start( self, scene : SimScene ):
        with self._lock:
            self._recording = True
            self._paused = False
            self._scene_id = scene.id
            self._accumulated = 0.0
            self._resumed_at = time.monotonic()
            self._steps = []
            self._working_steps = None
            self._working_scene_id = None
        return

    def _active_t_locked( self ) -> float:
        # caller holds self._lock
        if self._paused or self._resumed_at is None:
            return round( self._accumulated, 3 )
        return round( self._accumulated + ( time.monotonic() - self._resumed_at ), 3 )

    def toggle_pause( self ):
        """PAUSE while recording stops the clock; pressing it again resumes."""
        with self._lock:
            if not self._recording:
                return
            if self._paused:
                self._resumed_at = time.monotonic()
                self._paused = False
            else:
                self._accumulated += time.monotonic() - self._resumed_at
                self._paused = True
        return

    def mark( self, name = None ) -> bool:
        """Insert a timestamped marker at the current position; allowed only
        while paused (so it stamps the frozen pause time)."""
        with self._lock:
            if not self._recording or not self._paused:
                return False
            self._steps.append({
                'marker': ( name or '' ).strip() or 'mark',
                't': self._active_t_locked(),
            })
        return True

    def record_step( self, module_key, entity_name, sim_state_id, value_str ):
        with self._lock:
            if not self._recording:
                return
            t = self._active_t_locked()
            self._steps.append({
                't': t,
                'module': module_key,
                'entity': entity_name,
                'state': sim_state_id,
                'value': value_str,
            })
        return

    def stop( self ):
        with self._lock:
            if not self._recording:
                return
            # Append an end sentinel at the true stop time. It carries no
            # state but participates in playback (the player waits out its t),
            # so trailing time is preserved and an empty recording still has a
            # span. Start is implicit at t=0 — no start sentinel.
            self._steps.append({ 't': self._active_t_locked(), 'end': True })
            self._recording = False
            self._paused = False
            self._working_steps = self._steps
            self._working_scene_id = self._scene_id
            self._steps = []
        return

    def discard( self ):
        with self._lock:
            self._working_steps = None
            self._working_scene_id = None
        return

    def save( self, name : Optional[ str ] = None ) -> Optional[ SimStateSequence ]:
        with self._lock:
            steps = self._working_steps
            scene_id = self._working_scene_id
        if steps is None or scene_id is None:
            return None
        try:
            scene = SimScene.objects.get( id = scene_id )
        except SimScene.DoesNotExist:
            self.discard()
            return None
        name = ( name or '' ).strip() or self._auto_name( scene )
        name = self._unique_name( scene, name )
        sequence = SimStateSequence.objects.create(
            scene = scene,
            name = name,
            steps_json = steps,
        )
        self.discard()
        return sequence

    def get_status( self ) -> dict:
        with self._lock:
            return {
                'recording': self._recording,
                'paused': self._recording and self._paused,
                'scene_id': self._scene_id if self._recording else None,
                'step_count': len( self._steps ),
                'has_working': self._working_steps is not None,
                'working_step_count': len( self._working_steps ) if self._working_steps else 0,
                'working_scene_id': self._working_scene_id,
            }

    def _auto_name( self, scene : SimScene ) -> str:
        return f'Sequence {scene.state_sequences.count() + 1}'

    def _unique_name( self, scene : SimScene, name : str ) -> str:
        """Append a numeric suffix when the name is already used in the scene,
        so a save never collides with the (scene, name) unique constraint (a
        duplicate name previously raised IntegrityError). Quick capture action
        — uniquify rather than block; the operator can rename afterward."""
        if not scene.state_sequences.filter( name = name ).exists():
            return name
        index = 2
        while scene.state_sequences.filter( name = f'{name} ({index})' ).exists():
            index += 1
            continue
        return f'{name} ({index})'
