from unittest.mock import Mock

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.services.homebox.hb_converter import HbConverter
from hi.services.homebox.hb_metadata import HbMetaData


class TestHbConverter(TestCase):

    def _mock_item(self, item_id='item-1', name='Item 1', description='desc', quantity=1):
        item = Mock()
        item.id = item_id
        item.name = name
        item.description = description
        item.quantity = quantity
        item.location = {'id': 'loc-1', 'name': 'Garage'}
        item.labels = [{'id': 'lab-1', 'name': 'Tools'}]
        return item

    def test_create_models_for_hb_item_creates_entity(self):
        item = self._mock_item(item_id='item-create', name='Drill')

        entity = HbConverter.create_models_for_hb_item(hb_item=item)

        self.assertIsInstance(entity, Entity)
        self.assertEqual(entity.integration_id, HbMetaData.integration_id)
        self.assertEqual(entity.integration_name, 'item-create')
        self.assertEqual(entity.name, 'Drill')
        self.assertEqual(entity.entity_type, EntityType.OTHER)
        self.assertEqual(entity.integration_payload.get('location_name'), 'Garage')
        self.assertEqual(entity.integration_payload.get('label_names'), ['Tools'])

    def test_update_models_for_hb_item_updates_name_type_and_payload(self):
        entity = Entity.objects.create(
            name='Old Name',
            entity_type_str=str(EntityType.SERVICE),
            can_user_delete=False,
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
        self.assertEqual(entity.integration_payload.get('description'), 'new')
        self.assertEqual(entity.integration_payload.get('quantity'), 3)

    def test_hb_item_to_entity_name_fallback(self):
        item = self._mock_item(item_id='item-no-name', name='')
        self.assertEqual(HbConverter.hb_item_to_entity_name(hb_item=item), 'HomeBox Item item-no-name')
