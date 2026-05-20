from typing import List

from hi.simulator.services.base_models import SimEntityDefinition, SimState
from hi.simulator.services.service_simulator import ServiceSimulator

from .event_manager import FrigateSimEventManager
from .sim_models import (
    FRIGATE_SIM_ENTITY_DEFINITION_LIST,
    FrigateCameraMotionState,
    FrigateCameraSimEntityFields,
    FrigateSimCamera,
)


class FrigateSimulator( ServiceSimulator ):
    """Simulator entry point for the Frigate integration.

    Mirrors the ZoneMinder simulator in role: discovers per-camera
    sim_entities, dispatches Frigate-shape API calls to
    ``service_dispatchers``, serves JPEG snapshots, etc.
    """

    @property
    def id(self) -> str:
        return 'frigate'

    @property
    def label(self) -> str:
        return 'Frigate'

    @property
    def integration_urls(self):
        return [
            ( 'Base URL', 'services/frigate' ),
        ]

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        return FRIGATE_SIM_ENTITY_DEFINITION_LIST

    def get_sim_cameras(self) -> List[ FrigateSimCamera ]:
        """All Frigate camera entities in the active profile, wrapped
        in the ``FrigateSimCamera`` accessor for typed access."""
        return [
            FrigateSimCamera( sim_entity = sim_entity )
            for sim_entity in self.sim_entities
            if sim_entity.sim_entity_definition.sim_entity_fields_class
            == FrigateCameraSimEntityFields
        ]

    def set_sim_state( self,
                       sim_entity_id  : int,
                       sim_state_id   : str,
                       value_str      : str ) -> SimState:
        """Override so Motion sim-state toggles synthesize Frigate
        events via ``FrigateSimEventManager``. The event's ``label``
        comes from the camera's current ObjectPresence sim-state at
        the moment motion-ON fires — matching real Frigate's "label
        fixed at first detection" closely enough for the simulator.
        ObjectPresence changes during an open event don't relabel it;
        the operator can close + reopen motion to start a new event
        with the new label.
        """
        sim_state = super().set_sim_state(
            sim_entity_id = sim_entity_id,
            sim_state_id = sim_state_id,
            value_str = value_str,
        )
        if isinstance( sim_state, FrigateCameraMotionState ):
            sim_entity = self.get_sim_entity_by_id( sim_entity_id = sim_entity_id )
            sim_camera = FrigateSimCamera( sim_entity = sim_entity )
            object_label = sim_camera.object_presence_sim_state.value
            FrigateSimEventManager().add_motion_value(
                frigate_sim_camera = sim_camera,
                motion_value = bool( sim_state.value ),
                object_label = object_label,
            )
        return sim_state
