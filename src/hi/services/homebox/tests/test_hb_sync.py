import logging
from contextlib import nullcontext
from unittest.mock import ANY, Mock, patch

from django.test import SimpleTestCase

from hi.apps.common.processing_result import ProcessingResult
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
                patch.object(synchronizer, '_sync_helper_entities') as sync_entities_mock:
            result = synchronizer._sync_helper()

        self.assertIsInstance(result, ProcessingResult)
        self.assertIn('Found 3 current HomeBox items.', result.message_list)
        sync_entities_mock.assert_called_once_with(
            item_list=manager.fetch_hb_items_from_api.return_value,
            result=result,
        )

    def test_sync_helper_entities_create_update_remove_entities(self):
        synchronizer = HomeBoxSynchronizer()
        result = ProcessingResult(title='HomeBox Import Result')

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

        with patch('hi.services.homebox.hb_sync.transaction.atomic', return_value=nullcontext()), \
                patch('hi.services.homebox.hb_sync.HbConverter.hb_item_to_integration_key', side_effect=key_from_item), \
                patch.object(synchronizer, '_get_existing_hb_entities', return_value={
                    existing_key: existing_entity,
                    stale_key: stale_entity,
                }), \
                patch.object(synchronizer, '_create_entity', return_value=created_entity) as create_entity_mock, \
                patch.object(synchronizer, '_update_entity') as update_entity_mock, \
                patch.object(synchronizer, '_remove_entity') as remove_entity_mock, \
                patch.object(synchronizer, '_sync_helper_entity_attributes') as sync_attrs_mock:
            synchronizer._sync_helper_entities(
                item_list=[item_new, item_existing, item_invalid],
                result=result,
            )

        create_entity_mock.assert_called_once_with(item=item_new, result=result)
        update_entity_mock.assert_called_once_with(entity=existing_entity, item=item_existing, result=result)
        remove_entity_mock.assert_called_once_with(entity=stale_entity, result=result)

        self.assertEqual(sync_attrs_mock.call_count, 2)
        self.assertEqual(sync_attrs_mock.call_args_list[0].kwargs['entity'], created_entity)
        self.assertEqual(sync_attrs_mock.call_args_list[0].kwargs['hb_item'], item_new)
        self.assertEqual(sync_attrs_mock.call_args_list[1].kwargs['entity'], existing_entity)
        self.assertEqual(sync_attrs_mock.call_args_list[1].kwargs['hb_item'], item_existing)

        self.assertIn('Found 2 existing HomeBox entities.', result.message_list)
        self.assertTrue(any('Ignoring HomeBox item due to missing/invalid id' in message
                            for message in result.error_list))

    def test_sync_helper_entity_attributes_create_update_remove_fields_and_attachments(self):
        synchronizer = HomeBoxSynchronizer()
        result = ProcessingResult(title='HomeBox Import Result')

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

        with patch('hi.services.homebox.hb_sync.transaction.atomic', return_value=nullcontext()), \
                patch('hi.services.homebox.hb_sync.HbConverter.hb_item_to_attribute_field_list',
                      return_value=[field_existing, field_new]), \
                patch('hi.services.homebox.hb_sync.HbConverter.hb_field_to_integration_key',
                      side_effect=lambda hb_field: field_key_by_id.get(hb_field.get('id'))), \
                patch('hi.services.homebox.hb_sync.HbConverter.hb_item_to_attachment_field_list',
                      return_value=[attachment_existing, attachment_new]), \
                patch('hi.services.homebox.hb_sync.HbConverter.hb_attachment_to_integration_key',
                      side_effect=lambda hb_attachment: attachment_key_by_id.get(hb_attachment.get('id'))), \
                patch.object(synchronizer, '_get_existing_hb_attributes', return_value={
                    field_existing_key: existing_field_attr,
                    attachment_existing_key: existing_attachment_attr,
                    stale_key: stale_attr,
                    foreign_key: foreign_attr,
                }), \
                patch.object(synchronizer, '_update_attribute') as update_attr_mock, \
                patch.object(synchronizer, '_create_attribute', return_value=created_field_attr) as create_attr_mock, \
                patch.object(synchronizer, '_update_attachment_attribute') as update_attachment_mock, \
                patch.object(synchronizer, '_create_attachment_attribute',
                             return_value=created_attachment_attr) as create_attachment_mock:
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
            order_id=0,
            message_list=ANY,
            updated_prefix='Attachment attribute updated',
        )
        create_attachment_mock.assert_called_once_with(
            entity=entity,
            hb_attachment=attachment_new,
            order_id=1,
        )

        stale_attr.delete.assert_called_once()
        foreign_attr.delete.assert_not_called()

        self.assertEqual(len(result.message_list), 1)
        self.assertIn('Updated HomeBox entity attributes', result.message_list[0])
        self.assertIn('Field attribute added: Field New', result.message_list[0])
        self.assertIn('Attachment attribute added: Attachment New', result.message_list[0])
        self.assertIn('Field attribute removed: Stale Field', result.message_list[0])
