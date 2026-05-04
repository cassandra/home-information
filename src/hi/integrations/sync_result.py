"""
Transient data shapes returned by integration sync operations.

The framework owns the sync workflow (pre-sync modal, sync view,
post-sync placement modal). Each integration's
``IntegrationSynchronizer.sync()`` returns an
``IntegrationSyncResult`` describing what happened during sync —
title, structured change counts, info/error notes — plus an
optional ``EntityPlacementInput`` that drives the placement modal
when the sync produced new entities to place.

The placement input shape lives in ``hi.apps.entity.entity_placement``
because it isn't sync-specific: any future flow that bulk-places
entities (e.g., a "place unplaced items" recovery feature) builds
the same shape from a different source. Sync is one supplier among
several.

The result modal renders a counts-driven lead summary
("N created, M updated, R removed") with per-category disclosures
that enumerate the affected items by name, plus collapsible
Details (``info_list``) and Errors (``error_list``) sections.
Counts are derived from list lengths — the lists are the source
of truth. ``info_list`` carries diagnostic context the per-item
lists can't express ("Found N upstream items", "Filtered N by
allowlist", etc.).
"""
from dataclasses import dataclass, field
from typing import List, Optional

from hi.apps.entity.entity_placement import EntityPlacementInput


@dataclass
class IntegrationSyncResult:
    """Outcome of a single integration sync run.

    ``placement_input`` is None when the sync produced no new
    entities to place (the typical refresh-with-no-new-items case);
    populated when there's something for the placement modal to
    show. The framework uses presence/absence of placement_input —
    not emptiness checks against groups/ungrouped_items — to decide
    whether to show the placement.

    ``created_list`` / ``updated_list`` / ``removed_list`` hold the
    *names* of entities affected by this sync run, populated by the
    per-integration synchronizer as it walks upstream items. The
    result modal uses list length for the count badges and the
    list contents for per-category "Show items" disclosures so the
    operator can see which entities were touched. Names only —
    per-attribute change detail is intentionally not surfaced.

    ``info_list`` carries diagnostic notes — "Found N upstream
    items", "Filtered N by allowlist" — that the per-item lists
    can't express. Rendered as a collapsible Details section in
    the result modal. ``error_list`` is the parallel for failures.
    """
    title: str
    placement_input: Optional[EntityPlacementInput] = None
    created_list: List[str] = field(default_factory=list)
    updated_list: List[str] = field(default_factory=list)
    removed_list: List[str] = field(default_factory=list)
    info_list: List[str] = field(default_factory=list)
    error_list: List[str] = field(default_factory=list)
    footer_message: str = ''

    @property
    def has_changes(self) -> bool:
        """True if the sync produced any operator-relevant change.
        Drives the 'Nothing new' lead line when False."""
        return bool(
            self.created_list
            or self.updated_list
            or self.removed_list
        )
