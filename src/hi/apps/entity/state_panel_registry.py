import importlib
import logging
import pkgutil
from threading import Lock
from typing import Dict, List, Optional

from hi.apps.common.singleton import Singleton

from hi.apps.entity.state_panel_base import EntityStatusPanel


logger = logging.getLogger( __name__ )


class EntityStatusPanelRegistry( Singleton ):

    def __init_singleton__( self ):
        self._panels : Dict[ str, EntityStatusPanel ] = {}
        self._lock = Lock()
        self._discovered = False
        return

    def register( self, panel : EntityStatusPanel ) -> None:
        with self._lock:
            existing = self._panels.get( panel.name )
            if existing is not None and existing is not panel:
                raise RuntimeError( f'Duplicate panel name: {panel.name!r}' )
            self._panels[ panel.name ] = panel
        return

    def discover( self ) -> None:
        """Import each ``state_panels/<name>/panel.py`` and register every
        ``EntityStatusPanel`` instance found at module scope. Idempotent."""
        with self._lock:
            if self._discovered:
                return
            self._discovered = True
        try:
            from hi.apps.entity import state_panels as panels_pkg
        except ImportError:
            return
        for module_info in pkgutil.iter_modules( panels_pkg.__path__ ):
            if not module_info.ispkg:
                continue
            module_path = f'{panels_pkg.__name__}.{module_info.name}.panel'
            try:
                module = importlib.import_module( module_path )
            except ImportError as e:
                logger.warning( f'Skipping {module_path}: {e}' )
                continue
            found = [
                value for value in vars( module ).values()
                if isinstance( value, EntityStatusPanel )
            ]
            if not found:
                logger.warning(
                    f'{module_path}: no EntityStatusPanel instance at module scope'
                )
                continue
            for panel in found:
                self.register( panel )
                continue
            continue
        return

    def all_panels( self ) -> List[ EntityStatusPanel ]:
        return list( self._panels.values() )

    def get_by_name( self, name : str ) -> Optional[ EntityStatusPanel ]:
        return self._panels.get( name )

    def reset_for_tests( self ) -> None:
        with self._lock:
            self._panels.clear()
            self._discovered = False
        return

    def snapshot_for_tests( self ):
        with self._lock:
            return ( dict( self._panels ), self._discovered )

    def restore_for_tests( self, snapshot ) -> None:
        panels, discovered = snapshot
        with self._lock:
            self._panels = dict( panels )
            self._discovered = discovered
        return
