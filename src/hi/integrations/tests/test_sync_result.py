"""
Tests for the IntegrationSyncResult shape.

Sync-vocabulary fields: title, structured change counts
(created/updated/removed), info_list / error_list / footer_message,
plus the optional placement_input that bridges to the dispatcher
modal when the sync produced new entities to place.

Tests for the EntityPlacementInput / EntityPlacementItem /
EntityPlacementGroup data shapes themselves live in
hi/apps/entity/tests/test_entity_placement.py.
"""
import logging

from django.test import SimpleTestCase

from hi.apps.entity.entity_placement import (
    EntityPlacementGroup,
    EntityPlacementInput,
    EntityPlacementItem,
)
from hi.integrations.sync_result import IntegrationSyncResult

logging.disable(logging.CRITICAL)


class _FakeEntity:
    """Stand-in for Entity used in shape tests; we never persist."""
    def __init__(self, name):
        self.name = name


class IntegrationSyncResultTests(SimpleTestCase):

    def test_default_collections_are_independent(self):
        """Default-factory lists must not be shared across instances.

        Regression guard for the standard mutable-default-arg trap;
        important because synchronizers append into these lists.
        """
        a = IntegrationSyncResult(title='A')
        b = IntegrationSyncResult(title='B')

        a.info_list.append('msg-a')
        a.error_list.append('err-a')

        self.assertEqual(b.info_list, [])
        self.assertEqual(b.error_list, [])

    def test_field_shape(self):
        """title / info_list / error_list / footer_message and the
        change counters all round-trip cleanly."""
        result = IntegrationSyncResult(
            title='Sync Done',
            created_count=3,
            updated_count=2,
            removed_count=1,
            info_list=['Found 50 upstream items'],
            error_list=['warning x'],
            footer_message='see settings',
        )
        self.assertEqual(result.title, 'Sync Done')
        self.assertEqual(result.created_count, 3)
        self.assertEqual(result.updated_count, 2)
        self.assertEqual(result.removed_count, 1)
        self.assertEqual(result.info_list, ['Found 50 upstream items'])
        self.assertEqual(result.error_list, ['warning x'])
        self.assertEqual(result.footer_message, 'see settings')

    def test_has_changes_true_when_any_count_nonzero(self):
        for kwargs in (
            {'created_count': 1},
            {'updated_count': 1},
            {'removed_count': 1},
            {'created_count': 1, 'updated_count': 1},
        ):
            result = IntegrationSyncResult(title='X', **kwargs)
            self.assertTrue(result.has_changes, kwargs)

    def test_has_changes_false_when_all_counts_zero(self):
        # Nothing-new refresh: no changes even if info_list has lines.
        result = IntegrationSyncResult(
            title='Empty',
            info_list=['Found 12 upstream items'],
        )
        self.assertFalse(result.has_changes)

    def test_placement_input_default_is_none(self):
        """A bare sync result has no placement_input — that's the
        signal the framework uses to decide whether to show the
        dispatcher modal."""
        result = IntegrationSyncResult(title='Empty')
        self.assertIsNone(result.placement_input)

    def test_placement_input_carries_groups_and_ungrouped(self):
        """placement_input wires sync results to the dispatcher: the
        synchronizer populates groups/ungrouped via
        group_entities_for_placement and stashes the input on the
        result."""
        entity = _FakeEntity('Camera 1')
        placement_input = EntityPlacementInput(
            groups=[EntityPlacementGroup(
                label='Monitors',
                items=[EntityPlacementItem(
                    key='zm:1', label='Camera 1', entity=entity,
                )],
            )],
        )
        result = IntegrationSyncResult(
            title='Sync',
            placement_input=placement_input,
        )
        self.assertIs(result.placement_input, placement_input)
        self.assertEqual(result.placement_input.groups[0].label, 'Monitors')
