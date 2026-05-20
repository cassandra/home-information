from typing import List

from hi.simulator.services.base_models import SimEntityDefinition, SimState
from hi.simulator.services.service_simulator import ServiceSimulator

from .event_manager import FrigateSimEventManager
from .sim_models import (
    FRIGATE_SIM_ENTITY_DEFINITION_LIST,
    FRIGATE_OBJECT_LABEL_NONE,
    FrigateCameraObjectPresenceState,
    FrigateCameraSimEntityFields,
    FrigateSimCamera,
)


class FrigateSimulator( ServiceSimulator ):
    """Simulator entry point for the Frigate integration.

    Each camera exposes a single discrete ``ObjectPresence``
    sim-state. Picking a class value declares "this is what's
    currently being detected"; picking ``none`` declares
    "nothing is detected". The override below translates value
    changes into the underlying event lifecycle.
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
        """Override so ObjectPresence value changes drive Frigate's
        event lifecycle in the ``FrigateSimEventManager``:

        - New value ``none`` → close the currently-open event (if any).
        - New value matches the open event's label → no-op (the
          operator re-picked the same class).
        - New value differs from the open event's label → close current,
          open new event with the new label. Mirrors real Frigate's
          "new object class -> new tracked event" behavior.
        - New value with no open event → open new event with this label.
        """
        sim_state = super().set_sim_state(
            sim_entity_id = sim_entity_id,
            sim_state_id = sim_state_id,
            value_str = value_str,
        )

        if isinstance( sim_state, FrigateCameraObjectPresenceState ):
            sim_entity = self.get_sim_entity_by_id( sim_entity_id = sim_entity_id )
            sim_camera = FrigateSimCamera( sim_entity = sim_entity )
            FrigateSimEventManager().set_current_object(
                frigate_sim_camera = sim_camera,
                object_label = sim_state.value,
                none_label = FRIGATE_OBJECT_LABEL_NONE,
            )
        return sim_state
