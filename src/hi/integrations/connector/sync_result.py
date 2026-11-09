"""
Transient data shapes returned by integration sync operations.

The framework owns the sync workflow (pre-sync modal, sync view,
post-sync placement modal). Each integration's
``IntegrationConnector.sync()`` returns an
``IntegrationSyncResult`` describing what happened during sync --
title, structured change counts, info/error notes -- plus an
optional ``EntityPlacementInput`` that drives the placement modal
when the sync produced new entities to place.

The placement input shape lives in ``hi.apps.entity.entity_placement``
because it isn't sync-specific: sync is one supplier among
several. The shape is built from entities, not from sync-time
context.

Counts are derived from list lengths -- the lists are the source
of truth. ``info_list`` carries diagnostic context the per-item
lists can't express ("Found N upstream items", "Filtered N by
allowlist", etc.).
"""
from dataclasses import dataclass, field
from typing import List, Optional

from hi.apps.entity.entity_placement import EntityPlacementInput
from hi.apps.entity.models import Entity
from hi.integrations.transient_models import IntegrationKey


@dataclass
class IntegrationSyncItem:
    """An item in a preview category list: the HI-side display name
    plus the integration key, so the operator can line up what HI
    calls an item with how the upstream system identifies it.

    ``name`` is empty when the preview cannot resolve a display name
    (e.g., the framework default preview's upstream additions, which
    are known only by key). ``__str__`` returns the name so the
    shared result partials render items and plain names the same way.
    """
    name: str
    integration_key: Optional[IntegrationKey] = None

    def __str__(self):
        return self.name


@dataclass
class IntegrationSyncResult:
    """Outcome of a single integration sync run.

    ``placement_input`` is None when the sync produced no new
    entities to place; populated when there's something for the
    placement modal to show. The framework uses presence/absence of
    placement_input -- not emptiness checks against
    groups/ungrouped_items -- to decide whether to show the
    placement.

    ``created_list`` / ``updated_list`` / ``reconnected_list`` /
    ``detached_list`` / ``removed_list`` hold the *names* of entities
    affected by this sync run, populated by the per-integration
    synchronizer as it walks upstream items. Names only --
    per-attribute change detail is intentionally not surfaced.

    The five categories are mutually exclusive for any given entity
    in a single sync run:
      * ``created_list``      -- brand new entities this sync.
      * ``updated_list``      -- existing primary-matched entities
                                 whose payload changed.
      * ``reconnected_list``  -- previously-detached entities that
                                 were re-attached this sync.
      * ``detached_list``     -- entities preserved with user data on
                                 this sync. They retain their
                                 custom attributes / layout / etc.
      * ``removed_list``      -- entities hard-deleted this sync.

    ``info_list`` carries diagnostic notes -- "Found N upstream
    items", "Filtered N by allowlist", ambiguous-reconnect
    breadcrumbs -- that the per-item lists can't express.
    ``error_list`` is the parallel for failures. ``conflict_list``
    names upstream items the sync left untouched because applying
    them would take over integration keys owned by another HI entity;
    the operator resolves these upstream.

    ``created_entities`` carries the just-created ``Entity``
    instances back to the framework caller, which passes them
    through ``gateway.group_entities_for_placement`` to build the
    ``placement_input``. Keeping the grouping out of the connector
    keeps Connect-sync and Import-run flows on a single grouping
    method per integration.
    """
    title: str
    placement_input: Optional[EntityPlacementInput] = None
    created_entities: List[Entity] = field(default_factory=list)
    created_list: List[str] = field(default_factory=list)
    updated_list: List[str] = field(default_factory=list)
    reconnected_list: List[str] = field(default_factory=list)
    detached_list: List[str] = field(default_factory=list)
    removed_list: List[str] = field(default_factory=list)
    info_list: List[str] = field(default_factory=list)
    error_list: List[str] = field(default_factory=list)
    conflict_list: List[str] = field(default_factory=list)
    footer_message: str = ''
    items_filtered_count: int = 0

    @property
    def has_changes(self) -> bool:
        """True if the sync produced any operator-relevant change."""
        return bool(
            self.created_list
            or self.updated_list
            or self.reconnected_list
            or self.detached_list
            or self.removed_list
        )

    @property
    def is_successful(self) -> bool:
        """True if HI is now in line with upstream: no errors and no
        conflicts left for the operator to resolve."""
        return not ( self.error_list or self.conflict_list )


@dataclass
class IntegrationSyncPreviewResult(IntegrationSyncResult):
    """Preview-time result for a sync that has not been executed.

    Shape-compatible with ``IntegrationSyncResult`` so the result-modal
    partials render either. The ``created_list`` / ``detached_list`` /
    ``removed_list`` entries are ``IntegrationSyncItem`` instances
    rather than names, so the preview can show each item's
    integration key alongside its HI name.

    ``approximation_message`` is a prose disclaimer about preview
    fidelity (what wasn't predicted, or couldn't be), rendered as a
    small callout in the preview-result modal. ``None`` when the
    preview is full-fidelity and has nothing to caveat.
    """
    created_list: List[IntegrationSyncItem] = field(default_factory=list)
    detached_list: List[IntegrationSyncItem] = field(default_factory=list)
    removed_list: List[IntegrationSyncItem] = field(default_factory=list)
    approximation_message: Optional[str] = None
