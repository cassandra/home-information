"""Per-Sequence initial-state snapshot — capture and apply.

A Scene's profile bindings give each module a clean baseline on apply
(``SceneController.apply``). That baseline is generic; for filming, each
beat needs a tailored starting state on top of it (e.g. garage door
already open, a light already on). The snapshot fills that gap: capture
the current sim states as the selected Sequence's overlay, and apply it
after the scene baseline whenever that sequence loads.

Captures all currently-loaded states (simple, predictable; SimState
already no-ops on unchanged values). Stored on ``SimStateSequence`` as
``initial_state_json``, in the same dict shape as a ``steps_json`` entry
without ``t``: ``{module, entity, state, value}``.
"""
import logging
from typing import List

from hi.simulator.services.service_simulator_manager import ServiceSimulatorManager

logger = logging.getLogger(__name__)


def capture_current_state() -> List[ dict ]:
    """Snapshot every currently-loaded sim state across all modules.

    Values are stringified so the overlay round-trips through the same
    ``value_str`` path that recorded steps use."""
    entries : List[ dict ] = []
    for simulator_data in ServiceSimulatorManager().get_simulator_data_list():
        simulator = simulator_data.simulator
        for sim_entity in simulator.sim_entities:
            for sim_state in sim_entity.sim_state_list:
                entries.append({
                    'module': simulator.module_key,
                    'entity': sim_entity.name,
                    'state': sim_state.sim_state_id,
                    'value': '' if sim_state.value is None else str( sim_state.value ),
                })
                continue
            continue
        continue
    return entries


def apply_initial_state( initial_state_json : List[ dict ] ) -> List[ dict ]:
    """Apply each entry via the simulator's ``set_sim_state``. Returns a
    miss list (same shape as ``SimPlayer``'s misses) for entries whose
    module/entity/state isn't currently loaded — surfaced via the
    player's status when called from playback."""
    if not initial_state_json:
        return []
    simulator_by_module = {
        data.simulator.module_key: data.simulator
        for data in ServiceSimulatorManager().get_simulator_data_list()
    }
    misses : List[ dict ] = []
    for entry in initial_state_json:
        module_key = entry.get( 'module' )
        entity_name = entry.get( 'entity' )
        sim_state_id = entry.get( 'state' )
        value_str = entry.get( 'value' )
        simulator = simulator_by_module.get( module_key )
        sim_entity = None
        if simulator is not None:
            sim_entity = next(
                ( e for e in simulator.sim_entities if e.name == entity_name ),
                None,
            )
        if simulator is None or sim_entity is None:
            misses.append({ 'module': module_key, 'entity': entity_name, 'state': sim_state_id })
            continue
        try:
            simulator.set_sim_state(
                sim_entity_id = sim_entity.id,
                sim_state_id = sim_state_id,
                value_str = value_str,
            )
        except Exception:
            logger.exception(
                f'apply_initial_state: failed {module_key}/{entity_name}/{sim_state_id}'
            )
            misses.append({ 'module': module_key, 'entity': entity_name, 'state': sim_state_id })
        continue
    return misses
