import logging

from django.urls import reverse

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.models import EntityAttribute
from hi.testing.view_test_base import SyncViewTestCase

from .synthetic_data import EntityAttributeSyntheticData

logging.disable(logging.CRITICAL)


class TestEntityAttributeSoftDelete(SyncViewTestCase):

    def setUp(self):
        super().setUp()
        self.entity = EntityAttributeSyntheticData.create_test_entity(name='Restore Test Entity')
        self.attribute = EntityAttribute.objects.create(
            entity=self.entity,
            name='manual',
            value='content',
            attribute_type_str=str(AttributeType.CUSTOM),
            value_type_str=str(AttributeValueType.TEXT),
        )

    def test_restore_deleted_entity_attribute_not_deleted_returns_404(self):
        """Restoring an active attribute should fail deleted manager lookup."""
        url = reverse(
            'entity_attribute_restore_deleted_inline',
            kwargs={'entity_id': self.entity.id, 'attribute_id': self.attribute.id},
        )

        response = self.client.get(url)

        self.assertResponseStatusCode(response, 404)
        self.attribute.refresh_from_db()
        self.assertFalse(self.attribute.is_deleted)

    def test_soft_delete_and_restore_model_cycle(self):
        """Soft delete should hide from active manager and restore should bring it back."""
        self.attribute.delete()

        self.assertFalse(EntityAttribute.objects.filter(id=self.attribute.id).exists())
        self.assertTrue(EntityAttribute.deleted_objects.filter(id=self.attribute.id).exists())

        deleted_attr = EntityAttribute.deleted_objects.get(id=self.attribute.id)
        deleted_attr.restore_from_deleted()

        self.assertTrue(EntityAttribute.objects.filter(id=self.attribute.id).exists())
        self.assertFalse(EntityAttribute.deleted_objects.filter(id=self.attribute.id).exists())

    def test_restore_deleted_entity_attribute_inline_success(self):
        """Restore endpoint should recover a previously soft-deleted attribute."""
        self.attribute.delete()
        self.assertFalse(EntityAttribute.objects.filter(id=self.attribute.id).exists())

        url = reverse(
            'entity_attribute_restore_deleted_inline',
            kwargs={'entity_id': self.entity.id, 'attribute_id': self.attribute.id},
        )

        response = self.client.get(url)

        self.assertSuccessResponse(response)
        restored = EntityAttribute.objects.get(id=self.attribute.id)
        self.assertFalse(restored.is_deleted)

    def test_restore_deleted_entity_attribute_wrong_entity_returns_404(self):
        """Deleted attributes must only be restored through the owning entity endpoint."""
        other_entity = EntityAttributeSyntheticData.create_test_entity(name='Other Entity')
        self.attribute.delete()

        url = reverse(
            'entity_attribute_restore_deleted_inline',
            kwargs={'entity_id': other_entity.id, 'attribute_id': self.attribute.id},
        )

        response = self.client.get(url)

        self.assertResponseStatusCode(response, 404)
        self.assertTrue(EntityAttribute.deleted_objects.filter(id=self.attribute.id).exists())
