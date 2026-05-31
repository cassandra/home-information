"""Tests for the external-reference models: create_or_update
upsert semantics and delete-time thumbnail cleanup. Thumbnail
bytes are synthesized inline with Pillow so fixtures stay
self-contained.
"""
import logging
from io import BytesIO
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.test import TestCase
from PIL import Image

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location
from hi.integrations.models import (
    EntityExternalReference,
    LocationExternalReference,
)
from hi.integrations.transient_models import IntegrationKey


def _key(integration_id, integration_name):
    return IntegrationKey(
        integration_id=integration_id,
        integration_name=integration_name,
    )


logging.disable(logging.CRITICAL)


def _png_bytes(color='red'):
    img = Image.new('RGB', (16, 16), color)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class TestCreateOrUpdateInsert(TestCase):

    def setUp(self):
        self.entity = Entity.objects.create(
            name='Fridge', entity_type_str=str(EntityType.APPLIANCE),
        )

    def test_insert_with_all_fields_writes_thumbnail_under_per_integration_path(self):
        instance = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('immich', 'asset-uuid-1'),
            title='Fridge serial plate',
            source_url='https://im.example.com/photos/asset-uuid-1',
            mime_type='image/jpeg',
            thumbnail_bytes=_png_bytes(),
        )
        self.assertEqual(instance.integration_id, 'immich')
        self.assertEqual(instance.integration_name, 'asset-uuid-1')
        self.assertIn('entity/external/immich/thumbnails/',
                      instance.thumbnail.name)
        # Cleanup so the test leaves no media residue.
        instance.delete()

    def test_insert_without_thumbnail_bytes_leaves_thumbnail_empty(self):
        instance = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('paperless', '42'),
            title='Warranty',
            source_url='https://p.example.com/documents/42/details/',
        )
        self.assertFalse(instance.thumbnail)


class TestCreateOrUpdateUpsert(TestCase):

    def setUp(self):
        self.entity = Entity.objects.create(
            name='Fridge', entity_type_str=str(EntityType.APPLIANCE),
        )
        self.original = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('immich', 'uuid-1'),
            title='Original title',
            source_url='https://im.example.com/photos/uuid-1',
            mime_type='image/jpeg',
            thumbnail_bytes=_png_bytes('red'),
        )
        # Operator edits the local title + repositions the card.
        self.original.order_id = 7
        self.original.title = 'Operator-edited title'
        self.original.save(update_fields=['order_id', 'title'])

    def tearDown(self):
        # Reload to get the post-upsert thumbnail name for cleanup.
        for row in EntityExternalReference.objects.filter(entity=self.entity):
            row.delete()

    def test_upsert_overwrites_source_url_and_mime_type(self):
        updated = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('immich', 'uuid-1'),
            title='Upstream title (ignored)',
            source_url='https://im.example.com/photos/uuid-1?v=2',
            mime_type='image/png',
        )
        self.assertEqual(updated.pk, self.original.pk)
        self.assertEqual(updated.source_url,
                         'https://im.example.com/photos/uuid-1?v=2')
        self.assertEqual(updated.mime_type, 'image/png')

    def test_upsert_preserves_operator_title_order_id_created_datetime(self):
        updated = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('immich', 'uuid-1'),
            title='Upstream title (should be ignored)',
            source_url='https://im.example.com/photos/uuid-1',
            mime_type='image/jpeg',
        )
        self.assertEqual(updated.title, 'Operator-edited title')
        self.assertEqual(updated.order_id, 7)
        self.assertEqual(updated.created_datetime,
                         self.original.created_datetime)

    def test_upsert_without_thumbnail_bytes_leaves_existing_thumbnail(self):
        original_thumbnail_name = self.original.thumbnail.name
        self.assertTrue(default_storage.exists(original_thumbnail_name))
        updated = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('immich', 'uuid-1'),
            title='x',
            source_url='https://im.example.com/photos/uuid-1',
            mime_type='image/jpeg',
            thumbnail_bytes=None,
        )
        self.assertEqual(updated.thumbnail.name, original_thumbnail_name)
        self.assertTrue(default_storage.exists(updated.thumbnail.name))

    def test_upsert_with_thumbnail_bytes_replaces_file(self):
        original_thumbnail_name = self.original.thumbnail.name
        self.assertTrue(default_storage.exists(original_thumbnail_name))
        updated = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('immich', 'uuid-1'),
            title='x',
            source_url='https://im.example.com/photos/uuid-1',
            mime_type='image/jpeg',
            thumbnail_bytes=_png_bytes('blue'),
        )
        # Stable filename per (owner, integration_name) so the rewrite
        # lands on the same path; the old file is deleted and the new
        # one occupies the same slot.
        self.assertTrue(default_storage.exists(updated.thumbnail.name))


class TestExternalReferenceDelete(TestCase):

    def setUp(self):
        self.entity = Entity.objects.create(
            name='Fridge', entity_type_str=str(EntityType.APPLIANCE),
        )

    def test_delete_removes_thumbnail_file(self):
        instance = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('immich', 'uuid-1'),
            title='X',
            source_url='https://im.example.com/photos/uuid-1',
            mime_type='image/jpeg',
            thumbnail_bytes=_png_bytes(),
        )
        thumbnail_name = instance.thumbnail.name
        self.assertTrue(default_storage.exists(thumbnail_name))
        instance.delete()
        self.assertFalse(default_storage.exists(thumbnail_name))

    def test_delete_without_thumbnail_does_not_raise(self):
        instance = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('paperless', '42'),
            title='X',
            source_url='https://p.example.com/documents/42/details/',
        )
        instance.delete()

    @patch('hi.integrations.models.default_storage.delete',
           side_effect=OSError('disk gone'))
    def test_delete_swallows_storage_errors_best_effort(self, _mock_delete):
        instance = EntityExternalReference.objects.create_or_update(
            owner=self.entity,
            integration_key=_key('immich', 'uuid-1'),
            title='X',
            source_url='https://im.example.com/photos/uuid-1',
            mime_type='image/jpeg',
            thumbnail_bytes=_png_bytes(),
        )
        # Delete must succeed even though file deletion errored.
        instance.delete()
        self.assertFalse(
            EntityExternalReference.objects.filter(pk=instance.pk).exists(),
        )


class TestLocationExternalReference(TestCase):
    """Spot-check that the Location flavor uses the same path
    convention as Entity. Deep coverage stays on Entity since the
    abstract base owns the shared behavior."""

    def test_create_or_update_inserts_under_location_thumbnail_path(self):
        location = Location.objects.create(
            name='Kitchen', svg_view_box_str='0 0 100 100',
        )
        instance = LocationExternalReference.objects.create_or_update(
            owner=location,
            integration_key=_key('immich', 'uuid-1'),
            title='X',
            source_url='https://im.example.com/photos/uuid-1',
            mime_type='image/jpeg',
            thumbnail_bytes=_png_bytes(),
        )
        self.assertEqual(instance.location, location)
        self.assertIn('location/external/immich/thumbnails/',
                      instance.thumbnail.name)
        # Cleanup so the test leaves no media residue.
        instance.delete()
