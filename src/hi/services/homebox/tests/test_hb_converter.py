import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.services.homebox.hb_converter import HbConverter
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_models import HbItem


logging.disable(logging.CRITICAL)


class TestHbConverter(TestCase):

    def _mock_item(self, item_id='item-1', name='Item 1', description='desc', quantity=1):
        api_dict = {
            'id': item_id,
            'name': name,
            'description': description,
            'quantity': quantity,
            'location': {'id': 'loc-1', 'name': 'Garage'},
            'labels': [{'id': 'lab-1', 'name': 'Tools'}],
            'fields': [],
            'attachments': [],
        }

        client = Mock()
        client.download_attachment.return_value = None

        return HbItem(api_dict=api_dict, client=client)

    def test_create_models_for_hb_item_creates_entity(self):
        item = self._mock_item(item_id='item-create', name='Drill')

        entity = HbConverter.create_models_for_hb_item(hb_item=item)

        self.assertIsInstance(entity, Entity)
        self.assertEqual(entity.integration_id, HbMetaData.integration_id)
        self.assertEqual(entity.integration_name, 'item-create')
        self.assertEqual(entity.name, 'Drill')
        self.assertEqual(entity.entity_type, EntityType.OTHER)
        self.assertFalse(entity.can_add_custom_attributes)
        self.assertNotIn('description', entity.integration_payload)
        self.assertEqual(entity.integration_payload.get('location', {}).get('name'), 'Garage')
        self.assertEqual(entity.integration_payload.get('labels')[0].get('name'), 'Tools')

    def test_create_models_with_existing_entity_does_not_create_new_and_preserves_name(self):
        """Issue #281 reconnect contract: when an existing Entity is
        passed in, repopulate its integration-owned fields without
        creating a new row and without overwriting the (possibly
        user-edited) name."""
        existing = Entity.objects.create(
            name='User Renamed Item',
            entity_type_str=str(EntityType.SERVICE),
        )
        baseline_count = Entity.objects.count()
        item = self._mock_item(item_id='item-reconnect', name='Upstream Drill Name')

        returned = HbConverter.create_models_for_hb_item(
            hb_item=item,
            entity=existing,
        )

        self.assertEqual(Entity.objects.count(), baseline_count)
        self.assertEqual(returned.id, existing.id)
        existing.refresh_from_db()
        # Name preserved (NOT 'Upstream Drill Name').
        self.assertEqual(existing.name, 'User Renamed Item')
        # Integration-owned fields repopulated from upstream.
        self.assertEqual(existing.integration_id, HbMetaData.integration_id)
        self.assertEqual(existing.integration_name, 'item-reconnect')
        self.assertEqual(
            existing.integration_payload.get('location', {}).get('name'),
            'Garage',
        )

    def test_update_models_for_hb_item_updates_name_type_and_payload(self):
        entity = Entity.objects.create(
            name='Old Name',
            entity_type_str=str(EntityType.SERVICE),
            can_user_delete=False,
            can_add_custom_attributes=True,
            integration_id=HbMetaData.integration_id,
            integration_name='item-update',
            integration_payload={'quantity': 1},
        )

        item = self._mock_item(item_id='item-update', name='New Name', description='new', quantity=3)

        messages = HbConverter.update_models_for_hb_item(entity=entity, hb_item=item)

        self.assertTrue(messages)
        entity.refresh_from_db()
        self.assertEqual(entity.name, 'New Name')
        self.assertEqual(entity.entity_type, EntityType.OTHER)
        self.assertFalse(entity.can_add_custom_attributes)
        self.assertNotIn('description', entity.integration_payload)
        self.assertEqual(entity.integration_payload.get('quantity'), 3)

    def test_hb_item_to_attribute_field_list_contains_top_level_fields(self):
        item = self._mock_item(item_id='item-top-level')
        item.api_dict['description'] = 'Portable drill'
        item.api_dict['serialNumber'] = 'SN-123'
        item.api_dict['modelNumber'] = 'MD-456'
        item.api_dict['manufacturer'] = 'ACME'

        hb_field_list = HbConverter.hb_item_to_attribute_field_list( hb_item = item )
        field_id_to_field = { field.get( 'id' ): field for field in hb_field_list }

        self.assertEqual( field_id_to_field['hb_item:description']['textValue'], 'Portable drill' )
        self.assertEqual( field_id_to_field['hb_item:serial_number']['textValue'], 'SN-123' )
        self.assertEqual( field_id_to_field['hb_item:model_number']['textValue'], 'MD-456' )
        self.assertEqual( field_id_to_field['hb_item:manufacturer']['textValue'], 'ACME' )

    def test_hb_item_attachment_maps_to_file_attribute_payload(self):
        item = self._mock_item(item_id='item-with-attachment')
        item.api_dict['attachments'] = [{
            'id': 'att-1',
            'title': 'Manual',
            'mimeType': 'text/plain',
            'path': 'some/path',
        }]
        item.client.download_attachment.return_value = {
            'content': b'attachment-content',
            'mime_type': 'text/plain',
            'filename': 'Manual.txt',
            'source_url': 'https://example/download',
        }

        attachment_field_list = HbConverter.hb_item_to_attachment_field_list(hb_item=item)
        attachment_data = attachment_field_list[0]
        payload = HbConverter.hb_attachment_to_attribute_payload(hb_attachment=attachment_data, order_id=0)

        self.assertEqual(payload['value_type_str'], str(AttributeValueType.FILE))
        self.assertEqual(payload['name'], 'Manual')
        self.assertEqual(payload['file_mime_type'], 'text/plain')
        self.assertIn('file_value', payload)

    def test_create_and_update_file_attribute_from_attachment(self):
        item = self._mock_item(item_id='item-file-sync')
        entity = HbConverter.create_models_for_hb_item(hb_item=item)

        attachment = {
            'id': 'att-2',
            'title': 'Teste.txt',
            'mimeType': 'text/plain; charset=utf-8',
            'path': 'x/y/z',
        }
        attachment_data = {
            'id': 'attachment:att-2',
            'type': 'attachment',
            'name': 'Teste.txt',
            'textValue': 'Teste.txt',
            'mimeType': 'text/plain; charset=utf-8',
            'attachment': attachment,
            'downloaded_attachment': {
                'content': b'v1',
                'mime_type': 'text/plain; charset=utf-8',
                'filename': 'Teste.txt',
                'source_url': 'https://example/v1',
            }
        }

        created_attribute = HbConverter.create_attribute_from_hb_attachment(
            entity=entity,
            hb_attachment=attachment_data,
            order_id=0,
        )

        self.assertEqual(created_attribute.value_type_str, str(AttributeValueType.FILE))
        self.assertTrue(bool(created_attribute.file_value))

        # File should not be overwritten when already present.
        original_name = created_attribute.file_value.name
        attachment_data['downloaded_attachment'] = {
            'content': b'v2',
            'mime_type': 'text/plain; charset=utf-8',
            'filename': 'Teste-v2.txt',
            'source_url': 'https://example/v2',
        }
        was_changed = HbConverter.update_attribute_from_hb_attachment(
            attribute=created_attribute,
            hb_attachment=attachment_data,
            order_id=1,
        )

        self.assertTrue(was_changed)
        created_attribute.refresh_from_db()
        self.assertEqual(created_attribute.order_id, 1)
        self.assertEqual(created_attribute.file_value.name, original_name)



class TestHbConverterPayloadTimestampOmission(TestCase):
    """Regression coverage for the timestamp-omission contract on
    ``hb_item_to_entity_payload``.

    Timestamps are deliberately excluded from the payload — they
    are metadata about *when* a change happened, not *what*
    changed. Including them caused spurious 'updated' reports on
    every refresh because real HomeBox can tick ``updatedAt`` for
    housekeeping events the operator doesn't care about. These
    tests pin the contract so a future re-add (e.g., 'for
    completeness') silently re-introducing the bug fails loudly."""

    def _mock_item(self, **api_overrides):
        api_dict = {
            'id': 'item-1',
            'name': 'Item 1',
            'description': 'desc',
            'quantity': 1,
            'createdAt': '2026-01-01T00:00:00+00:00',
            'updatedAt': '2026-01-01T00:00:00+00:00',
            'location': {'id': 'loc-1', 'name': 'Garage'},
            'labels': [{'id': 'lab-1', 'name': 'Tools'}],
            'fields': [],
            'attachments': [],
        }
        api_dict.update(api_overrides)
        return HbItem(api_dict=api_dict, client=Mock())

    def test_payload_excludes_timestamp_keys(self):
        item = self._mock_item()
        payload = HbConverter.hb_item_to_entity_payload(hb_item=item)
        self.assertNotIn('created_at', payload)
        self.assertNotIn('updated_at', payload)

    def test_payloads_compare_equal_when_only_timestamps_differ(self):
        """The change-detection signal: two payloads identical
        except for timestamps must compare equal so a refresh
        against unchanged upstream content reports zero updates."""
        earlier = self._mock_item(
            createdAt='2026-01-01T00:00:00+00:00',
            updatedAt='2026-01-01T00:00:00+00:00',
        )
        later = self._mock_item(
            createdAt='2026-04-15T12:34:56+00:00',
            updatedAt='2026-05-04T08:00:00+00:00',
        )
        self.assertEqual(
            HbConverter.hb_item_to_entity_payload(hb_item=earlier),
            HbConverter.hb_item_to_entity_payload(hb_item=later),
        )
