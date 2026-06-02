"""In-memory fault-mode selection per weather source.

Mirrors how the services simulator holds fault mode: a transient testing
toggle (not profile-scoped, not persisted) that resets on restart. Keyed
by the source's short name — the same segment that appears in its API
URL path (``/weather/<short_name>/api/...``).
"""
import threading

from hi.simulator.fault_injection import FaultMode

_lock = threading.Lock()
_fault_mode_by_source = {}


def get_fault_mode( short_name : str ) -> FaultMode:
    with _lock:
        return _fault_mode_by_source.get( short_name, FaultMode.default() )


def set_fault_mode( short_name : str, fault_mode : FaultMode ) -> None:
    with _lock:
        _fault_mode_by_source[ short_name ] = fault_mode
    return
