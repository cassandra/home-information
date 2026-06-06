"""The scene dashboard's curated state-control grid.

Curated controls are stored by a re-seed-proof stable key
(``module_key | entity_name | sim_state_id``) and resolved to the live
(simulator, sim_state) at render time. This module owns that codec and
resolution; no HTTP.
"""
from hi.simulator.services.service_simulator_manager import ServiceSimulatorManager


def simulator_by_module():
    return {
        simulator_data.simulator.module_key: simulator_data.simulator
        for simulator_data in ServiceSimulatorManager().get_simulator_data_list()
    }


def control_key( module_key, entity_name, sim_state_id ):
    return f'{module_key}|{entity_name}|{sim_state_id}'


def split_control_key( key ):
    # module_key (dotted) and sim_state_id (slug) are '|'-free, so take
    # them from the ends; entity_name (the middle) may contain '|'.
    parts = key.split( '|' )
    return parts[0], '|'.join( parts[1:-1] ), parts[-1]


def resolve_control( control, simulator_by_module_map ):
    """Resolve a SimSceneControl's stable key to the live (simulator,
    sim_state); None if the entity/state isn't currently loaded."""
    simulator = simulator_by_module_map.get( control.module_key )
    if simulator is None:
        return None
    sim_entity = next(
        ( e for e in simulator.sim_entities if e.name == control.entity_name ),
        None,
    )
    if sim_entity is None:
        return None
    sim_state = next(
        ( s for s in sim_entity.sim_state_list if s.sim_state_id == control.sim_state_id ),
        None,
    )
    if sim_state is None:
        return None
    # The scenes grid shows the entity name in its own column, so drop a
    # redundant leading "<entity> " from the state label (e.g. hass's
    # "Front Door Motion" -> "Motion"). Labels without that prefix (frigate's
    # "Detected Object") are left as-is.
    entity_name = sim_entity.name
    state_label = sim_state.name
    prefix = f'{entity_name} '
    if state_label.startswith( prefix ) and len( state_label ) > len( prefix ):
        state_label = state_label[ len( prefix ): ]
    return {
        'simulator': simulator,
        'sim_state': sim_state,
        'entity_name': entity_name,
        'state_label': state_label,
    }
