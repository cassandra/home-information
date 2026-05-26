"""
Coverage for the placement-stats viability helper.

These tests pin the measurement contract integrations rely on when
picking among candidate ``EntityPlacementInput`` partitionings.
Threshold defaults are tested at the boundaries so a future
adjustment that drifts them silently fails loudly.
"""
import logging

from django.test import TestCase

from hi.apps.entity.entity_placement import (
    PLACEMENT_DEFAULT_HEADING,
    EntityPlacementGroup,
    EntityPlacementInput,
    EntityPlacementItem,
)
from hi.integrations.placement_stats import (
    compute_grouping_stats,
)


logging.disable(logging.CRITICAL)


def _item(key: str) -> EntityPlacementItem:
    """Build a stub item. The stats helper never touches ``entity``,
    so a sentinel is fine."""
    return EntityPlacementItem(key=key, label=key, entity=None)


def _input(group_sizes, ungrouped=0) -> EntityPlacementInput:
    """Build an EntityPlacementInput with named groups of the
    requested sizes plus ``ungrouped`` ungrouped items. Keys are
    globally unique so the modal-key invariant holds."""
    groups = []
    counter = 0
    for index, size in enumerate(group_sizes):
        items = []
        for _ in range(size):
            items.append(_item(f'k{counter}'))
            counter += 1
        groups.append(EntityPlacementGroup(label=f'g{index}', items=items))
    ungrouped_items = []
    for _ in range(ungrouped):
        ungrouped_items.append(_item(f'k{counter}'))
        counter += 1
    return EntityPlacementInput(groups=groups, ungrouped_items=ungrouped_items)


class TestComputeGroupingStats(TestCase):

    def test_empty_input_yields_zero_stats(self):
        stats = compute_grouping_stats(EntityPlacementInput())
        self.assertEqual(stats.total_items, 0)
        self.assertEqual(stats.grouped_items, 0)
        self.assertEqual(stats.group_count, 0)
        self.assertEqual(stats.largest_group_size, 0)
        self.assertEqual(stats.coverage, 0.0)
        self.assertEqual(stats.concentration, 0.0)
        self.assertEqual(stats.avg_group_size, 0.0)

    def test_all_grouped_counts_total_and_largest(self):
        stats = compute_grouping_stats(_input([3, 2, 5]))
        self.assertEqual(stats.total_items, 10)
        self.assertEqual(stats.grouped_items, 10)
        self.assertEqual(stats.group_count, 3)
        self.assertEqual(stats.largest_group_size, 5)
        self.assertEqual(stats.coverage, 1.0)
        self.assertAlmostEqual(stats.concentration, 0.5)
        self.assertAlmostEqual(stats.avg_group_size, 10 / 3)

    def test_ungrouped_items_dilute_coverage(self):
        stats = compute_grouping_stats(_input([2, 2], ungrouped=6))
        self.assertEqual(stats.total_items, 10)
        self.assertEqual(stats.grouped_items, 4)
        self.assertEqual(stats.coverage, 0.4)
        self.assertEqual(stats.avg_group_size, 2.0)


class TestPlacementGroupingStatsIsViable(TestCase):
    """Pin the default-threshold viability decision at boundaries."""

    def test_empty_never_viable(self):
        self.assertFalse(compute_grouping_stats(EntityPlacementInput()).is_viable())

    def test_balanced_multi_group_is_viable(self):
        # 12 items across 4 groups of 3 — coverage 1.0, concentration 0.25,
        # avg 3.0, group_count 4: comfortably viable on every axis.
        self.assertTrue(compute_grouping_stats(_input([3, 3, 3, 3])).is_viable())

    def test_below_coverage_threshold_not_viable(self):
        # 10 items, 4 grouped → coverage 0.4 (< 0.5 default).
        self.assertFalse(compute_grouping_stats(_input([2, 2], ungrouped=6)).is_viable())

    def test_single_group_not_viable(self):
        # group_count 1 falls below min_group_count default of 2.
        self.assertFalse(compute_grouping_stats(_input([10])).is_viable())

    def test_high_concentration_not_viable(self):
        # 12 items: 11 in one group, 1 in another. concentration ≈ 0.92,
        # over the 0.9 default ceiling.
        self.assertFalse(compute_grouping_stats(_input([11, 1])).is_viable())

    def test_one_item_per_group_sprawl_not_viable(self):
        # 10 items each in its own group: avg_group_size 1.0 (< 2.0),
        # AND effective_max_groups clamped to total_items // 2 = 5,
        # so 10 groups is over the ceiling. Either gate disqualifies.
        self.assertFalse(compute_grouping_stats(_input([1] * 10)).is_viable())

    def test_small_batch_clamps_max_group_count(self):
        # Six items in three groups of two: avg 2.0 (at floor), but
        # effective_max_groups = 6 // 2 = 3 — still within bounds.
        self.assertTrue(compute_grouping_stats(_input([2, 2, 2])).is_viable())

    def test_small_batch_above_clamp_not_viable(self):
        # Six items in four groups: effective_max_groups = 6 // 2 = 3,
        # so 4 distinct groups disqualifies even though the avg
        # (1.5) is the bigger fail on its own.
        self.assertFalse(compute_grouping_stats(_input([2, 2, 1, 1])).is_viable())

    def test_custom_thresholds_override_defaults(self):
        # Same shape as test_below_coverage_threshold_not_viable, but
        # lowering ``min_coverage`` to 0.4 lets it through. The
        # avg_group_size (2.0) and group_count (2) need to stay
        # within their defaults too; this batch sits exactly at the
        # avg floor and effective_max_groups (10 // 2 = 5).
        stats = compute_grouping_stats(_input([2, 2], ungrouped=6))
        self.assertTrue(stats.is_viable(min_coverage=0.4))


class TestEntityPlacementInputHeading(TestCase):
    """The grouping dimension's heading rides on the placement
    input itself so the modal can render it without the supplier
    threading it through a parallel channel."""

    def test_default_heading_matches_module_constant(self):
        self.assertEqual(
            EntityPlacementInput().heading,
            PLACEMENT_DEFAULT_HEADING,
        )
        self.assertEqual(PLACEMENT_DEFAULT_HEADING, 'Item Type')

    def test_supplier_can_set_dimension_specific_heading(self):
        placement_input = EntityPlacementInput(heading='HomeBox Location')
        self.assertEqual(placement_input.heading, 'HomeBox Location')
