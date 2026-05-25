from dataclasses import dataclass, field
from typing import List, Optional

from hi.apps.entity.entity_placement import EntityPlacementInput


@dataclass
class IntegrationImportResult:
    """Outcome of a single Importer.run_import() invocation.

    Parallel to IntegrationSyncResult but with import-specific fields.
    Imports are add-only: items not already in HI are created;
    pre-existing matches are reported as skipped. There is no
    update/remove path.

    ``placement_input`` is None when the import produced no new
    entities to place; populated when the result modal should expose
    the post-import placement flow.
    """
    title: str
    placement_input: Optional[EntityPlacementInput] = None
    items_imported_count: int = 0
    items_skipped_count: int = 0
    imported_list: List[str] = field(default_factory=list)
    info_list: List[str] = field(default_factory=list)
    error_list: List[str] = field(default_factory=list)

    @property
    def has_imports(self) -> bool:
        return self.items_imported_count > 0
