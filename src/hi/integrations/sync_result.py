"""
Transient data shapes returned by integration sync operations.

The framework owns the sync workflow (pre-sync modal, sync view,
post-sync dispatcher modal in Phase 3). Each integration's
``IntegrationSynchronizer.sync()`` returns an
``IntegrationSyncResult`` describing what was imported and how those
items are grouped, plus message/error lines for the result modal.

Grouping contract:

* ``groups`` is populated when the integration has a domain notion
  of grouping for imported items (e.g., HASS areas, ZM cameras).
  The synchronizer decides what makes sense; the framework never
  overrides those choices with count-based heuristics.
* ``ungrouped_items`` is populated when the integration has no
  domain grouping (e.g., HomeBox inventory items). The framework's
  dispatcher template decides how to surface ungrouped items in
  the UI; synchronizers do not name an absence.
* The same ``SyncResultItem`` must not appear both in a group and
  in ``ungrouped_items``.
* Removed and preserved entities are reported via ``message_list``
  (not as items), since the dispatcher offers no placement action
  for them.

The ``title`` / ``message_list`` / ``error_list`` fields mirror the
shape of the legacy ``ProcessingResult`` so the existing result-modal
template renders without changes during Phase 2; the dispatcher modal
in Phase 3 will consume ``groups`` / ``ungrouped_items`` directly.
This class deliberately does not depend on ``ProcessingResult`` so
its evolution is independent.
"""
from dataclasses import dataclass, field
from typing import List

from hi.apps.entity.models import Entity


@dataclass
class SyncResultItem:
    """A single entity imported during sync.

    ``key`` is a stable identifier the dispatcher uses to address
    this item across modal turns; integration-derived (typically
    ``integration_id:integration_name``).
    """
    key: str
    label: str
    entity: Entity


@dataclass
class SyncResultItemGroup:
    """A synchronizer-defined grouping of imported items.

    Synchronizers create groups when their domain has a meaningful
    grouping notion (HASS areas, ZM "Cameras"). The framework
    presents groups verbatim in the dispatcher modal.
    """
    label: str
    items: List[SyncResultItem] = field(default_factory=list)


@dataclass
class IntegrationSyncResult:
    """Outcome of a single integration sync run.

    Returned by ``IntegrationSynchronizer.sync()`` and consumed by
    the framework's sync result modal (Phase 2) and dispatcher modal
    (Phase 3). See module docstring for the grouping contract.
    """
    title: str
    groups: List[SyncResultItemGroup] = field(default_factory=list)
    ungrouped_items: List[SyncResultItem] = field(default_factory=list)
    message_list: List[str] = field(default_factory=list)
    error_list: List[str] = field(default_factory=list)
    footer_message: str = ''
