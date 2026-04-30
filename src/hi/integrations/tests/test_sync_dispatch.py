"""
Tests for sync_dispatch dataclasses (PlacementDecision,
ViewPlacementSummary, DispatcherOutcome).

Pure data shape behavior — primary/secondary helpers, total counts,
tie-breaking. The dispatcher view itself (form parsing, placement
application, modal rendering) is exercised in test_views.py.
"""
import logging

from django.test import SimpleTestCase

from hi.integrations.sync_dispatch import (
    DispatcherOutcome,
    ViewPlacementSummary,
)

logging.disable(logging.CRITICAL)


class _NamedView:
    """Stand-in for LocationView; only the name attribute is read by
    these tests."""
    def __init__(self, name):
        self.name = name
        self.id = 0


class DispatcherOutcomeTests(SimpleTestCase):

    def _summary(self, name, count):
        return ViewPlacementSummary(
            location_view=_NamedView(name), placed_entity_count=count,
        )

    def test_empty_outcome_has_no_primary(self):
        outcome = DispatcherOutcome()
        self.assertIsNone(outcome.primary_summary)
        self.assertEqual(outcome.secondary_summaries, [])
        self.assertEqual(outcome.total_placed, 0)
        self.assertEqual(outcome.affected_views, [])

    def test_primary_picks_highest_count(self):
        a = self._summary('A', 1)
        b = self._summary('B', 5)
        c = self._summary('C', 3)
        outcome = DispatcherOutcome(summaries=[a, b, c])
        self.assertIs(outcome.primary_summary, b)
        # Secondaries are everything else, in input order.
        self.assertEqual(outcome.secondary_summaries, [a, c])

    def test_primary_breaks_ties_by_first_seen(self):
        first = self._summary('First', 4)
        second = self._summary('Second', 4)
        outcome = DispatcherOutcome(summaries=[first, second])
        # `max` returns first occurrence on ties.
        self.assertIs(outcome.primary_summary, first)
        self.assertEqual(outcome.secondary_summaries, [second])

    def test_total_placed_sums_counts(self):
        outcome = DispatcherOutcome(summaries=[
            self._summary('A', 2),
            self._summary('B', 5),
        ])
        self.assertEqual(outcome.total_placed, 7)

    def test_skipped_count_is_independent_of_summaries(self):
        outcome = DispatcherOutcome(
            summaries=[self._summary('A', 1)],
            skipped_entity_count=3,
        )
        self.assertEqual(outcome.skipped_entity_count, 3)
        self.assertEqual(outcome.total_placed, 1)

    def test_affected_views_preserves_input_order(self):
        a = _NamedView('Alpha')
        b = _NamedView('Beta')
        outcome = DispatcherOutcome(summaries=[
            ViewPlacementSummary(location_view=a, placed_entity_count=1),
            ViewPlacementSummary(location_view=b, placed_entity_count=2),
        ])
        self.assertEqual(outcome.affected_views, [a, b])
