import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.integrations.enums import IntegrationCapability
from hi.services.homebox.hb_entity_factory import HbEntityFactory
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.hb_models import HbItem


logging.disable(logging.CRITICAL)


class TestHbEntityFactory(TestCase):

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

    def test_create_models_for_hb_item_creates_entity_connect_mode(self):
        item = self._mock_item(item_id='item-create', name='Drill')

        entity = HbEntityFactory.create_models_for_hb_item(
            hb_item=item,
            capability=IntegrationCapability.CONNECT,
        )

        self.assertIsInstance(entity, Entity)
        self.assertEqual(entity.integration_id, HbMetaData.integration_id)
        self.assertEqual(entity.integration_name, 'item-create')
        self.assertEqual(entity.name, 'Drill')
        # HbConverter's keyword heuristic resolves 'Drill' to TOOL.
        self.assertEqual(entity.entity_type, EntityType.TOOL)
        self.assertFalse(entity.allow_internal_attributes)
        self.assertTrue(entity.is_external)
        self.assertNotIn('description', entity.integration_payload)
        self.assertEqual(entity.integration_payload.get('location', {}).get('name'), 'Garage')
        self.assertEqual(entity.integration_payload.get('tags')[0].get('name'), 'Tools')

    def test_create_models_for_hb_item_creates_entity_import_mode(self):
        item = self._mock_item(item_id='item-import', name='Drill')

        entity = HbEntityFactory.create_models_for_hb_item(
            hb_item=item,
            capability=IntegrationCapability.IMPORT,
        )

        self.assertTrue(entity.allow_internal_attributes)
        self.assertTrue(entity.can_user_delete)
        self.assertTrue(entity.is_imported)

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

        returned = HbEntityFactory.create_models_for_hb_item(
            hb_item=item,
            capability=IntegrationCapability.CONNECT,
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
            allow_internal_attributes=True,
            integration_id=HbMetaData.integration_id,
            integration_name='item-update',
            integration_payload={'quantity': 1},
        )

        item = self._mock_item(item_id='item-update', name='New Name', description='new', quantity=3)

        messages = HbEntityFactory.update_models_for_hb_item(entity=entity, hb_item=item)

        self.assertTrue(messages)
        entity.refresh_from_db()
        self.assertEqual(entity.name, 'New Name')
        self.assertEqual(entity.entity_type, EntityType.OTHER)
        self.assertFalse(entity.allow_internal_attributes)
        self.assertNotIn('description', entity.integration_payload)
        self.assertEqual(entity.integration_payload.get('quantity'), 3)
