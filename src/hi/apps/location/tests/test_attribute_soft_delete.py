import logging

from django.urls import reverse

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.location.models import Location, LocationAttribute
from hi.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestLocationAttributeSoftDelete(SyncViewTestCase):

    def setUp(self):
        super().setUp()
        self.location = Location.objects.create(
            name='Restore Test Location',
            svg_fragment_filename='restore-test.svg',
            svg_view_box_str='0 0 100 100',
        )
        self.attribute = LocationAttribute.objects.create(
            location=self.location,
            name='note',
            value='content',
            attribute_type_str=str(AttributeType.CUSTOM),
            value_type_str=str(AttributeValueType.TEXT),
        )

    def test_restore_deleted_location_attribute_inline(self):
        self.attribute.delete()
        self.assertFalse(LocationAttribute.objects.filter(id=self.attribute.id).exists())

        url = reverse(
            'location_attribute_restore_deleted_inline',
            kwargs={'location_id': self.location.id, 'attribute_id': self.attribute.id},
        )
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        restored = LocationAttribute.objects.get(id=self.attribute.id)
        self.assertFalse(restored.is_deleted)

    def test_soft_delete_and_restore_model_cycle(self):
        """Soft delete should hide from active manager and restore should bring it back."""
        self.attribute.delete()

        self.assertFalse(LocationAttribute.objects.filter(id=self.attribute.id).exists())
        self.assertTrue(LocationAttribute.deleted_objects.filter(id=self.attribute.id).exists())

        deleted_attr = LocationAttribute.deleted_objects.get(id=self.attribute.id)
        deleted_attr.restore_from_deleted()

        self.assertTrue(LocationAttribute.objects.filter(id=self.attribute.id).exists())
        self.assertFalse(LocationAttribute.deleted_objects.filter(id=self.attribute.id).exists())

    def test_restore_deleted_location_attribute_not_deleted_returns_404(self):
        """Restoring an active attribute should return not found for deleted manager lookup."""
        url = reverse(
            'location_attribute_restore_deleted_inline',
            kwargs={'location_id': self.location.id, 'attribute_id': self.attribute.id},
        )

        response = self.client.get(url)

        self.assertResponseStatusCode(response, 404)
        self.attribute.refresh_from_db()
        self.assertFalse(self.attribute.is_deleted)

    def test_restore_deleted_location_attribute_wrong_location_returns_404(self):
        """Deleted attributes must only be restored through the owning location endpoint."""
        other_location = Location.objects.create(
            name='Other Location',
            svg_fragment_filename='other-location.svg',
            svg_view_box_str='0 0 100 100',
        )
        self.attribute.delete()

        url = reverse(
            'location_attribute_restore_deleted_inline',
            kwargs={'location_id': other_location.id, 'attribute_id': self.attribute.id},
        )

        response = self.client.get(url)

        self.assertResponseStatusCode(response, 404)
        self.assertTrue(LocationAttribute.deleted_objects.filter(id=self.attribute.id).exists())
