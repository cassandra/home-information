import logging

from django.urls import reverse

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.location.models import Location, LocationAttribute
from hi.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestDeletedAttributeRestore(SyncViewTestCase):

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
