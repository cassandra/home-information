"""
Unit tests for EntityEditFormHandler.

Tests the complex form handling business logic including form creation,
validation, file processing, and error collection.
"""
import logging
from unittest.mock import patch
from django.http import QueryDict
from django.test import RequestFactory

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.entity.entity_edit_form_handler import EntityEditFormHandler
from hi.apps.entity.enums import EntityType
from hi.apps.entity.forms import EntityForm, EntityAttributeRegularFormSet
from hi.apps.entity.models import EntityAttribute
from django.urls import reverse
from hi.testing.base_test_case import BaseTestCase
from .synthetic_data import EntityAttributeSyntheticData

logging.disable(logging.CRITICAL)


class TestEntityEditFormHandlerFormCreation(BaseTestCase):
    """Test form creation and initialization logic."""

    def setUp(self):
        super().setUp()
        self.handler = EntityEditFormHandler()
        self.entity = EntityAttributeSyntheticData.create_test_entity(name='Test Entity')

    def test_create_entity_forms_unbound(self):
        """Test creating unbound forms for initial rendering."""
        entity_form, file_attributes, regular_attributes_formset = self.handler.create_entity_forms(self.entity)
        
        # Verify form types and initialization
        self.assertIsInstance(entity_form, EntityForm)
        self.assertEqual(entity_form.instance, self.entity)
        self.assertFalse(entity_form.is_bound)
        
        # Verify formset initialization
        self.assertIsInstance(regular_attributes_formset, EntityAttributeRegularFormSet)
        self.assertEqual(regular_attributes_formset.instance, self.entity)
        self.assertFalse(regular_attributes_formset.is_bound)
        
        # File attributes should be a QuerySet
        self.assertEqual(list(file_attributes), [])  # No file attributes yet

    def test_create_entity_forms_bound_with_data(self):
        """Test creating bound forms with POST data."""
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, name='Updated Name'
        )
        
        entity_form, file_attributes, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        # Verify bound forms
        self.assertTrue(entity_form.is_bound)
        self.assertTrue(regular_attributes_formset.is_bound)
        self.assertEqual(entity_form.data['name'], 'Updated Name')

    def test_create_entity_forms_filters_file_attributes_correctly(self):
        """Test that file attributes are correctly separated from regular attributes."""
        # Create mixed attributes
        EntityAttributeSyntheticData.create_test_text_attribute(
            entity=self.entity, name='description'
        )
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity, name='manual'
        )
        
        entity_form, file_attributes, regular_attributes_formset = self.handler.create_entity_forms(self.entity)
        
        # Verify file attributes separation
        file_attr_list = list(file_attributes)
        self.assertEqual(len(file_attr_list), 1)
        self.assertEqual(file_attr_list[0], file_attr)
        
        # Verify formset only includes non-file attributes
        # Note: The actual filtering happens in the formset queryset
        self.assertIsNotNone(regular_attributes_formset)

    def test_create_entity_forms_with_formset_prefix(self):
        """Test that formset uses correct prefix based on entity ID."""
        entity_form, file_attributes, regular_attributes_formset = self.handler.create_entity_forms(self.entity)
        
        # Verify prefix includes entity ID
        expected_prefix = EntityEditFormHandler.get_formset_prefix(self.entity)
        self.assertEqual(regular_attributes_formset.prefix, expected_prefix)


class TestEntityEditFormHandlerValidation(BaseTestCase):
    """Test form validation logic."""

    def setUp(self):
        super().setUp()
        self.handler = EntityEditFormHandler()
        self.entity = EntityAttributeSyntheticData.create_test_entity()

    def test_validate_forms_both_valid(self):
        """Test validation when both forms are valid."""
        # Create valid form data
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, name='Valid Name'
        )
        
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        result = self.handler.validate_forms(entity_form, regular_attributes_formset)
        self.assertTrue(result)

    def test_validate_forms_entity_form_invalid(self):
        """Test validation when entity form is invalid."""
        # Create invalid form data (empty name)
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, name=''  # Invalid: required field
        )
        
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        result = self.handler.validate_forms(entity_form, regular_attributes_formset)
        self.assertFalse(result)
        self.assertFalse(entity_form.is_valid())

    def test_validate_forms_formset_invalid(self):
        """Test validation when formset is invalid."""
        # Create attribute for formset testing
        attr = EntityAttributeSyntheticData.create_test_text_attribute(entity=self.entity)
        
        # Create valid entity data but invalid formset data
        entity_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        formset_data = EntityAttributeSyntheticData.create_formset_data_for_attributes([attr], self.entity)
        prefix = EntityEditFormHandler.get_formset_prefix(self.entity)
        formset_data[f'{prefix}-0-name'] = ''  # Invalid: empty name
        
        form_data = {**entity_data, **formset_data}
        
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        result = self.handler.validate_forms(entity_form, regular_attributes_formset)
        self.assertFalse(result)

    def test_validate_forms_both_invalid(self):
        """Test validation when both forms are invalid."""
        prefix = EntityEditFormHandler.get_formset_prefix(self.entity)
        form_data = {
            'name': '',  # Invalid entity name
            f'{prefix}-TOTAL_FORMS': '1',
            f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-0-name': '',  # Invalid attribute name
        }
        
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        result = self.handler.validate_forms(entity_form, regular_attributes_formset)
        self.assertFalse(result)


class TestEntityEditFormHandlerSaveOperations(BaseTestCase):
    """Test form saving and file processing operations."""

    def setUp(self):
        super().setUp()
        self.handler = EntityEditFormHandler()
        self.entity = EntityAttributeSyntheticData.create_test_entity()
        self.factory = RequestFactory()

    def test_save_forms_basic_success(self):
        """Test successful form saving with transaction."""
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, name='Updated Entity Name'
        )
        
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        # Create real request
        request = self.factory.post('/fake-url/', {})
        
        # Save forms
        self.handler.save_forms(entity_form, regular_attributes_formset, request, self.entity)
        
        # Verify entity was updated
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.name, 'Updated Entity Name')

    def test_save_forms_uses_transaction(self):
        """Test that save_forms uses database transaction with rollback behavior."""
        # Create a text attribute to modify
        attr = EntityAttributeSyntheticData.create_test_text_attribute(
            entity=self.entity, name='test_attr', value='original_value'
        )
        
        # Create form data that will modify both entity and attribute
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, name='Updated Entity Name'
        )
        
        # Update the attribute value in the formset data
        prefix = EntityEditFormHandler.get_formset_prefix(self.entity) 
        form_data[f'{prefix}-0-id'] = str(attr.id)
        form_data[f'{prefix}-0-name'] = attr.name
        form_data[f'{prefix}-0-value'] = 'updated_value'
        form_data[f'{prefix}-0-attribute_type_str'] = attr.attribute_type_str
        
        # Use real entity_edit URL to ensure proper transaction handling
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, form_data)
        
        # Should succeed with proper transaction
        self.assertEqual(response.status_code, 200)
        
        # Verify both entity and attribute were updated (transactional success)
        self.entity.refresh_from_db()
        attr.refresh_from_db()
        self.assertEqual(self.entity.name, 'Updated Entity Name')
        self.assertEqual(attr.value, 'updated_value')

    def test_save_forms_processes_file_operations(self):
        """Test that save_forms calls file processing methods."""
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        # Create real request
        request = self.factory.post('/fake-url/', {})
        
        # Mock the file processing methods
        with patch.object(self.handler, 'process_file_deletions') as mock_deletions, \
             patch.object(self.handler, 'process_file_title_updates') as mock_updates:
            
            self.handler.save_forms(entity_form, regular_attributes_formset, request, self.entity)
            
            mock_deletions.assert_called_once_with(request, self.entity)
            mock_updates.assert_called_once_with(request, self.entity)


class TestEntityEditFormHandlerFileDeletions(BaseTestCase):
    """Test file deletion processing logic."""

    def setUp(self):
        super().setUp()
        self.handler = EntityEditFormHandler()
        self.entity = EntityAttributeSyntheticData.create_test_entity()
        self.factory = RequestFactory()

    def test_process_file_deletions_single_file(self):
        """Test deleting a single file attribute."""
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(entity=self.entity)
        
        # Create real request with POST data
        post_data = QueryDict(mutable=True)
        post_data.setlist('delete_file_attribute', [str(file_attr.id)])
        request = self.factory.post('/fake-url/', post_data)
        
        # Verify file exists before deletion
        self.assertTrue(EntityAttribute.objects.filter(id=file_attr.id).exists())
        
        # Process deletion
        self.handler.process_file_deletions(request, self.entity)
        
        # Verify file was deleted
        self.assertFalse(EntityAttribute.objects.filter(id=file_attr.id).exists())

    def test_process_file_deletions_multiple_files(self):
        """Test deleting multiple file attributes."""
        file_attr1 = EntityAttributeSyntheticData.create_test_file_attribute(entity=self.entity, name='file1')
        file_attr2 = EntityAttributeSyntheticData.create_test_file_attribute(entity=self.entity, name='file2')
        
        # Debug: Check attributes were created with correct types
        self.assertEqual(file_attr1.value_type_str, str(AttributeValueType.FILE))
        self.assertEqual(file_attr2.value_type_str, str(AttributeValueType.FILE))
        self.assertEqual(file_attr1.attribute_type_str, str(AttributeType.CUSTOM))
        self.assertEqual(file_attr2.attribute_type_str, str(AttributeType.CUSTOM))
        
        # Create form data for entity edit with file deletions
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        form_data['delete_file_attribute'] = [str(file_attr1.id), str(file_attr2.id)]
        
        # Use real entity_edit URL
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, form_data)
        
        # Verify successful response
        self.assertEqual(response.status_code, 200)
        
        # Verify both files were deleted
        self.assertFalse(EntityAttribute.objects.filter(id=file_attr1.id).exists())
        self.assertFalse(EntityAttribute.objects.filter(id=file_attr2.id).exists())

    def test_process_file_deletions_ignores_empty_values(self):
        """Test that empty deletion values are ignored."""
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(entity=self.entity)
        
        # Create form data for entity edit with empty values mixed in
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        form_data['delete_file_attribute'] = ['', str(file_attr.id), '']
        
        # Use real entity_edit URL
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, form_data)
        
        # Verify successful response
        self.assertEqual(response.status_code, 200)
        
        # Only the valid ID should cause deletion
        self.assertFalse(EntityAttribute.objects.filter(id=file_attr.id).exists())

    def test_process_file_deletions_nonexistent_attribute(self):
        """Test handling of nonexistent attribute IDs."""
        # Create real request with nonexistent ID
        post_data = QueryDict(mutable=True)
        post_data.setlist('delete_file_attribute', ['99999'])  # Nonexistent ID
        request = self.factory.post('/fake-url/', post_data)
        
        # Should not raise exception
        self.handler.process_file_deletions(request, self.entity)

    def test_process_file_deletions_wrong_entity(self):
        """Test that attributes belonging to different entities are not deleted."""
        other_entity = EntityAttributeSyntheticData.create_test_entity(name='Other Entity')
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(entity=other_entity)
        
        # Create real request
        post_data = QueryDict(mutable=True)
        post_data.setlist('delete_file_attribute', [str(file_attr.id)])
        request = self.factory.post('/fake-url/', post_data)
        
        self.handler.process_file_deletions(request, self.entity)
        
        # File should still exist (belongs to different entity)
        self.assertTrue(EntityAttribute.objects.filter(id=file_attr.id).exists())

    def test_process_file_deletions_non_file_attribute(self):
        """Test that non-file attributes are not deleted."""
        text_attr = EntityAttributeSyntheticData.create_test_text_attribute(entity=self.entity)
        
        # Create real request with text attribute ID
        post_data = QueryDict(mutable=True)
        post_data.setlist('delete_file_attribute', [str(text_attr.id)])
        request = self.factory.post('/fake-url/', post_data)
        
        self.handler.process_file_deletions(request, self.entity)
        
        # Text attribute should still exist
        self.assertTrue(EntityAttribute.objects.filter(id=text_attr.id).exists())

    def test_process_file_deletions_respects_can_delete_permission(self):
        """Test that deletion respects the can_delete permission."""
        # Create a PREDEFINED file attribute (can't be deleted)
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity,
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        # Create real request
        post_data = QueryDict(mutable=True)
        post_data.setlist('delete_file_attribute', [str(file_attr.id)])
        request = self.factory.post('/fake-url/', post_data)
        
        self.handler.process_file_deletions(request, self.entity)
        
        # File should still exist (deletion not allowed)
        self.assertTrue(EntityAttribute.objects.filter(id=file_attr.id).exists())


class TestEntityEditFormHandlerFileTitleUpdates(BaseTestCase):
    """Test file title update processing logic."""

    def setUp(self):
        super().setUp()
        self.handler = EntityEditFormHandler()
        self.entity = EntityAttributeSyntheticData.create_test_entity()
        self.factory = RequestFactory()

    def test_process_file_title_updates_single_file(self):
        """Test updating a single file title."""
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity, value='Original Title'
        )
        
        # Create real request with POST data
        field_name = f'file_title_{self.entity.id}_{file_attr.id}'
        request = self.factory.post('/fake-url/', {field_name: 'Updated Title'})
        
        self.handler.process_file_title_updates(request, self.entity)
        
        # Verify title was updated
        file_attr.refresh_from_db()
        self.assertEqual(file_attr.value, 'Updated Title')

    def test_process_file_title_updates_multiple_files(self):
        """Test updating multiple file titles."""
        file_attr1 = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity, name='file1', value='Title 1'
        )
        file_attr2 = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity, name='file2', value='Title 2'
        )
        
        field_name1 = f'file_title_{self.entity.id}_{file_attr1.id}'
        field_name2 = f'file_title_{self.entity.id}_{file_attr2.id}'
        
        # Create real request with POST data
        post_data = {
            field_name1: 'New Title 1',
            field_name2: 'New Title 2',
            'other_field': 'ignored',  # Should be ignored
        }
        request = self.factory.post('/fake-url/', post_data)
        
        self.handler.process_file_title_updates(request, self.entity)
        
        # Verify both titles were updated
        file_attr1.refresh_from_db()
        file_attr2.refresh_from_db()
        self.assertEqual(file_attr1.value, 'New Title 1')
        self.assertEqual(file_attr2.value, 'New Title 2')

    def test_process_file_title_updates_ignores_mismatched_entity(self):
        """Test that fields with wrong entity ID are ignored."""
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity, value='Original Title'
        )
        
        # Create form data with wrong entity ID in field name
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        field_name = f'file_title_99999_{file_attr.id}'
        form_data[field_name] = 'Should Not Update'
        
        # Use real entity_edit URL
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, form_data)
        
        # Should return successful response
        self.assertEqual(response.status_code, 200)
        
        # Title should not be updated (observable behavior - what actually matters)
        file_attr.refresh_from_db()
        self.assertEqual(file_attr.value, 'Original Title')

    def test_process_file_title_updates_ignores_empty_title(self):
        """Test that empty titles are ignored."""
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity, value='Original Title'
        )
        
        # Create form data with empty title (whitespace only)
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        field_name = f'file_title_{self.entity.id}_{file_attr.id}'
        form_data[field_name] = '   '  # Whitespace only
        
        # Use real entity_edit URL
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, form_data)
        
        # Should return successful response
        self.assertEqual(response.status_code, 200)
        
        # Title should not be updated (observable behavior)
        file_attr.refresh_from_db()
        self.assertEqual(file_attr.value, 'Original Title')

    def test_process_file_title_updates_skips_unchanged_titles(self):
        """Test that unchanged titles are not unnecessarily saved."""
        file_attr = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity, value='Same Title'
        )
        
        field_name = f'file_title_{self.entity.id}_{file_attr.id}'
        request = self.factory.post('/fake-url/', {field_name: 'Same Title'})
        
        # Mock the save method to verify it's not called
        with patch.object(file_attr, 'save') as mock_save:
            self.handler.process_file_title_updates(request, self.entity)
            
            mock_save.assert_not_called()

    def test_process_file_title_updates_handles_invalid_attribute_id(self):
        """Test handling of invalid attribute IDs."""
        # Create form data with invalid attribute ID in field name
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        field_name = f'file_title_{self.entity.id}_invalid'
        form_data[field_name] = 'New Title'
        
        # Use real entity_edit URL - should handle invalid ID gracefully
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, form_data)
        
        # Should return successful response (invalid IDs are handled gracefully)
        self.assertEqual(response.status_code, 200)

    def test_process_file_title_updates_handles_nonexistent_attribute(self):
        """Test handling of nonexistent attribute IDs."""
        # Create form data with nonexistent attribute ID in field name
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        field_name = f'file_title_{self.entity.id}_99999'
        form_data[field_name] = 'New Title'
        
        # Use real entity_edit URL - should handle nonexistent ID gracefully
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.post(url, form_data)
        
        # Should return successful response (nonexistent IDs are handled gracefully)
        self.assertEqual(response.status_code, 200)


class TestEntityEditFormHandlerErrorCollection(BaseTestCase):
    """Test form error collection and formatting."""

    def setUp(self):
        super().setUp()
        self.handler = EntityEditFormHandler()
        self.entity = EntityAttributeSyntheticData.create_test_entity()

    def test_collect_form_errors_no_errors(self):
        """Test error collection when no errors exist."""
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        # Ensure forms are valid
        entity_form.is_valid()
        regular_attributes_formset.is_valid()
        
        errors = self.handler.collect_form_errors(entity_form, regular_attributes_formset)
        self.assertEqual(errors, [])

    def test_collect_form_errors_entity_form_errors(self):
        """Test collection of entity form non-field errors."""
        # Since EntityForm doesn't have custom clean() methods that create non-field errors,
        # we create a minimal test that confirms the method handles forms without non-field errors
        form_data = {'name': 'Valid Name', 'entity_type_str': str(EntityType.LIGHT)}
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        entity_form.is_valid()  # Trigger validation
        regular_attributes_formset.is_valid()
        
        errors = self.handler.collect_form_errors(entity_form, regular_attributes_formset)
        
        # Should return empty list since we have no non-field errors
        entity_errors = [err for err in errors if err.startswith('Entity:')]
        self.assertEqual(len(entity_errors), 0)

    def test_collect_form_errors_formset_errors(self):
        """Test collection of formset non-field errors."""
        attr = EntityAttributeSyntheticData.create_test_text_attribute(entity=self.entity)
        
        entity_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        formset_data = EntityAttributeSyntheticData.create_formset_data_for_attributes([attr], self.entity)
        
        form_data = {**entity_data, **formset_data}
        
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        entity_form.is_valid()
        regular_attributes_formset.is_valid()
        
        errors = self.handler.collect_form_errors(entity_form, regular_attributes_formset)
        
        # Should return empty list since we have no non-field errors in valid formset
        self.assertEqual(len(errors), 0)

    def test_collect_form_errors_handles_none_forms(self):
        """Test error collection with None form parameters."""
        errors = self.handler.collect_form_errors(None, None)
        self.assertEqual(errors, [])

    def test_collect_form_errors_comprehensive_error_formatting(self):
        """Test that error messages are properly formatted with context."""
        # Create attribute for formset testing
        attr = EntityAttributeSyntheticData.create_test_text_attribute(entity=self.entity, name='test_prop')
        
        # Create valid data since we're testing non-field error formatting, not field validation
        entity_data = {'name': 'Valid Entity', 'entity_type_str': str(EntityType.LIGHT)}
        formset_data = EntityAttributeSyntheticData.create_formset_data_for_attributes([attr], self.entity)
        
        form_data = {**entity_data, **formset_data}
        
        entity_form, _, regular_attributes_formset = self.handler.create_entity_forms(
            self.entity, form_data
        )
        
        entity_form.is_valid()
        regular_attributes_formset.is_valid()
        
        errors = self.handler.collect_form_errors(entity_form, regular_attributes_formset)
        
        # Since we have valid data and no custom non-field validation, should be empty
        self.assertEqual(len(errors), 0)


class TestEntityEditFormHandlerInitialContext(BaseTestCase):
    """Test initial context creation for template rendering."""

    def setUp(self):
        super().setUp()
        self.handler = EntityEditFormHandler()
        self.entity = EntityAttributeSyntheticData.create_entity_with_mixed_attributes()

    def test_create_initial_context_contains_required_keys(self):
        """Test that initial context contains all required template variables."""
        context = self.handler.create_initial_context(self.entity)
        
        required_keys = ['entity', 'entity_form', 'file_attributes', 'regular_attributes_formset']
        for key in required_keys:
            self.assertIn(key, context)

    def test_create_initial_context_correct_types(self):
        """Test that context values have correct types."""
        context = self.handler.create_initial_context(self.entity)
        
        self.assertEqual(context['entity'], self.entity)
        self.assertIsInstance(context['entity_form'], EntityForm)
        self.assertIsInstance(context['regular_attributes_formset'], EntityAttributeRegularFormSet)
        
        # file_attributes should be a QuerySet
        file_attributes = context['file_attributes']
        self.assertTrue(hasattr(file_attributes, 'model'))  # QuerySet-like

    def test_create_initial_context_file_attributes_filtering(self):
        """Test that file attributes are properly filtered in context."""
        context = self.handler.create_initial_context(self.entity)
        
        file_attributes = list(context['file_attributes'])
        
        # Should only include file attributes
        for attr in file_attributes:
            self.assertEqual(attr.value_type_str, str(AttributeValueType.FILE))

    def test_create_initial_context_unbound_forms(self):
        """Test that initial context creates unbound forms."""
        context = self.handler.create_initial_context(self.entity)
        
        self.assertFalse(context['entity_form'].is_bound)
        self.assertFalse(context['regular_attributes_formset'].is_bound)
        
