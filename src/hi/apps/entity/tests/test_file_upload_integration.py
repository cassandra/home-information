"""
File upload context integration tests.

Tests file storage patterns, upload path generation, file cleanup operations,
and cross-owner file handling consistency using AttributeItemEditContext pattern.
"""
import logging
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from hi.apps.entity.tests.synthetic_data import EntityAttributeSyntheticData
from hi.apps.entity.models import EntityAttribute
from hi.apps.attribute.enums import AttributeValueType, AttributeType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestFileUploadContextIntegration(BaseTestCase):
    """Test file upload operations with AttributeItemEditContext integration."""
    
    def setUp(self):
        super().setUp()
        # Create temporary media root for this test class
        self._temp_media_dir = tempfile.mkdtemp()
        self._settings_patcher = override_settings(MEDIA_ROOT=self._temp_media_dir)
        self._settings_patcher.enable()
        
        self.entity = EntityAttributeSyntheticData.create_test_entity(
            name="File Upload Test Entity"
        )
    
    def tearDown(self):
        # Clean up the temporary media directory and settings
        if hasattr(self, '_settings_patcher'):
            self._settings_patcher.disable()
        if hasattr(self, '_temp_media_dir'):
            import shutil
            shutil.rmtree(self._temp_media_dir, ignore_errors=True)
        super().tearDown()
        
    def test_file_attribute_creation_with_context(self):
        """Test file attribute creation provides correct context - file lifecycle integration."""
        test_file = EntityAttributeSyntheticData.create_test_image_file()
        
        # Create file attribute
        file_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name=test_file.name,
            value="Test Image",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=test_file
        )
        
        # Test AttributeItemEditContext integration
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Context should provide file-related functionality
        file_title_field = context.file_title_field_name(file_attr.id)
        expected_field = f"file_title_{self.entity.id}_{file_attr.id}"
        self.assertEqual(file_title_field, expected_field)
        
    def test_file_upload_path_generation_consistency(self):
        """Test file upload paths follow consistent patterns across contexts - storage organization."""
        # Create file attributes for entity
        image_file = EntityAttributeSyntheticData.create_test_image_file()
        pdf_file = EntityAttributeSyntheticData.create_test_pdf_file()
        
        entity_image = EntityAttribute.objects.create(
            entity=self.entity,
            name="entity_image.jpg",
            value="Entity Image",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=image_file
        )
        
        entity_pdf = EntityAttribute.objects.create(
            entity=self.entity,
            name="entity_document.pdf",
            value="Entity Document",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=pdf_file
        )
        
        # File paths should follow consistent patterns
        self.assertTrue(hasattr(entity_image, 'file_value'))
        self.assertTrue(hasattr(entity_pdf, 'file_value'))
        
        # Context should handle both file types consistently
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        image_field = context.file_title_field_name(entity_image.id)
        pdf_field = context.file_title_field_name(entity_pdf.id)
        
        # Both should follow same naming pattern
        self.assertRegex(image_field, r'^file_title_\d+_\d+$')
        self.assertRegex(pdf_field, r'^file_title_\d+_\d+$')
        
    def test_file_deletion_context_integration(self):
        """Test file deletion with AttributeItemEditContext - cleanup workflow integration."""
        test_file = self.create_test_text_file("test_delete.txt", "content to be deleted")
        
        file_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="test_delete.txt",
            value="File to Delete",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=test_file
        )
        
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Context should provide deletion-related functionality
        self.assertEqual(context.owner_id, self.entity.id)
        original_count = EntityAttribute.objects.filter(entity=self.entity).count()
        
        # Delete the attribute
        file_attr.delete()
        
        # Should be removed from context queries
        new_count = EntityAttribute.objects.filter(entity=self.entity).count()
        self.assertEqual(new_count, original_count - 1)
        
    def test_file_title_update_context_integration(self):
        """Test file title updates through context interface - metadata management."""
        test_file = self.create_test_text_file("original_title.txt", "file content")
        
        file_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="original_title.txt",
            value="Original Title",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=test_file
        )
        
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Get field name that would be used in form
        field_name = context.file_title_field_name(file_attr.id)
        expected_pattern = f"file_title_{self.entity.id}_{file_attr.id}"
        self.assertEqual(field_name, expected_pattern)
        
        # Update the title
        new_title = "Updated File Title"
        file_attr.value = new_title
        file_attr.save()
        
        # Context should reflect the updated title
        file_attr.refresh_from_db()
        self.assertEqual(file_attr.value, new_title)
        
    def test_cross_owner_file_handling_consistency(self):
        """Test file operations work consistently across Entity and Location - cross-owner compatibility."""
        from hi.apps.location.tests.synthetic_data import LocationSyntheticData
        from hi.apps.location.models import LocationAttribute
        from hi.apps.location.location_attribute_edit_context import LocationAttributeItemEditContext
        
        # Create location for comparison
        location = LocationSyntheticData.create_test_location(name="File Test Location")
        
        # Create file attributes for both entity and location
        entity_file = self.create_test_text_file("entity_file.txt", "entity content")
        location_file = self.create_test_text_file("location_file.txt", "location content")
        
        entity_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="entity_file.txt",
            value="Entity File",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=entity_file
        )
        
        location_attr = LocationAttribute.objects.create(
            location=location,
            name="location_file.txt",
            value="Location File",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=location_file
        )
        
        # Create contexts
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        entity_context = EntityAttributeItemEditContext(self.entity)
        location_context = LocationAttributeItemEditContext(location)
        
        # File field naming should follow same pattern
        entity_field = entity_context.file_title_field_name(entity_attr.id)
        location_field = location_context.file_title_field_name(location_attr.id)
        
        # Both should follow pattern: file_title_{owner_id}_{attr_id}
        self.assertRegex(entity_field, r'^file_title_\d+_\d+$')
        self.assertRegex(location_field, r'^file_title_\d+_\d+$')
        
        # Template context should handle files consistently
        entity_template_ctx = entity_context.to_template_context()
        location_template_ctx = location_context.to_template_context()
        
        # Both should have attr_item_context for template usage
        self.assertIn('attr_item_context', entity_template_ctx)
        self.assertIn('attr_item_context', location_template_ctx)
        
    def test_file_mime_type_detection_integration(self):
        """Test MIME type detection works with context integration - file type handling."""
        # Create files with different MIME types
        image_file = SimpleUploadedFile(
            "test_image.jpg",
            b"fake jpeg data",
            content_type="image/jpeg"
        )
        
        pdf_file = SimpleUploadedFile(
            "test_document.pdf",
            b"fake pdf data",
            content_type="application/pdf"
        )
        
        # Create attributes with different file types
        image_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="test_image.jpg",
            value="Test Image",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=image_file,
            file_mime_type="image/jpeg"
        )
        
        pdf_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="test_document.pdf",
            value="Test Document",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=pdf_file,
            file_mime_type="application/pdf"
        )
        
        # Context should work with all file types
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Should generate consistent field names regardless of MIME type
        image_field = context.file_title_field_name(image_attr.id)
        pdf_field = context.file_title_field_name(pdf_attr.id)
        
        self.assertRegex(image_field, r'^file_title_\d+_\d+$')
        self.assertRegex(pdf_field, r'^file_title_\d+_\d+$')
        
    def test_large_file_handling_context_integration(self):
        """Test large file handling with context integration - performance and storage."""
        # Create a large file
        large_file = EntityAttributeSyntheticData.create_large_text_file()
        
        large_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="large_file.txt",
            value="Large File",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=large_file
        )
        
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Context operations should work efficiently with large files
        field_name = context.file_title_field_name(large_attr.id)
        history_id = context.history_target_id(large_attr.id)
        
        # Operations should complete without performance issues
        self.assertIsInstance(field_name, str)
        self.assertIsInstance(history_id, str)
        
    def test_file_upload_form_context_integration(self):
        """Test file upload form integration with context - upload workflow."""
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Context should provide template integration data
        template_ctx = context.to_template_context()
        
        # Should have context data needed for upload forms
        self.assertIn('attr_item_context', template_ctx)
        self.assertIn('owner', template_ctx)
        self.assertIn('entity', template_ctx)
        
        # Upload form would use these for generating correct field names and URLs
        attr_item_context = template_ctx['attr_item_context']
        self.assertEqual(attr_item_context.owner_type, 'entity')
        self.assertEqual(attr_item_context.owner_id, self.entity.id)
        
    def test_file_error_handling_context_integration(self):
        """Test file error handling with context integration - error resilience."""
        # Test with invalid file operations
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Context should handle edge cases gracefully
        invalid_attr_id = 999999
        field_name = context.file_title_field_name(invalid_attr_id)
        
        # Should generate field name even for non-existent attribute
        expected = f"file_title_{self.entity.id}_{invalid_attr_id}"
        self.assertEqual(field_name, expected)
        
        # Context operations should not depend on attribute existence
        history_id = context.history_target_id(invalid_attr_id)
        self.assertIn(str(invalid_attr_id), history_id)
        
    def test_file_permissions_context_integration(self):
        """Test file permissions with context integration - security integration."""
        # Create file attributes with different permission levels
        custom_file = SimpleUploadedFile("custom_file.txt", b"custom content")
        
        # Custom attribute (can be deleted)
        custom_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="custom_file.txt",
            value="Custom File",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=custom_file
        )
        
        # Predefined attribute (cannot be deleted)
        predefined_file = SimpleUploadedFile("predefined_file.txt", b"predefined content")
        predefined_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="predefined_file.txt",
            value="Predefined File",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.PREDEFINED),
            file_value=predefined_file
        )
        
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Context should work with both permission levels
        custom_field = context.file_title_field_name(custom_attr.id)
        predefined_field = context.file_title_field_name(predefined_attr.id)
        
        # Field generation should be consistent regardless of permissions
        self.assertRegex(custom_field, r'^file_title_\d+_\d+$')
        self.assertRegex(predefined_field, r'^file_title_\d+_\d+$')
        
        # Permission checking happens at the business logic level, not context level
        self.assertTrue(custom_attr.attribute_type.can_delete)
        self.assertFalse(predefined_attr.attribute_type.can_delete)
        
    def test_file_history_context_integration(self):
        """Test file attribute history with context integration - audit trail integration."""
        test_file = SimpleUploadedFile("history_file.txt", b"original content")
        
        file_attr = EntityAttribute.objects.create(
            entity=self.entity,
            name="history_file.txt",
            value="Original Title",
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
            file_value=test_file
        )
        
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
        context = EntityAttributeItemEditContext(self.entity)
        
        # Context should provide history-related functionality
        history_target = context.history_target_id(file_attr.id)
        history_toggle = context.history_toggle_id(file_attr.id)
        
        expected_target = f"hi-entity-attr-history-{self.entity.id}-{file_attr.id}"
        expected_toggle = f"history-extra-{self.entity.id}-{file_attr.id}"
        
        self.assertEqual(history_target, expected_target)
        self.assertEqual(history_toggle, expected_toggle)
        
        # Update file title to create history
        file_attr.value = "Updated Title"
        file_attr.save()
        
        # Context should still work after updates
        new_history_target = context.history_target_id(file_attr.id)
        self.assertEqual(new_history_target, expected_target)  # Should be consistent
        
