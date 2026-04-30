"""
Tests for the IntegrationSyncResult / SyncResultItem / SyncResultItemGroup
data shapes returned by integration synchronizers.

Pins the contract Phase 3's dispatcher modal will read against:

  * groups and ungrouped_items default to empty lists (independent
    instances per result, no shared mutable state).
  * Synchronizers populate exactly one of (groups, ungrouped_items)
    per item; the framework relies on that invariant when rendering
    grouped vs. ungrouped UI.
  * ProcessingResult-like fields (title, message_list, error_list,
    footer_message) preserve the legacy result-modal UX without
    depending on ProcessingResult.
"""
import logging

from django.test import SimpleTestCase

from hi.integrations.sync_result import (
    IntegrationSyncResult,
    SyncResultItem,
    SyncResultItemGroup,
)

logging.disable(logging.CRITICAL)


class _FakeEntity:
    """Stand-in for Entity used in shape tests; we never persist."""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<_FakeEntity {self.name}>'


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
        a.groups.append(SyncResultItemGroup(label='Group A'))
        a.ungrouped_items.append(
            SyncResultItem(key='k', label='l', entity=_FakeEntity('e'))
        )

        self.assertEqual(b.message_list, [])
        self.assertEqual(b.error_list, [])
        self.assertEqual(b.groups, [])
        self.assertEqual(b.ungrouped_items, [])

    def test_borrows_processing_result_shape(self):
        """title/message_list/error_list/footer_message preserve the
        legacy ProcessingResult UX so the result-modal template
        renders without changes during Phase 2."""
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

    def test_group_carries_items_with_entities(self):
        entity = _FakeEntity('Camera 1')
        item = SyncResultItem(key='zm:1', label='Camera 1', entity=entity)
        group = SyncResultItemGroup(label='Monitors', items=[item])
        self.assertEqual(group.label, 'Monitors')
        self.assertEqual(group.items, [item])
        # Item retains its referenced Entity so the dispatcher can
        # invoke placement against it without an extra DB lookup.
        self.assertIs(group.items[0].entity, entity)
