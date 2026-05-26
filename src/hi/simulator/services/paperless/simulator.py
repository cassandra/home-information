"""Paperless-ngx simulator: parametric document-search responses.

Unlike the entity-shaped simulators (HASS, HomeBox, ZoneMinder),
paperless-ngx has no 1-to-1 mapping onto HI Entities — its
contribution is the ATTRIBUTE_REFERENCE capability, which produces
TEXT attributes on existing Entity / Location records, not new
entities. So this simulator has no SimEntities and no persistent
corpus. Instead it generates synthetic search results on the fly,
shaped by a small set of operator-tunable knobs held on the
singleton:

  - result_count   : how many documents each search returns (chosen
                     to exercise empty / single / multi-page picker
                     rendering paths)
  - mime_mix       : which mime-type mix populates result rows (PDF
                     only, images only, plain text only, or mixed)
  - thumbnails     : whether the simulator's
                     ``/api/documents/<id>/thumb/`` endpoint serves
                     a thumbnail (when off, the endpoint 404s and
                     the picker falls back to its icon)
  - snippets       : whether each result carries a content snippet
                     (exercises picker layout with / without it)
  - latency_ms     : artificial latency on the documents-list
                     endpoint, for surfacing any debounce or
                     loading-state issues in the picker

Settings live in memory on the singleton (same lifecycle as
HomeBox's ``_api_version``) — lost on server restart, survives
SimProfile switches.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from hi.simulator.services.base_models import SimEntityDefinition
from hi.simulator.services.service_simulator import ServiceSimulator


class MimeMix( Enum ):
    """Which mime types populate generated search results. Drives
    the picker's thumbnail / fallback-icon path through different
    code branches."""

    PDF_ONLY    = 'PDF only'
    IMAGE_ONLY  = 'Images only'
    TEXT_ONLY   = 'Plain text only'
    MIXED       = 'Mixed'

    @classmethod
    def default(cls) -> 'MimeMix':
        return cls.MIXED

    @property
    def label(self) -> str:
        return self.value


# Discrete result counts the operator can pick from the extras form.
# Chosen to exercise distinct picker rendering paths: empty,
# single-result, small-multi, scroll-into-view, and large-page.
RESULT_COUNT_CHOICES = ( 0, 1, 3, 10, 50 )


@dataclass
class PaperlessSimSettings:
    """Knobs that parametrize every documents-search response. Held
    on the PaperlessSimulator singleton; ephemeral."""

    result_count : int     = 3
    mime_mix     : MimeMix = MimeMix.MIXED
    thumbnails   : bool    = True
    snippets     : bool    = True
    latency_ms   : int     = 0


class PaperlessSimulator( ServiceSimulator ):
    """Stub paperless-ngx server. Responds to any documents query
    with a parametrically-generated result list shaped by the
    operator-tuned ``PaperlessSimSettings``."""

    def __init_singleton__( self ):
        # Set BEFORE initialize() so a SimProfile switch does NOT
        # reset operator-tuned settings (same lifecycle as
        # ``_fault_mode`` on the base class).
        self._settings = PaperlessSimSettings()
        super().__init_singleton__()
        return

    @property
    def id(self) -> str:
        return 'paperless'

    @property
    def label(self) -> str:
        return 'Paperless-ngx'

    @property
    def integration_urls(self) -> List[ tuple ]:
        return [ ( 'Paperless API base', 'services/paperless/' ) ]

    @property
    def settings(self) -> PaperlessSimSettings:
        return self._settings

    def set_settings( self, settings : PaperlessSimSettings ) -> None:
        self._settings = settings
        return

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        # Paperless contributes only via ATTRIBUTE_REFERENCE — no
        # SimEntity rows ever, so the service page's entity-list
        # area renders empty. The extras pane carries the operator
        # UI.
        return []

    @property
    def extras_template_name(self) -> str:
        return 'paperless/panes/settings_form.html'

    @property
    def extras_context(self) -> Dict:
        return {
            'settings': self._settings,
            'result_count_choices': RESULT_COUNT_CHOICES,
            'mime_mix_choices': list( MimeMix ),
        }
