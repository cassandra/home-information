"""
Transient data shapes returned by integration sync operations.

The framework owns the sync workflow (pre-sync modal, sync view,
post-sync dispatcher modal). Each integration's
``IntegrationSynchronizer.sync()`` returns an
``IntegrationSyncResult`` describing what happened during sync —
title, message_list, error_list, footer_message — plus an optional
``EntityPlacementInput`` that drives the dispatcher modal when the
sync produced new entities to place.

The placement input shape lives in ``hi.apps.entity.entity_placement``
because it isn't sync-specific: any future flow that bulk-places
entities (e.g., a "place unplaced items" recovery feature) builds
the same shape from a different source. Sync is one supplier among
several.

The ``title`` / ``message_list`` / ``error_list`` / ``footer_message``
fields mirror the legacy ``ProcessingResult`` shape so the existing
result-modal template renders without changes; this class
deliberately does not depend on ``ProcessingResult`` so its
evolution is independent.
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
    """
    title: str
    placement_input: Optional[EntityPlacementInput] = None
    message_list: List[str] = field(default_factory=list)
    error_list: List[str] = field(default_factory=list)
    footer_message: str = ''
