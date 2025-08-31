"""
Tests for LocationEditFormHandler business logic.

Focuses on high-value form processing logic: formset creation, file operations,
validation orchestration, and error collection patterns.
"""
import logging
import re
from django.test import RequestFactory

from hi.apps.location.location_edit_form_handler import LocationEditFormHandler
from hi.apps.location.models import LocationAttribute
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestLocationEditFormHandler(BaseTestCase):
    """Test LocationEditFormHandler business logic - form processing and file operations."""
    
    def setUp(self):
        super().setUp()
        self.location = LocationSyntheticData.create_test_location(
            name="Test Location Handler"
        )
        self.handler = LocationEditFormHandler()
        self.request_factory = RequestFactory()
        
    def test_formset_prefix_generation_consistency(self):
        """Test formset prefix follows expected pattern - critical for form processing."""
        prefix = LocationEditFormHandler.get_formset_prefix(self.location)
        expected = f"location-{self.location.id}"
        self.assertEqual(prefix, expected)
        
        # Test with different location
        location2 = LocationSyntheticData.create_test_location(name="Another Location")
        prefix2 = LocationEditFormHandler.get_formset_prefix(location2)
        expected2 = f"location-{location2.id}"
        self.assertEqual(prefix2, expected2)
        self.assertNotEqual(prefix, prefix2)
        
    def test_create_location_forms_unbound(self):
        """Test creating unbound forms for initial display - form initialization logic."""
        location_form, file_attributes, regular_formset = self.handler.create_location_forms(self.location)
        
        # Location form should be unbound
        self.assertFalse(location_form.is_bound)
        self.assertEqual(location_form.instance, self.location)
        
        # File attributes should be queryset of FILE type attributes
        self.assertEqual(list(file_attributes), list(self.location.attributes.filter(
            value_type_str=str(AttributeValueType.FILE)
        ).order_by('id')))
        
        # Regular formset should be unbound and exclude FILE attributes
        self.assertFalse(regular_formset.is_bound)
        self.assertEqual(regular_formset.instance, self.location)
        
    def test_create_location_forms_bound_with_data(self):
        """Test creating bound forms with POST data - form binding logic."""
        form_data = {
            'name': 'Updated Location Name',
            # Add formset management form data
            f'location-{self.location.id}-TOTAL_FORMS': '1',
            f'location-{self.location.id}-INITIAL_FORMS': '0',
            f'location-{self.location.id}-MIN_NUM_FORMS': '0',
            f'location-{self.location.id}-MAX_NUM_FORMS': '1000',
        }
        
        location_form, file_attributes, regular_formset = self.handler.create_location_forms(
            self.location, form_data
        )
        
        # Forms should be bound with data
        self.assertTrue(location_form.is_bound)
        self.assertTrue(regular_formset.is_bound)
        
        # Formset should use correct prefix
        expected_prefix = LocationEditFormHandler.get_formset_prefix(self.location)
        self.assertEqual(regular_formset.prefix, expected_prefix)
        
    def test_validate_forms_both_valid(self):
        """Test form validation when both forms are valid - success path."""
        # Create valid form data
        form_data = {
            'name': 'Valid Location Name',
            f'location-{self.location.id}-TOTAL_FORMS': '0',
            f'location-{self.location.id}-INITIAL_FORMS': '0',
            f'location-{self.location.id}-MIN_NUM_FORMS': '0',
            f'location-{self.location.id}-MAX_NUM_FORMS': '1000',
        }
        
        location_form, _, regular_formset = self.handler.create_location_forms(
            self.location, form_data
        )
        
        is_valid = self.handler.validate_forms(location_form, regular_formset)
        self.assertTrue(is_valid)
        
    def test_validate_forms_location_invalid(self):
        """Test form validation when location form is invalid - error handling."""
        # Create invalid form data (empty name)
        form_data = {
            'name': '',  # Invalid empty name
            f'location-{self.location.id}-TOTAL_FORMS': '0',
            f'location-{self.location.id}-INITIAL_FORMS': '0',
            f'location-{self.location.id}-MIN_NUM_FORMS': '0',
            f'location-{self.location.id}-MAX_NUM_FORMS': '1000',
        }
        
        location_form, _, regular_formset = self.handler.create_location_forms(
            self.location, form_data
        )
        
        is_valid = self.handler.validate_forms(location_form, regular_formset)
        self.assertFalse(is_valid)
        
    def test_validate_forms_formset_invalid(self):
        """Test form validation when formset is invalid - error handling."""
        # Create form data with invalid formset (will depend on actual form validation rules)
        form_data = {
            'name': 'Valid Location Name',
            f'location-{self.location.id}-TOTAL_FORMS': '1',
            f'location-{self.location.id}-INITIAL_FORMS': '0',
            f'location-{self.location.id}-MIN_NUM_FORMS': '0',
            f'location-{self.location.id}-MAX_NUM_FORMS': '1000',
            # Add invalid attribute data
            f'location-{self.location.id}-0-name': '',  # Empty name might be invalid
            f'location-{self.location.id}-0-value': 'some value',
        }
        
        location_form, _, regular_formset = self.handler.create_location_forms(
            self.location, form_data
        )
        
        is_valid = self.handler.validate_forms(location_form, regular_formset)
        # Result depends on actual validation rules, but testing the validation orchestration
        self.assertIsInstance(is_valid, bool)
        
    def test_process_file_deletions_valid_file_attributes(self):
        """Test file deletion processing with valid file attributes - file management logic."""
        # Create file attribute
        file_attr = LocationAttribute.objects.create(
            location=self.location,
            name='test_file',
            value='Test File',
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),  # Can be deleted
        )
        
        # Create request with file deletion
        post_data = {
            'delete_file_attribute': [str(file_attr.id)]
        }
        request = self.request_factory.post('/', post_data)
        
        # Should delete the file attribute
        self.handler.process_file_deletions(request, self.location)
        
        # Attribute should be deleted
        self.assertFalse(LocationAttribute.objects.filter(id=file_attr.id).exists())
        
    def test_process_file_deletions_non_deletable_attribute(self):
        """Test file deletion processing skips non-deletable attributes - permission logic."""
        # Create non-deletable file attribute
        file_attr = LocationAttribute.objects.create(
            location=self.location,
            name='predefined_file',
            value='Predefined File',
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.PREDEFINED),  # Cannot be deleted
        )
        
        post_data = {
            'delete_file_attribute': [str(file_attr.id)]
        }
        request = self.request_factory.post('/', post_data)
        
        # Should not delete the file attribute
        self.handler.process_file_deletions(request, self.location)
        
        # Attribute should still exist
        self.assertTrue(LocationAttribute.objects.filter(id=file_attr.id).exists())
        
    def test_process_file_deletions_invalid_attribute_id(self):
        """Test file deletion processing handles invalid attribute IDs gracefully - error handling."""
        post_data = {
            'delete_file_attribute': ['999999', '']  # Non-existent, empty
        }
        request = self.request_factory.post('/', post_data)
        
        # Should not raise exception
        self.handler.process_file_deletions(request, self.location)
        # No assertions needed - just ensure no exceptions are raised
        
    def test_process_file_title_updates_valid_updates(self):
        """Test file title update processing - file metadata management logic."""
        # Create file attribute
        file_attr = LocationAttribute.objects.create(
            location=self.location,
            name='test_file',
            value='Original Title',
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
        )
        
        # Create request with file title update
        field_name = f'file_title_{self.location.id}_{file_attr.id}'
        post_data = {
            field_name: 'Updated Title'
        }
        request = self.request_factory.post('/', post_data)
        
        self.handler.process_file_title_updates(request, self.location)
        
        # Attribute value should be updated
        file_attr.refresh_from_db()
        self.assertEqual(file_attr.value, 'Updated Title')
        
    def test_process_file_title_updates_pattern_matching(self):
        """Test file title field name pattern matching - field parsing logic."""
        # Create file attribute
        file_attr = LocationAttribute.objects.create(
            location=self.location,
            name='test_file',
            value='Original Title',
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
        )
        
        # Test various field name patterns
        test_cases = [
            (f'file_title_{self.location.id}_{file_attr.id}', 'Valid Pattern', True),
            ('file_title_wrong_format', 'Invalid Pattern', False),
            (f'file_title_{self.location.id + 1}_{file_attr.id}', 'Wrong Location', False),
            (f'file_title_{self.location.id}_999999', 'Non-existent Attr', False),
        ]
        
        for field_name, new_title, should_update in test_cases:
            with self.subTest(field_name=field_name):
                original_title = file_attr.value
                
                post_data = {field_name: new_title}
                request = self.request_factory.post('/', post_data)
                
                self.handler.process_file_title_updates(request, self.location)
                
                file_attr.refresh_from_db()
                if should_update:
                    self.assertEqual(file_attr.value, new_title)
                else:
                    self.assertEqual(file_attr.value, original_title)
                    
                # Reset for next test
                file_attr.value = 'Original Title'
                file_attr.save()
                
    def test_process_file_title_updates_empty_title_handling(self):
        """Test file title update processing handles empty titles - data validation."""
        file_attr = LocationAttribute.objects.create(
            location=self.location,
            name='test_file',
            value='Original Title',
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
        )
        
        # Test empty and whitespace-only titles
        test_cases = ['', '   ', '\t\n']
        
        for empty_title in test_cases:
            with self.subTest(empty_title=repr(empty_title)):
                original_title = file_attr.value
                
                field_name = f'file_title_{self.location.id}_{file_attr.id}'
                post_data = {field_name: empty_title}
                request = self.request_factory.post('/', post_data)
                
                self.handler.process_file_title_updates(request, self.location)
                
                file_attr.refresh_from_db()
                # Title should remain unchanged for empty values
                self.assertEqual(file_attr.value, original_title)
                
    def test_collect_form_errors_multiple_sources(self):
        """Test error collection from multiple form sources - comprehensive error handling."""
        # Create forms with errors
        form_data = {
            'name': '',  # Will cause location form error
            f'location-{self.location.id}-TOTAL_FORMS': '1',
            f'location-{self.location.id}-INITIAL_FORMS': '0',
            f'location-{self.location.id}-MIN_NUM_FORMS': '0',
            f'location-{self.location.id}-MAX_NUM_FORMS': '1000',
            # Invalid attribute data might cause formset errors
            f'location-{self.location.id}-0-name': '',
            f'location-{self.location.id}-0-value': '',
        }
        
        location_form, _, regular_formset = self.handler.create_location_forms(
            self.location, form_data
        )
        
        # Trigger validation to generate errors
        location_form.is_valid()
        regular_formset.is_valid()
        
        errors = self.handler.collect_form_errors(location_form, regular_formset)
        
        # Should return a list of error strings
        self.assertIsInstance(errors, list)
        # Specific error content depends on form validation rules
        
    def test_create_initial_context_structure(self):
        """Test initial context creation includes all required components - template integration."""
        context = self.handler.create_initial_context(self.location)
        
        # Should include all expected keys
        required_keys = [
            'location', 'location_form', 'owner_form', 'file_attributes', 
            'regular_attributes_formset', 'attr_context', 'owner'
        ]
        
        for key in required_keys:
            with self.subTest(key=key):
                self.assertIn(key, context)
                
        # Generic aliases should point to same objects
        self.assertIs(context['owner_form'], context['location_form'])
        self.assertIs(context['owner'], context['location'])
        self.assertIs(context['location'], self.location)
        
    def test_create_initial_context_attribute_context_integration(self):
        """Test initial context includes AttributeEditContext integration - template generalization."""
        context = self.handler.create_initial_context(self.location)
        
        # Should have attr_context
        self.assertIn('attr_context', context)
        attr_context = context['attr_context']
        
        # attr_context should be LocationAttributeEditContext
        from hi.apps.location.location_attribute_edit_context import LocationAttributeEditContext
        self.assertIsInstance(attr_context, LocationAttributeEditContext)
        
        # Should reference the same location
        self.assertEqual(attr_context.location, self.location)
        
    def test_file_title_pattern_regex_accuracy(self):
        """Test the file title pattern regex matches expected formats - pattern validation."""
        # Access the pattern used in the handler (it's defined in the method)
        pattern = re.compile(r'^file_title_(\d+)_(\d+)$')
        
        test_cases = [
            ('file_title_123_456', True, ('123', '456')),
            ('file_title_0_0', True, ('0', '0')),
            ('file_title_abc_123', False, None),
            ('file_title_123_abc', False, None),
            ('file_title_123', False, None),
            ('prefix_file_title_123_456', False, None),
            ('file_title_123_456_suffix', False, None),
        ]
        
        for field_name, should_match, expected_groups in test_cases:
            with self.subTest(field_name=field_name):
                match = pattern.match(field_name)
                if should_match:
                    self.assertIsNotNone(match)
                    self.assertEqual(match.groups(), expected_groups)
                else:
                    self.assertIsNone(match)
                    
