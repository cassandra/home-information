"""Immich simulator: parametric smart-search responses.

Contributes only the EXTERNAL_REFERENCE capability -- TEXT
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
  - mime_mix     : which mime-type mix populates result rows
                   (images only, videos only, mixed). Drives the
                   ``_try_generate_from_original`` branch in the
                   referencer -- only image mimes pull original
                   bytes; video mimes skip that fetch.
  - include_exif : whether generated assets carry EXIF city /
                   country (drives the snippet on / off path in the
                   referencer's ``_build_secondary_text``).
  - thumbnails   : whether ``/api/assets/<id>/thumbnail`` serves a
                   PNG placeholder (when off the endpoint 404s and
                   HI falls back to the ``/api/assets/<id>/original``
                   bytes-to-thumbnail-png pipeline -- which produces
                   a HI-generated thumbnail with a different visual
                   so the operator can tell which path produced the
                   saved card's image). To exercise the full
                   no-thumbnail path (mime fallback icon on the
                   card), force a ``ServiceFaultMode.SERVER_ERROR``
                   so all endpoints fail.

Artificial latency is intentionally NOT a knob here -- the
framework ``ServiceFaultMode`` already exposes a ``SLOW`` mode that
covers the same operator need without per-simulator duplication.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from hi.simulator.services.base_models import SimEntityDefinition
from hi.simulator.services.service_simulator import ServiceSimulator


class MimeMix( Enum ):
    """Which mime types populate generated search results. Drives
    the referencer's image-vs-video gating through different code
    branches."""

    IMAGE_ONLY = 'Images only'
    VIDEO_ONLY = 'Videos only'
    MIXED      = 'Mixed'

    @classmethod
    def default(cls) -> 'MimeMix':
        return cls.MIXED

    @property
    def label(self) -> str:
        return self.value


# Discrete result counts the operator can pick; exercises distinct
# picker rendering paths.
RESULT_COUNT_CHOICES = ( 0, 1, 3, 10, 50 )


@dataclass
class ImmichSimSettings:
    """Knobs that parametrize every response. Held on the
    ImmichSimulator singleton; ephemeral."""

    result_count : int     = 3
    mime_mix     : MimeMix = MimeMix.MIXED
    include_exif : bool    = True
    thumbnails   : bool    = True


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
            'mime_mix_choices'     : list( MimeMix ),
        }
