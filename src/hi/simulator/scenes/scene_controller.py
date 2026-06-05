"""Active-scene orchestration for the simulator.

A ``SimScene`` names a per-module profile combination. Applying it drives
each bound module's ``ProfileManager`` to the scene's chosen profile,
which rehydrates that module's entities to a clean baseline. Modules with
no binding are left under individual control. "Off" is the absence of an
active scene (apply nothing; leave per-module control).

Singleton: the active scene is process-local session state (lost on
simulator restart, which is fine — the operator re-applies).
"""
import logging
import threading
from typing import Optional

from hi.apps.common.singleton import Singleton
from hi.simulator.profile.profile_manager import ProfileManager

from .models import SimScene

logger = logging.getLogger(__name__)


class SceneController( Singleton ):

    def __init_singleton__(self):
        self._active_scene_id : Optional[ int ] = None
        self._lock = threading.Lock()
        return

    def apply( self, scene : SimScene ):
        """Switch each bound module to its profile (rehydrating that
        module's entities to a clean baseline). A single bad binding is
        logged and skipped rather than aborting the whole scene."""
        profile_manager = ProfileManager()
        for binding in scene.bindings.select_related( 'profile' ).all():
            try:
                profile_manager.set_current(
                    module_key = binding.module_key,
                    profile = binding.profile,
                )
            except Exception:
                logger.exception(
                    f'Scene {scene.name!r}: failed to apply binding'
                    f' {binding.module_key!r} -> profile {binding.profile_id}'
                )
            continue
        with self._lock:
            self._active_scene_id = scene.id
        logger.info( f'Applied scene: {scene.name!r}' )
        return

    def clear( self ):
        """"Off": stop enforcing a scene. Leaves each module on its current
        profile under individual control (no profile changes)."""
        with self._lock:
            self._active_scene_id = None
        return

    def get_active_scene( self ) -> Optional[ SimScene ]:
        with self._lock:
            scene_id = self._active_scene_id
        if scene_id is None:
            return None
        try:
            return SimScene.objects.get( id = scene_id )
        except SimScene.DoesNotExist:
            with self._lock:
                self._active_scene_id = None
            return None
