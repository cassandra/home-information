from typing import List

from hi.simulator.services.base_models import SimEntityDefinition
from hi.simulator.services.service_simulator import ServiceSimulator

from .sim_models import FRIGATE_SIM_ENTITY_DEFINITION_LIST


class FrigateSimulator( ServiceSimulator ):
    """Simulator entry point for the Frigate integration.

    Mirrors the ZoneMinder simulator in role: discovers per-camera
    sim_entities, dispatches HA-shape API calls to ``service_dispatchers``,
    serves JPEG snapshots, etc. Scaffolding stub — the entity
    definition list is empty until feature work fills it in.
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
