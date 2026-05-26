from dataclasses import dataclass, field
from typing import List, Optional

from hi.apps.entity.entity_placement import EntityPlacementInput
from hi.apps.entity.models import Entity


@dataclass
class CandidateItem:
    """One upstream item surfaced by IntegrationImporter.get_candidate_items().

    ``integration_name`` is the per-integration unique identifier for
    the upstream item; matched against existing entities'
    ``integration_name`` to detect already-imported items.
    """
    name: str
    integration_name: str


@dataclass
class IntegrationImportResult:
    """Outcome of a single IntegrationImporter.run_import() invocation.

    Parallel to IntegrationSyncResult but with import-specific fields.
    Imports are add-only: items not already in HI are created;
    pre-existing matches are reported as skipped. There is no
    update/remove path.

    ``placement_input`` is None when the import produced no new
    entities to place; populated when the result modal should expose
    the post-import placement flow.

    ``created_entities`` carries the just-created ``Entity``
    instances back to the framework caller, which passes them
    through ``gateway.group_entities_for_placement`` to build the
    ``placement_input`` — same shape as the Connect-sync flow.
    """
    title: str
    placement_input: Optional[EntityPlacementInput] = None
    created_entities: List[Entity] = field(default_factory=list)
    items_imported_count: int = 0
    items_skipped_count: int = 0
    items_filtered_count: int = 0
    imported_list: List[str] = field(default_factory=list)
    info_list: List[str] = field(default_factory=list)
    error_list: List[str] = field(default_factory=list)
    footer_message: str = ''

    @property
    def has_imports(self) -> bool:
        return self.items_imported_count > 0


@dataclass
class IntegrationDiscardResult:
    """Outcome of an IntegrationImporter.discard_imported_data() invocation.

    ``count`` is the number of imported entities removed. ``errors``
    carries per-entity failure messages; an empty list means clean
    removal.
    """
    count: int = 0
    errors: List[str] = field(default_factory=list)
