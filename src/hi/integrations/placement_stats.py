"""
Statistics + viability scoring over an ``EntityPlacementInput``.

Integrations that have multiple plausible grouping dimensions
(HomeBox: Location, Tag, EntityType) need a way to ask "is this
candidate grouping actually useful, or is it one giant bucket / one
item per bucket?". This module supplies the measurement; the
selection logic stays in the integration so it can compose strategies
however it likes (ordered fallback, score-based, hand-rolled).

Typical use from an integration's ``group_entities_for_placement``::

    candidate = self._group_by_location( entities )
    if compute_grouping_stats( candidate ).is_viable():
        return candidate
    candidate = self._group_by_tag( entities )
    if compute_grouping_stats( candidate ).is_viable():
        return candidate
    return super().group_entities_for_placement( entities )

The integration owns what counts as "in a group": items placed in
``EntityPlacementInput.ungrouped_items`` are treated as
no-signal; items in a labeled fallback group (e.g., "Untagged") are
treated as a normal group because that's how the placement modal
renders them.
"""

from dataclasses import dataclass
import logging
from typing import List

from hi.apps.entity.entity_placement import EntityPlacementInput


logger = logging.getLogger(__name__)


# Default viability thresholds. Tuned for the tens-of-items import
# batches the placement modal sees today. Exposed as constants so
# callers can read them and override individual ones per-call.
DEFAULT_MIN_COVERAGE      : float = 0.5   # at least half the items must land in a named group
DEFAULT_MIN_GROUP_COUNT   : int   = 2     # at least two distinct groups
DEFAULT_MAX_GROUP_COUNT   : int   = 15    # too many groups overwhelms the modal
DEFAULT_MIN_AVG_GROUP_SIZE: float = 2.0   # avoid one-item-per-group sprawl
DEFAULT_MAX_CONCENTRATION : float = 0.9   # a single group holding >90% isn't grouping


@dataclass(frozen=True)
class PlacementGroupingStats:
    """Single-pass measurements over an ``EntityPlacementInput``.

    "Grouped items" are items in any named group, including a
    fallback group like "Untagged". "Ungrouped items" are items
    in ``EntityPlacementInput.ungrouped_items`` — the items the
    modal renders under its built-in 'Other items' section, which
    by convention means the integration found no signal for them.
    """
    total_items         : int
    grouped_items       : int
    group_count         : int
    largest_group_size  : int
    group_sizes         : List[int]

    @property
    def coverage(self) -> float:
        """Fraction of total items that landed in a named group."""
        if self.total_items == 0:
            return 0.0
        return self.grouped_items / self.total_items

    @property
    def concentration(self) -> float:
        """Largest group size as a fraction of grouped items. Close
        to 1.0 means one dominant group — the strategy isn't really
        partitioning."""
        if self.grouped_items == 0:
            return 0.0
        return self.largest_group_size / self.grouped_items

    @property
    def avg_group_size(self) -> float:
        if self.group_count == 0:
            return 0.0
        return self.grouped_items / self.group_count

    def is_viable(
            self,
            *,
            min_coverage       : float = DEFAULT_MIN_COVERAGE,
            min_group_count    : int   = DEFAULT_MIN_GROUP_COUNT,
            max_group_count    : int   = DEFAULT_MAX_GROUP_COUNT,
            min_avg_group_size : float = DEFAULT_MIN_AVG_GROUP_SIZE,
            max_concentration  : float = DEFAULT_MAX_CONCENTRATION,
    ) -> bool:
        """Apply viability thresholds. ``max_group_count`` is
        additionally clamped to ``total_items // 2`` so a 6-item
        batch can't show 6 one-item groups even if the configured
        ceiling permits it."""
        if self.total_items == 0:
            return False
        effective_max_groups = min( max_group_count, self.total_items // 2 )
        return (
            self.coverage          >= min_coverage
            and self.group_count   >= min_group_count
            and self.group_count   <= effective_max_groups
            and self.avg_group_size >= min_avg_group_size
            and self.concentration <= max_concentration
        )


def compute_grouping_stats(
        placement_input : EntityPlacementInput,
) -> PlacementGroupingStats:
    """Single-pass measurement over a candidate ``EntityPlacementInput``.

    The caller has already built the candidate (one
    ``EntityPlacementInput`` per dimension it's considering); this
    function tells them how useful that partitioning is.
    """
    group_sizes = [ len( group.items ) for group in placement_input.groups ]
    grouped_items = sum( group_sizes )
    ungrouped = len( placement_input.ungrouped_items )
    return PlacementGroupingStats(
        total_items         = grouped_items + ungrouped,
        grouped_items       = grouped_items,
        group_count         = len( group_sizes ),
        largest_group_size  = max( group_sizes ) if group_sizes else 0,
        group_sizes         = group_sizes,
    )
