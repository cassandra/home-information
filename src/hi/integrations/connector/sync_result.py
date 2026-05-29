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
    ``error_list`` is the parallel for failures.

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
    def has_displayable_created_list(self) -> bool:
        """True iff ``created_list`` contains at least one non-empty
        name worth rendering in the Created category section. The
        preview's framework default impl populates ``created_list``
        with placeholder empty entries to keep the stat-card "Created"
        count consistent with the upstream-added count; the templates
        use this to skip rendering an empty-bodied Created section in
        that case. For real sync results every entry is a real entity
        name and this is equivalent to ``bool(created_list)``."""
        return any(self.created_list)


@dataclass
class IntegrationSyncPreviewResult(IntegrationSyncResult):
    """Preview-time result for a sync that has not been executed.

    Shape-compatible with ``IntegrationSyncResult`` so the result-modal
    partials render either; carries two preview-specific fields:

    * ``approximation_message`` -- prose disclaimer about preview
      fidelity (what wasn't predicted, or couldn't be). Rendered as a
      small callout in the preview-result modal. ``None`` when the
      preview is full-fidelity and has nothing to caveat.

    * ``upstream_added_keys`` -- the integration_name tokens for items
      detected upstream but not present in HI. The default preview
      impl can't resolve these into display names (the upstream side
      is opaque at the framework layer), so they're hidden from the
      main visible result and surfaced via a collapsible debug section
      so the operator can verify what would be created without
      committing to sync. Stays empty when an integration's higher-
      fidelity override populates ``created_list`` with real names.
    """
    approximation_message: Optional[str] = None
    upstream_added_keys: List[str] = field(default_factory=list)
