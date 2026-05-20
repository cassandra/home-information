from typing import List

from hi.simulator.services.base_models import SimEntityDefinition
from hi.simulator.services.service_simulator import ServiceSimulator

from .sim_models import (
    FRIGATE_SIM_ENTITY_DEFINITION_LIST,
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
