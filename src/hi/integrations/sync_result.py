"""
Transient data shapes returned by integration sync operations.

The framework owns the sync workflow (pre-sync modal, sync view,
post-sync dispatcher modal). Each integration's
``IntegrationSynchronizer.sync()`` returns an
``IntegrationSyncResult`` describing what happened during sync —
title, structured change counts, info/error notes — plus an
optional ``EntityPlacementInput`` that drives the dispatcher modal
when the sync produced new entities to place.

The placement input shape lives in ``hi.apps.entity.entity_placement``
because it isn't sync-specific: any future flow that bulk-places
entities (e.g., a "place unplaced items" recovery feature) builds
the same shape from a different source. Sync is one supplier among
several.

The result modal renders a counts-driven lead summary
("N created, M updated, R removed") plus collapsible Details (the
``info_list``) and Errors (the ``error_list``) sections. Per-change
events are not duplicated into the lists — counts capture them.
``info_list`` carries diagnostic context the counts can't express
("Found N upstream items", "Filtered N by allowlist", etc.).
"""
from dataclasses import dataclass, field
from typing import List, Optional

from hi.apps.entity.entity_placement import EntityPlacementInput


@dataclass
class IntegrationSyncResult:
    """Outcome of a single integration sync run.

    ``placement_input`` is None when the sync produced no new
    entities to place (the typical refresh-with-no-new-items case);
    populated when there's something for the dispatcher modal to
    show. The framework uses presence/absence of placement_input —
    not emptiness checks against groups/ungrouped_items — to decide
    whether to show the dispatcher.

    ``created_count`` / ``updated_count`` / ``removed_count`` are
    structured signal for the result modal's lead summary. They're
    bumped per-event by synchronizers; the modal renders one
    sentence from the totals rather than asking the operator to
    scan a per-event list.

    ``info_list`` carries diagnostic notes — "Found N upstream
    items", "Filtered N by allowlist" — that count totals can't
    express. Rendered as a collapsible Details section in the
    result modal. ``error_list`` is the parallel for failures.
    """
    title: str
    placement_input: Optional[EntityPlacementInput] = None
    created_count: int = 0
    updated_count: int = 0
    removed_count: int = 0
    info_list: List[str] = field(default_factory=list)
    error_list: List[str] = field(default_factory=list)
    footer_message: str = ''

    @property
    def has_changes(self) -> bool:
        """True if the sync produced any operator-relevant change.
        Drives the 'Nothing new' lead line when False."""
        return bool(
            self.created_count
            or self.updated_count
            or self.removed_count
        )
