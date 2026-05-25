from dataclasses import dataclass, field
from typing import List


@dataclass
class CandidateItem:
    """One upstream item surfaced by Importer.get_candidate_items().

    ``integration_name`` is the per-integration unique identifier for
    the upstream item; matched against existing entities'
    ``integration_name`` to detect already-imported items.
    """
    name: str
    integration_name: str


@dataclass
class IntegrationDiscardResult:
    """Outcome of an Importer.discard_imported_data() invocation.

    ``count`` is the number of imported entities removed. ``errors``
    carries per-entity failure messages; an empty list means clean
    removal.
    """
    count: int = 0
    errors: List[str] = field(default_factory=list)
