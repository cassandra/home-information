import importlib
import logging
import pkgutil
from threading import Lock
from typing import Dict, List, Optional

from hi.apps.common.singleton import Singleton

from hi.apps.entity.state_panel_base import EntityStatePanel


logger = logging.getLogger( __name__ )


class EntityStatePanelRegistry( Singleton ):

    def __init_singleton__( self ):
        self._panels : Dict[ str, EntityStatePanel ] = {}
        self._lock = Lock()
        self._discovered = False
        return

    def register( self, panel : EntityStatePanel ) -> None:
        with self._lock:
            existing = self._panels.get( panel.name )
            if existing is not None and existing is not panel:
                raise RuntimeError( f'Duplicate panel name: {panel.name!r}' )
            self._panels[ panel.name ] = panel
        return

    def discover( self ) -> None:
        """Import each ``state_panels/<name>/panel.py`` and register every
        ``EntityStatePanel`` instance found at module scope. Idempotent.
        Per-module failures are logged and skipped rather than aborting
        app startup, so one malformed panel doesn't poison the registry."""
        with self._lock:
            if self._discovered:
                return
        try:
            from hi.apps.entity import state_panels as panels_pkg
        except ImportError:
            with self._lock:
                self._discovered = True
            return
        for module_info in pkgutil.iter_modules( panels_pkg.__path__ ):
            if not module_info.ispkg:
                continue
            module_path = f'{panels_pkg.__name__}.{module_info.name}.panel'
            try:
                module = importlib.import_module( module_path )
                found = [
                    value for value in vars( module ).values()
                    if isinstance( value, EntityStatePanel )
                ]
                if not found:
                    logger.warning(
                        f'{module_path}: no EntityStatePanel instance at module scope'
                    )
                    continue
                for panel in found:
                    self.register( panel )
                    continue
            except Exception:
                logger.exception( f'Skipping {module_path}: discovery error' )
                continue
            continue
        with self._lock:
            self._discovered = True
        return

    def all_panels( self ) -> List[ EntityStatePanel ]:
        return list( self._panels.values() )

    def get_by_name( self, name : str ) -> Optional[ EntityStatePanel ]:
        return self._panels.get( name )

    def snapshot_for_tests( self ):
        with self._lock:
            return ( dict( self._panels ), self._discovered )

    def restore_for_tests( self, snapshot ) -> None:
        panels, discovered = snapshot
        with self._lock:
            self._panels = dict( panels )
            self._discovered = discovered
        return
