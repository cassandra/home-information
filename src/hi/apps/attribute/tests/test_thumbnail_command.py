from io import BytesIO, StringIO

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.files.storage import default_storage

from PIL import Image

from hi.apps.entity.enums import EntityType
from hi.testing.base_test_case import BaseTestCase
from hi.apps.entity.models import Entity, EntityAttribute
from hi.apps.attribute.enums import AttributeType, AttributeValueType


class TestBackfillAttributeThumbnailsCommand(BaseTestCase):

    @staticmethod
    def _create_valid_png_image_bytes(size=(320, 240)):
        image = Image.new('RGB', size=size, color=(80, 120, 200))
        image_bytes = BytesIO()
        image.save(image_bytes, format='PNG')
        return image_bytes.getvalue()

    def _create_entity(self):
        return Entity.objects.create(
            name='Thumbnail Command Test Entity',
            integration_id='test.thumbnail.command.entity',
            integration_name='test_integration',
            entity_type_str=str(EntityType.LIGHT),
        )

    def test_command_generates_thumbnails_for_existing_file_attributes(self):
        with self.isolated_media_root():
            # Pass the file contents to ``file_value`` directly so
            # ``AttributeModel.save()`` owns filename generation —
            # otherwise the model's ``generate_unique_filename()``
            # timestamp suffix desyncs the attribute's stored path
            # from the on-disk path written by ``default_storage.save()``.
            entity = self._create_entity()
            attribute = EntityAttribute.objects.create(
                entity=entity,
                name='retroactive_image',
                value='Retroactive image',
                file_value=ContentFile(
                    self._create_valid_png_image_bytes(),
                    name='retroactive-image.png',
                ),
                file_mime_type='image/png',
                value_type_str=str(AttributeValueType.FILE),
                attribute_type_str=str(AttributeType.CUSTOM),
            )

            self.assertFalse(default_storage.exists(attribute.thumbnail_relative_path))

            stdout = StringIO()
            call_command('backfill_attribute_thumbnails', stdout=stdout)

            self.assertTrue(default_storage.exists(attribute.thumbnail_relative_path))
            self.assertIn('generated=1', stdout.getvalue())

    def test_command_dry_run_does_not_write_thumbnail_files(self):
        with self.isolated_media_root():
            entity = self._create_entity()
            attribute = EntityAttribute.objects.create(
                entity=entity,
                name='retroactive_image_dry_run',
                value='Retroactive image dry-run',
                file_value=ContentFile(
                    self._create_valid_png_image_bytes(),
                    name='retroactive-image-dry-run.png',
                ),
                file_mime_type='image/png',
                value_type_str=str(AttributeValueType.FILE),
                attribute_type_str=str(AttributeType.CUSTOM),
            )

            self.assertFalse(default_storage.exists(attribute.thumbnail_relative_path))

            stdout = StringIO()
            call_command('backfill_attribute_thumbnails', '--dry-run', stdout=stdout)

            self.assertFalse(default_storage.exists(attribute.thumbnail_relative_path))
            self.assertIn('would_generate=1', stdout.getvalue())