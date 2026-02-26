from unittest.mock import Mock

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.services.homebox.hb_converter import HbConverter
from hi.services.homebox.hb_metadata import HbMetaData


class TestHbConverter(TestCase):

    def _mock_item(self, item_id='item-1', name='Item 1', description='desc', quantity=1):
        item = Mock()
        item.download_attachment.return_value = None
        item.id = item_id
        item.name = name
        item.description = description
        item.quantity = quantity
        item.location = {'id': 'loc-1', 'name': 'Garage'}
        item.labels = [{'id': 'lab-1', 'name': 'Tools'}]
        item.fields = []
        item.attachments = []
        return item

    def test_create_models_for_hb_item_creates_entity(self):
        item = self._mock_item(item_id='item-create', name='Drill')

        entity = HbConverter.create_models_for_hb_item(hb_item=item)

        self.assertIsInstance(entity, Entity)
        self.assertEqual(entity.integration_id, HbMetaData.integration_id)
        self.assertEqual(entity.integration_name, 'item-create')
        self.assertEqual(entity.name, 'Drill')
        self.assertEqual(entity.entity_type, EntityType.OTHER)
        self.assertFalse(entity.can_add_custom_attributes)
        self.assertEqual(entity.integration_payload.get('location_name'), 'Garage')
        self.assertEqual(entity.integration_payload.get('label_names'), ['Tools'])

    def test_update_models_for_hb_item_updates_name_type_and_payload(self):
        entity = Entity.objects.create(
            name='Old Name',
            entity_type_str=str(EntityType.SERVICE),
            can_user_delete=False,
            can_add_custom_attributes=True,
            integration_id=HbMetaData.integration_id,
            integration_name='item-update',
            integration_payload={'description': 'old', 'quantity': 1},
        )

        item = self._mock_item(item_id='item-update', name='New Name', description='new', quantity=3)

        messages = HbConverter.update_models_for_hb_item(entity=entity, hb_item=item)

        self.assertTrue(messages)
        entity.refresh_from_db()
        self.assertEqual(entity.name, 'New Name')
        self.assertEqual(entity.entity_type, EntityType.OTHER)
        self.assertFalse(entity.can_add_custom_attributes)
        self.assertEqual(entity.integration_payload.get('description'), 'new')
        self.assertEqual(entity.integration_payload.get('quantity'), 3)

    def test_hb_item_to_entity_name_fallback(self):
        item = self._mock_item(item_id='item-no-name', name='')
        self.assertEqual(HbConverter.hb_item_to_entity_name(hb_item=item), 'HomeBox Item item-no-name')

    def test_hb_item_to_attribute_field_list_contains_top_level_fields(self):
        item = self._mock_item(item_id='item-top-level')
        item.description = 'Portable drill'
        item.serial_number = 'SN-123'
        item.model_number = 'MD-456'
        item.manufacturer = 'ACME'

        hb_field_list = HbConverter.hb_item_to_attribute_field_list( hb_item = item )
        field_id_to_field = { field.get( 'id' ): field for field in hb_field_list }

        self.assertEqual( field_id_to_field['hb_item:description']['textValue'], 'Portable drill' )
        self.assertEqual( field_id_to_field['hb_item:serial_number']['textValue'], 'SN-123' )
        self.assertEqual( field_id_to_field['hb_item:model_number']['textValue'], 'MD-456' )
        self.assertEqual( field_id_to_field['hb_item:manufacturer']['textValue'], 'ACME' )

    def test_hb_item_attachment_maps_to_file_attribute_payload(self):
        item = self._mock_item(item_id='item-with-attachment')
        item.attachments = [{
            'id': 'att-1',
            'title': 'Manual',
            'mimeType': 'text/plain',
            'path': 'some/path',
        }]
        item.download_attachment.return_value = {
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
