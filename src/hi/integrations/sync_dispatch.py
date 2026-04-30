"""
Transient shapes for the post-sync placement dispatcher.

The dispatcher modal shows the operator the entities returned by a
sync and lets them assign each one (directly or via group default)
to a LocationView. After the operator submits, the dispatcher view
expands group choices into per-entity decisions, applies them via
``EntityPlacer``, and renders a post-dispatch summary modal.

Group identity does not survive the form-parsing layer:
``PlacementDecision`` is per-entity. The grouping abstraction stays
in ``IntegrationSyncResult`` and the dispatcher template + POST
handler. Everything downstream (placer, summary) reasons in
entities.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from hi.apps.entity.models import Entity
from hi.apps.location.models import LocationView


# Form-input sentinels for the dispatcher modal's <select> values.
#
# An empty string ('') means "inherit from parent level" — the
# top-level "(skip all)" reads as effective None; group-level
# "(use top)" reads as the resolved top choice; entity-level
# "(use group)" reads as the resolved group choice.
#
# FORM_VALUE_SKIP is an explicit "do not place this entity" choice
# that overrides any inherited parent value. Useful when the operator
# picks a top-level view but wants to opt out specific groups or
# entities.
#
# FORM_VALUE_NEW_VIEW is offered only at the top level. On submit,
# the dispatcher creates a single new LocationView using the
# integration label as the name and treats it as if the operator had
# picked that view at the top level. Group/entity overrides to other
# existing views still apply.
FORM_VALUE_SKIP = '__skip__'
FORM_VALUE_NEW_VIEW = '__new__'


@dataclass(frozen=True)
class PlacementDecision:
    """One entity → location_view assignment chosen by the operator.

    ``location_view`` is None when the operator chose to skip
    placement for this entity. Skipped decisions are filtered out
    before placement and counted toward the dispatcher outcome's
    ``skipped_entity_count``.
    """
    entity: Entity
    location_view: Optional[LocationView]


@dataclass(frozen=True)
class ViewPlacementSummary:
    """One affected LocationView + how many principal entities the
    dispatcher placed into it."""
    location_view: LocationView
    placed_entity_count: int


@dataclass
class DispatcherOutcome:
    """Result of one dispatcher submission. Drives the post-dispatch
    modal: per-view summary lines, primary "Refine" button, skipped
    count when present.
    """
    summaries: List[ViewPlacementSummary] = field(default_factory=list)
    skipped_entity_count: int = 0

    @property
    def affected_views(self) -> List[LocationView]:
        return [s.location_view for s in self.summaries]

    @property
    def total_placed(self) -> int:
        return sum(s.placed_entity_count for s in self.summaries)

    @property
    def primary_summary(self) -> Optional[ViewPlacementSummary]:
        """Highest-count summary; ties broken by first-seen (stable
        max). None when no entity was placed."""
        if not self.summaries:
            return None
        # `max` with key returns the first occurrence on ties.
        return max(self.summaries, key=lambda s: s.placed_entity_count)

    @property
    def secondary_summaries(self) -> List[ViewPlacementSummary]:
        """All summaries except the primary, in input order."""
        primary = self.primary_summary
        if primary is None:
            return []
        result = []
        skipped = False
        for summary in self.summaries:
            if not skipped and summary is primary:
                skipped = True
                continue
            result.append(summary)
        return result
