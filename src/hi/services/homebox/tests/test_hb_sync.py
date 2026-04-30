import logging
from contextlib import ExitStack, nullcontext
from unittest.mock import ANY, Mock, patch

from django.test import SimpleTestCase

from hi.integrations.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_sync import HomeBoxSynchronizer


logging.disable(logging.CRITICAL)


class TestHomeBoxSynchronizer(SimpleTestCase):

    def _key(self, name: str) -> IntegrationKey:
        return IntegrationKey(
            integration_id=HbMetaData.integration_id,
            integration_name=name,
        )

    def test_sync_helper_uses_mocked_api_response_and_delegates_entity_sync(self):
        synchronizer = HomeBoxSynchronizer()
        manager = Mock()
        manager.hb_client = object()
        manager.fetch_hb_items_from_api.return_value = [Mock(), Mock(), Mock()]

        with patch.object(synchronizer, 'hb_manager', return_value=manager), \
                patch.object(synchronizer, '_sync_helper_entities', return_value=[]) as sync_entities_mock:
            result = synchronizer._sync_impl(is_initial_import=True)

        self.assertIsInstance(result, IntegrationSyncResult)
        self.assertIn('Found 3 current HomeBox items.', result.info_list)
        sync_entities_mock.assert_called_once_with(
            item_list=manager.fetch_hb_items_from_api.return_value,
            result=result,
        )

    def test_sync_helper_entities_create_update_remove_entities(self):
        synchronizer = HomeBoxSynchronizer()
        result = IntegrationSyncResult(title='HomeBox Import Result')

        item_new = Mock(name='item_new')
        item_existing = Mock(name='item_existing')
        item_invalid = Mock(name='item_invalid')

        new_key = self._key('item-new')
        existing_key = self._key('item-existing')
        stale_key = self._key('item-stale')

        existing_entity = Mock(name='existing_entity')
        stale_entity = Mock(name='stale_entity')
        created_entity = Mock(name='created_entity')

        def key_from_item(hb_item):
            if hb_item is item_new:
                return new_key
            if hb_item is item_existing:
                return existing_key
            raise ValueError('missing id')

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    'hi.services.homebox.hb_sync.transaction.atomic',
                    return_value=nullcontext(),
                )
            )
            stack.enter_context(
                patch(
                    'hi.services.homebox.hb_sync.HbConverter.hb_item_to_integration_key',
                    side_effect=key_from_item,
                )
            )
            stack.enter_context(
                patch.object(
                    synchronizer,
                    '_get_existing_hb_entities',
                    return_value={
                        existing_key: existing_entity,
                        stale_key: stale_entity,
                    },
                )
            )
            create_entity_mock = stack.enter_context(
                patch.object(
                    synchronizer,
                    '_create_entity',
                    return_value=created_entity,
                )
            )
            update_entity_mock = stack.enter_context(
                patch.object(synchronizer, '_update_entity')
            )
            remove_entity_mock = stack.enter_context(
                patch.object(synchronizer, '_remove_entity')
            )
            sync_attrs_mock = stack.enter_context(
                patch.object(synchronizer, '_sync_helper_entity_attributes')
            )

            synchronizer._sync_helper_entities(
                item_list=[item_new, item_existing, item_invalid],
                result=result,
            )

        create_entity_mock.assert_called_once_with(item=item_new, result=result)
        update_entity_mock.assert_called_once_with(
            entity=existing_entity,
            item=item_existing,
            result=result,
        )
        remove_entity_mock.assert_called_once_with(
            entity=stale_entity,
            result=result,
        )

        self.assertEqual(sync_attrs_mock.call_count, 2)
        self.assertEqual(
            sync_attrs_mock.call_args_list[0].kwargs['entity'],
            created_entity,
        )
        self.assertEqual(
            sync_attrs_mock.call_args_list[0].kwargs['hb_item'],
            item_new,
        )
        self.assertEqual(
            sync_attrs_mock.call_args_list[1].kwargs['entity'],
            existing_entity,
        )
        self.assertEqual(
            sync_attrs_mock.call_args_list[1].kwargs['hb_item'],
            item_existing,
        )

        self.assertIn('Found 2 existing HomeBox entities.', result.info_list)
        self.assertTrue(any('Ignoring HomeBox item due to missing/invalid id' in message
                            for message in result.error_list))

    def test_sync_helper_entity_attributes_create_update_remove_fields_and_attachments(self):
        synchronizer = HomeBoxSynchronizer()
        result = IntegrationSyncResult(title='HomeBox Import Result')

        entity = Mock(name='entity')
        entity.id = 10

        field_existing = {'id': 'field-existing', 'name': 'Field Existing'}
        field_new = {'id': 'field-new', 'name': 'Field New'}
        attachment_existing = {'id': 'attachment-existing', 'name': 'Attachment Existing'}
        attachment_new = {'id': 'attachment-new', 'name': 'Attachment New'}

        field_existing_key = self._key('field:field-existing')
        field_new_key = self._key('field:field-new')
        attachment_existing_key = self._key('field:attachment-existing')
        attachment_new_key = self._key('field:attachment-new')
        stale_key = self._key('field:stale-field')
        foreign_key = self._key('field:foreign-field')

        existing_field_attr = Mock(name='existing_field_attr')
        existing_field_attr.entity_id = entity.id
        existing_attachment_attr = Mock(name='existing_attachment_attr')
        existing_attachment_attr.entity_id = entity.id
        stale_attr = Mock(name='stale_attr')
        stale_attr.entity_id = entity.id
        stale_attr.name = 'Stale Field'
        foreign_attr = Mock(name='foreign_attr')
        foreign_attr.entity_id = entity.id + 1

        created_field_attr = Mock(name='created_field_attr')
        created_field_attr.name = 'Field New'
        created_attachment_attr = Mock(name='created_attachment_attr')
        created_attachment_attr.name = 'Attachment New'

        field_key_by_id = {
            'field-existing': field_existing_key,
            'field-new': field_new_key,
        }
        attachment_key_by_id = {
            'attachment-existing': attachment_existing_key,
            'attachment-new': attachment_new_key,
        }

        def field_key_from_field(hb_field):
            return field_key_by_id.get(hb_field.get('id'))

        def attachment_key_from_attachment(hb_attachment):
            return attachment_key_by_id.get(hb_attachment.get('id'))

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    'hi.services.homebox.hb_sync.transaction.atomic',
                    return_value=nullcontext(),
                )
            )
            stack.enter_context(
                patch(
                    'hi.services.homebox.hb_sync.HbConverter.hb_item_to_attribute_field_list',
                    return_value=[field_existing, field_new],
                )
            )
            stack.enter_context(
                patch(
                    'hi.services.homebox.hb_sync.HbConverter.hb_field_to_integration_key',
                    side_effect=field_key_from_field,
                )
            )
            stack.enter_context(
                patch(
                    'hi.services.homebox.hb_sync.HbConverter.hb_item_to_attachment_field_list',
                    return_value=[attachment_existing, attachment_new],
                )
            )
            stack.enter_context(
                patch(
                    'hi.services.homebox.hb_sync.HbConverter.hb_attachment_to_integration_key',
                    side_effect=attachment_key_from_attachment,
                )
            )
            stack.enter_context(
                patch.object(
                    synchronizer,
                    '_get_existing_hb_attributes',
                    return_value={
                        field_existing_key: existing_field_attr,
                        attachment_existing_key: existing_attachment_attr,
                        stale_key: stale_attr,
                        foreign_key: foreign_attr,
                    },
                )
            )
            update_attr_mock = stack.enter_context(
                patch.object(synchronizer, '_update_attribute')
            )
            create_attr_mock = stack.enter_context(
                patch.object(
                    synchronizer,
                    '_create_attribute',
                    return_value=created_field_attr,
                )
            )
            update_attachment_mock = stack.enter_context(
                patch.object(synchronizer, '_update_attachment_attribute')
            )
            create_attachment_mock = stack.enter_context(
                patch.object(
                    synchronizer,
                    '_create_attachment_attribute',
                    return_value=created_attachment_attr,
                )
            )

            synchronizer._sync_helper_entity_attributes(
                entity=entity,
                hb_item=Mock(),
                result=result,
            )

        update_attr_mock.assert_called_once_with(
            attribute=existing_field_attr,
            hb_field=field_existing,
            order_id=0,
            message_list=ANY,
            updated_prefix='Field attribute updated',
        )
        create_attr_mock.assert_called_once_with(
            entity=entity,
            hb_field=field_new,
            order_id=1,
        )

        update_attachment_mock.assert_called_once_with(
            attribute=existing_attachment_attr,
            hb_attachment=attachment_existing,
            order_id=2,
            message_list=ANY,
            updated_prefix='Attachment attribute updated',
        )
        create_attachment_mock.assert_called_once_with(
            entity=entity,
            hb_attachment=attachment_new,
            order_id=3,
        )

        stale_attr.delete.assert_called_once()
        foreign_attr.delete.assert_not_called()

        # Per-attribute change detail is no longer surfaced in the
        # sync result (counts at the entity level capture the
        # operator-relevant signal). The persistence behavior above
        # — created/updated/deleted attribute records — remains the
        # contract this test pins.
        self.assertEqual(result.info_list, [])


class TestHomeBoxSynchronizerSyncResultGrouping(SimpleTestCase):
    """Phase 2 grouping behavior: HomeBox has no domain notion of
    grouping, so every imported item lands in `ungrouped_items`.
    `groups` stays empty. The framework's dispatcher modal decides
    how to surface ungrouped items at render time."""

    def test_sync_impl_populates_ungrouped_items_only(self):
        synchronizer = HomeBoxSynchronizer()
        manager = Mock()
        manager.hb_client = object()
        manager.fetch_hb_items_from_api.return_value = [Mock(), Mock()]

        entity_a = Mock()
        entity_a.name = 'Cordless Drill'
        entity_a.integration_key = IntegrationKey(
            integration_id=HbMetaData.integration_id,
            integration_name='item.42',
        )
        entity_a.id = 0
        entity_b = Mock()
        entity_b.name = 'Stud Finder'
        entity_b.integration_key = IntegrationKey(
            integration_id=HbMetaData.integration_id,
            integration_name='item.43',
        )
        entity_b.id = 0

        with patch.object(synchronizer, 'hb_manager', return_value=manager), \
             patch.object(synchronizer, '_sync_helper_entities',
                          return_value=[entity_a, entity_b]):
            result = synchronizer._sync_impl(is_initial_import=True)

        self.assertIsNotNone(result.placement_input)
        self.assertEqual(result.placement_input.groups, [])
        self.assertEqual(len(result.placement_input.ungrouped_items), 2)
        labels = [item.label for item in result.placement_input.ungrouped_items]
        self.assertEqual(labels, ['Cordless Drill', 'Stud Finder'])
        keys = [item.key for item in result.placement_input.ungrouped_items]
        self.assertEqual(
            keys,
            [
                f'{HbMetaData.integration_id}:item.42',
                f'{HbMetaData.integration_id}:item.43',
            ],
        )

    def test_sync_impl_emits_empty_when_no_items_imported(self):
        synchronizer = HomeBoxSynchronizer()
        manager = Mock()
        manager.hb_client = object()
        manager.fetch_hb_items_from_api.return_value = []

        with patch.object(synchronizer, 'hb_manager', return_value=manager), \
                patch.object(synchronizer, '_sync_helper_entities', return_value=[]):
            result = synchronizer._sync_impl(is_initial_import=True)

        # No newly-created entities → placement_input is None.
        self.assertIsNone(result.placement_input)
