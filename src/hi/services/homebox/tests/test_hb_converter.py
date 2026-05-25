import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.services.homebox.hb_converter import HbConverter
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
            'tags': [{'id': 'lab-1', 'name': 'Tools'}],
            'fields': [],
            'attachments': [],
        }

        client = Mock()
        client.download_attachment.return_value = None

        return HbItem(api_dict=api_dict, client=client)

    def test_hb_item_to_attribute_field_list_contains_top_level_fields(self):
        item = self._mock_item(item_id='item-top-level')
        item.api_dict['description'] = 'Portable drill'
        item.api_dict['serialNumber'] = 'SN-123'
        item.api_dict['modelNumber'] = 'MD-456'
        item.api_dict['manufacturer'] = 'ACME'
        item.api_dict['assetId'] = 'AS-789'
        item.api_dict['purchaseFrom'] = 'Big Box Store'
        item.api_dict['purchaseTime'] = '2024-01-15'
        item.api_dict['warrantyDetails'] = '2 year limited'
        item.api_dict['warrantyExpires'] = '2026-01-15'
        item.api_dict['notes'] = 'Keep in workshop'

        hb_field_list = HbConverter.hb_item_to_attribute_field_list( hb_item = item )
        field_id_to_field = { field.get( 'id' ): field for field in hb_field_list }

        self.assertEqual( field_id_to_field['hb_item:description']['textValue'], 'Portable drill' )
        self.assertEqual( field_id_to_field['hb_item:serial_number']['textValue'], 'SN-123' )
        self.assertEqual( field_id_to_field['hb_item:model_number']['textValue'], 'MD-456' )
        self.assertEqual( field_id_to_field['hb_item:manufacturer']['textValue'], 'ACME' )
        self.assertEqual( field_id_to_field['hb_item:asset_id']['textValue'], 'AS-789' )
        self.assertEqual( field_id_to_field['hb_item:purchase_from']['textValue'], 'Big Box Store' )
        self.assertEqual( field_id_to_field['hb_item:purchase_time']['textValue'], '2024-01-15' )
        self.assertEqual( field_id_to_field['hb_item:warranty_details']['textValue'], '2 year limited' )
        self.assertEqual( field_id_to_field['hb_item:warranty_expires']['textValue'], '2026-01-15' )
        self.assertEqual( field_id_to_field['hb_item:notes']['textValue'], 'Keep in workshop' )

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
            'tags': [{'id': 'lab-1', 'name': 'Tools'}],
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
