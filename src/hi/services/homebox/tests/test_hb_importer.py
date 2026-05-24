import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.services.homebox.connector.hb_entity_factory import HbEntityFactory
from hi.services.homebox.importer.hb_importer import HbImporter
from hi.services.homebox.shared.hb_models import HbItem


logging.disable(logging.CRITICAL)


class TestHbImporter(TestCase):

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

    def test_create_and_update_file_attribute_from_attachment(self):
        item = self._mock_item(item_id='item-file-sync')
        entity = HbEntityFactory.create_models_for_hb_item(hb_item=item)

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

        created_attribute = HbImporter.create_attribute_from_hb_attachment(
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
        was_changed = HbImporter.update_attribute_from_hb_attachment(
            attribute=created_attribute,
            hb_attachment=attachment_data,
            order_id=1,
        )

        self.assertTrue(was_changed)
        created_attribute.refresh_from_db()
        self.assertEqual(created_attribute.order_id, 1)
        self.assertEqual(created_attribute.file_value.name, original_name)
