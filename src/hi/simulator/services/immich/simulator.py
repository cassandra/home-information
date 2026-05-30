"""Immich simulator: parametric smart-search responses.

Contributes only the ATTRIBUTE_REFERENCE capability -- TEXT
attributes on existing Entity / Location records, no SimEntities of
its own. Search results are generated on the fly, shaped by
operator-tuned knobs on the singleton.

Auth-failure simulation is handled framework-wide via
``ServiceFaultMode``; this simulator does not enforce API keys of
its own.

Knobs:
  - result_count : how many assets each smart search returns
                   (0/1/3/10/50 -- exercises empty / single / multi
                   picker rendering paths).
  - include_exif : whether generated assets carry EXIF city /
                   country (drives the snippet on / off path in the
                   referencer's ``_build_secondary_text``).
  - latency_ms   : artificial latency on the smart-search endpoint,
                   for surfacing debounce or loading issues in the
                   picker.
"""
from dataclasses import dataclass
from typing import Dict, List

from hi.simulator.services.base_models import SimEntityDefinition
from hi.simulator.services.service_simulator import ServiceSimulator


# Discrete result counts the operator can pick; exercises distinct
# picker rendering paths.
RESULT_COUNT_CHOICES = ( 0, 1, 3, 10, 50 )


@dataclass
class ImmichSimSettings:
    """Knobs that parametrize every response. Held on the
    ImmichSimulator singleton; ephemeral."""

    result_count : int  = 3
    include_exif : bool = True
    latency_ms   : int  = 0


class ImmichSimulator( ServiceSimulator ):

    def __init_singleton__( self ):
        # Set BEFORE initialize() so a SimProfile switch does NOT
        # reset operator-tuned settings.
        self._settings = ImmichSimSettings()
        super().__init_singleton__()
        return

    @property
    def id(self) -> str:
        return 'immich'

    @property
    def label(self) -> str:
        return 'Immich'

    @property
    def integration_urls(self) -> List[ tuple ]:
        return [ ( 'Immich API base', 'services/immich/' ) ]

    @property
    def settings(self) -> ImmichSimSettings:
        return self._settings

    def set_settings( self, settings : ImmichSimSettings ) -> None:
        self._settings = settings
        return

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        return []

    @property
    def extras_template_name(self) -> str:
        return 'immich/panes/settings_form.html'

    @property
    def extras_context(self) -> Dict:
        return {
            'settings'             : self._settings,
            'result_count_choices' : RESULT_COUNT_CHOICES,
        }
