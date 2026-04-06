import importlib
import json
import logging
from io import BytesIO
from unittest.mock import patch, call

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from PIL import Image

from hi.apps.attribute.models import AttributeModel
from hi.apps.attribute.enums import AttributeValueType, AttributeType
from hi.integrations.transient_models import IntegrationKey
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class ConcreteAttributeModel(AttributeModel):
    """Concrete implementation for testing the abstract AttributeModel."""
    
    def get_upload_to(self):
        return 'test_attributes/'


class TestAttributeModel(BaseTestCase):

    @staticmethod
    def _create_valid_png_image_bytes(size=(128, 96)):
        image = Image.new('RGB', size=size, color=(24, 120, 220))
        image_bytes = BytesIO()
        image.save(image_bytes, format='PNG')
        return image_bytes.getvalue()

    @staticmethod
    def _create_valid_pdf_bytes():
        try:
            fitz = importlib.import_module('fitz')
        except Exception:
            return None

        pdf_document = fitz.open()
        first_page = pdf_document.new_page(width=360, height=220)
        first_page.insert_text((36, 72), 'HI PDF Preview Test')
        pdf_bytes = pdf_document.tobytes()
        pdf_document.close()
        return pdf_bytes

    def test_attribute_model_enum_property_conversions(self):
        """Test enum property conversions - custom business logic."""
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        
        # Test getter converts string to enum
        self.assertEqual(attr.value_type, AttributeValueType.FILE)
        self.assertEqual(attr.attribute_type, AttributeType.CUSTOM)
        
        # Test setter converts enum to string
        attr.value_type = AttributeValueType.BOOLEAN
        attr.attribute_type = AttributeType.PREDEFINED
        self.assertEqual(attr.value_type_str, 'boolean')
        self.assertEqual(attr.attribute_type_str, 'predefined')
        return

    def test_attribute_model_integration_key_parsing(self):
        """Test integration key parsing and serialization - complex object handling."""
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='TEXT',
            attribute_type_str='CUSTOM'
        )
        
        # Test with no integration key
        self.assertIsNone(attr.integration_key)
        
        # Test setting integration key
        test_key = IntegrationKey(integration_id='test_id', integration_name='test_integration')
        attr.integration_key = test_key
        self.assertEqual(attr.integration_key_str, str(test_key))
        
        # Test getting parsed integration key
        parsed_key = attr.integration_key
        self.assertEqual(parsed_key.integration_id, 'test_id')
        self.assertEqual(parsed_key.integration_name, 'test_integration')
        
        # Test clearing integration key
        attr.integration_key = None
        self.assertIsNone(attr.integration_key_str)
        self.assertIsNone(attr.integration_key)
        return

    def test_attribute_model_choices_json_parsing(self):
        """Test choices JSON parsing - complex data processing logic."""
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='ENUM',
            attribute_type_str='CUSTOM'
        )
        
        # Test with dictionary format
        attr.value_range_str = json.dumps({'key1': 'Label 1', 'key2': 'Label 2'})
        choices = attr.choices()
        expected = [('key1', 'Label 1'), ('key2', 'Label 2')]
        self.assertEqual(choices, expected)
        
        # Test with list format
        attr.value_range_str = json.dumps(['option1', 'option2', 'option3'])
        choices = attr.choices()
        expected = [('option1', 'option1'), ('option2', 'option2'), ('option3', 'option3')]
        self.assertEqual(choices, expected)
        
        # Test with invalid JSON
        attr.value_range_str = 'invalid json {'
        choices = attr.choices()
        self.assertEqual(choices, {})  # Should return empty dict on parse error
        
        # Test with empty value_range_str
        attr.value_range_str = None
        choices = attr.choices()
        self.assertEqual(choices, [])
        return

    @patch('hi.apps.attribute.models.PredefinedValueRanges.get_choices')
    def test_attribute_model_choices_predefined_lookup(self, mock_get_choices):
        """Test choices predefined value range lookup - external integration logic."""
        mock_get_choices.return_value = [('pred1', 'Predefined 1'), ('pred2', 'Predefined 2')]
        
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='ENUM',
            attribute_type_str='PREDEFINED',
            value_range_str='hi.test.choices'
        )
        
        choices = attr.choices()
        
        # Should use predefined choices, not parse JSON
        mock_get_choices.assert_called_once_with('hi.test.choices')
        self.assertEqual(choices, [('pred1', 'Predefined 1'), ('pred2', 'Predefined 2')])
        return

    @patch('hi.apps.attribute.models.generate_unique_filename')
    def test_attribute_model_file_save_logic(self, mock_generate_unique_filename):
        """Test file save logic with unique filename generation - complex file handling."""
        mock_generate_unique_filename.return_value = 'unique_test_file.txt'
        
        # Use isolated MEDIA_ROOT to prevent production pollution
        with self.isolated_media_root():
            # Create test file using base test utility
            test_file = self.create_test_text_file('test_file.txt', 'test content')
            
            attr = ConcreteAttributeModel(
                name='test_attr',
                value_type_str='FILE',
                attribute_type_str='CUSTOM'
            )
            attr.file_value = test_file
            # Ensure pk is None for new object behavior
            attr.pk = None
            
            # Mock the super().save() call to avoid database issues
            with patch('django.db.models.Model.save'):
                # Simulate calling save
                attr.save()
                
                # Should set upload_to and generate unique filename for new objects
                mock_generate_unique_filename.assert_called_once_with('test_file.txt')
                self.assertEqual(attr.value, 'test_file.txt')  # Value set to original filename
                self.assertEqual(attr.file_value.name, 'unique_test_file.txt')  # Name updated to unique
                self.assertEqual(attr.file_value.field.upload_to, 'test_attributes/')
        return

    def test_thumbnail_relative_path_for_supported_image_file(self):
        """Test deterministic thumbnail path generation for supported image files."""
        attr = ConcreteAttributeModel(
            name='photo',
            value_type_str='FILE',
            attribute_type_str='CUSTOM',
            file_mime_type='image/jpeg'
        )
        attr.file_value = 'entity/attributes/front_door.jpg'

        self.assertTrue(attr.supports_thumbnail_generation)
        self.assertEqual(
            attr.thumbnail_relative_path,
            'entity/attributes/thumbnails/front_door.thumb.png'
        )
        return

    def test_thumbnail_relative_path_none_for_unsupported_file_type(self):
        """Test unsupported files do not produce thumbnail paths."""
        attr = ConcreteAttributeModel(
            name='document',
            value_type_str='FILE',
            attribute_type_str='CUSTOM',
            file_mime_type='text/plain'
        )
        attr.file_value = 'entity/attributes/manual.txt'

        self.assertFalse(attr.supports_thumbnail_generation)
        self.assertIsNone(attr.thumbnail_relative_path)
        return

    def test_thumbnail_relative_path_for_supported_pdf_file(self):
        """Test deterministic thumbnail path generation for supported PDF files."""
        attr = ConcreteAttributeModel(
            name='manual',
            value_type_str='FILE',
            attribute_type_str='CUSTOM',
            file_mime_type='application/pdf'
        )
        attr.file_value = 'entity/attributes/manual.pdf'

        self.assertTrue(attr.supports_thumbnail_generation)
        self.assertEqual(
            attr.thumbnail_relative_path,
            'entity/attributes/thumbnails/manual.thumb.png'
        )
        return

    def test_generate_thumbnail_best_effort_success(self):
        """Test thumbnail generation creates a derived file for valid image content."""
        with self.isolated_media_root():
            source_path = 'test_attributes/camera_snapshot.png'
            default_storage.save(
                source_path,
                ContentFile(self._create_valid_png_image_bytes(size=(900, 600)))
            )

            attr = ConcreteAttributeModel(
                name='camera_snapshot',
                value_type_str='FILE',
                attribute_type_str='CUSTOM',
                file_mime_type='image/png'
            )
            attr.file_value = source_path

            generated = attr.generate_thumbnail_best_effort()

            self.assertTrue(generated)
            self.assertTrue(default_storage.exists(attr.thumbnail_relative_path))
            self.assertTrue(attr.has_thumbnail)
            self.assertIsNotNone(attr.thumbnail_url)
            self.assertIn('test_attributes/thumbnails/camera_snapshot.thumb.png', attr.thumbnail_url)
        return

    def test_generate_thumbnail_best_effort_invalid_image_content(self):
        """Test thumbnail generation failure is graceful for bad image bytes."""
        with self.isolated_media_root():
            source_path = 'test_attributes/not_really_an_image.jpg'
            default_storage.save(source_path, ContentFile(b'plain text bytes, not an image'))

            attr = ConcreteAttributeModel(
                name='broken_image',
                value_type_str='FILE',
                attribute_type_str='CUSTOM',
                file_mime_type='image/jpeg'
            )
            attr.file_value = source_path

            generated = attr.generate_thumbnail_best_effort()

            self.assertFalse(generated)
            self.assertFalse(attr.has_thumbnail)
            self.assertIsNone(attr.thumbnail_url)
        return

    def test_generate_thumbnail_best_effort_pdf_success(self):
        """Test thumbnail generation from first page of a PDF file."""
        pdf_bytes = self._create_valid_pdf_bytes()
        if not pdf_bytes:
            self.skipTest('PyMuPDF not installed in this environment')

        with self.isolated_media_root():
            source_path = 'test_attributes/manual.pdf'
            default_storage.save(source_path, ContentFile(pdf_bytes))

            attr = ConcreteAttributeModel(
                name='manual',
                value_type_str='FILE',
                attribute_type_str='CUSTOM',
                file_mime_type='application/pdf'
            )
            attr.file_value = source_path

            generated = attr.generate_thumbnail_best_effort()

            self.assertTrue(generated)
            self.assertTrue(default_storage.exists(attr.thumbnail_relative_path))
            self.assertTrue(attr.has_thumbnail)
            self.assertIsNotNone(attr.thumbnail_url)
        return

    @patch('hi.apps.attribute.models.default_storage')
    def test_attribute_model_file_delete_also_deletes_thumbnail(self, mock_storage):
        """Test file deletion removes generated thumbnail when present."""
        mock_storage.exists.side_effect = [True, True]

        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM',
            file_mime_type='image/jpeg'
        )
        attr.file_value = 'test_image.jpg'
        attr.pk = 1

        with patch('django.db.models.Model.delete'):
            attr.delete()

        self.assertEqual(
            mock_storage.delete.call_args_list,
            [call('test_image.jpg'), call('thumbnails/test_image.thumb.png')]
        )
        return

    @patch('hi.apps.attribute.models.default_storage')
    def test_attribute_model_file_deletion_missing_file(self, mock_storage):
        """Test file deletion when file doesn't exist - error handling."""
        mock_storage.exists.return_value = False
        
        # Create attribute with file reference that doesn't exist
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        attr.file_value = 'nonexistent_file.txt'
        attr.pk = 1  # Set a fake primary key
        
        # Mock the delete operation to avoid database issues
        with patch('django.db.models.Model.delete'):
            attr.delete()
            
            # Should check existence but not try to delete
            mock_storage.exists.assert_called_once_with('nonexistent_file.txt')
            mock_storage.delete.assert_not_called()
        return

    @patch('hi.apps.attribute.models.default_storage')
    def test_attribute_model_file_deletion_exception_handling(self, mock_storage):
        """Test file deletion exception handling - resilient error handling."""
        mock_storage.exists.return_value = True
        mock_storage.delete.side_effect = Exception('Storage error')
        
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        attr.file_value = 'test_file.txt'
        attr.pk = 1  # Set a fake primary key
        
        # Mock the delete operation to avoid database issues  
        with patch('django.db.models.Model.delete'):
            # Delete should not raise exception even if storage deletion fails
            attr.delete()
            
            mock_storage.exists.assert_called_once_with('test_file.txt')
            mock_storage.delete.assert_called_once_with('test_file.txt')
        return

    def test_attribute_model_abstract_upload_to_enforcement(self):
        """Test abstract get_upload_to method enforcement - critical for subclass contracts."""
        # Test that abstract method raises NotImplementedError
        # We use our concrete class but call parent method directly
        attr = ConcreteAttributeModel(
            name='test_attr',
            value_type_str='FILE',
            attribute_type_str='CUSTOM'
        )
        
        # Should raise NotImplementedError when calling parent method
        with self.assertRaises(NotImplementedError):
            AttributeModel.get_upload_to(attr)
        return

    def test_attribute_model_string_representation(self):
        """Test __str__ and __repr__ methods - important for debugging."""
        attr = ConcreteAttributeModel(
            name='test_attr',
            value='test_value',
            value_type_str='TEXT',
            attribute_type_str='CUSTOM'
        )
        
        str_repr = str(attr)
        self.assertIn('test_attr', str_repr)
        self.assertIn('test_value', str_repr)
        self.assertIn('TEXT', str_repr)
        self.assertIn('CUSTOM', str_repr)
        
        # __repr__ should equal __str__
        self.assertEqual(repr(attr), str(attr))
        return

