"""
Tests for the IntegrationSyncResult shape.

The legacy sync-vocabulary fields (title, message_list, error_list,
footer_message) preserve the result-modal UX without depending on
ProcessingResult. The placement_input field is the optional bridge
to the dispatcher modal — populated when the sync produced new
entities to place, None otherwise.

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

        a.message_list.append('msg-a')
        a.error_list.append('err-a')

        self.assertEqual(b.message_list, [])
        self.assertEqual(b.error_list, [])

    def test_borrows_processing_result_shape(self):
        """title/message_list/error_list/footer_message preserve the
        legacy ProcessingResult UX so the result-modal template
        renders without changes."""
        result = IntegrationSyncResult(
            title='Sync Done',
            message_list=['imported 3'],
            error_list=['warning x'],
            footer_message='see settings',
        )
        self.assertEqual(result.title, 'Sync Done')
        self.assertEqual(result.message_list, ['imported 3'])
        self.assertEqual(result.error_list, ['warning x'])
        self.assertEqual(result.footer_message, 'see settings')

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
