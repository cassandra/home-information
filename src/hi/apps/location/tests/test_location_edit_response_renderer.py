"""
Tests for LocationEditResponseRenderer integration logic.

Focuses on high-value template rendering, context assembly, and antinode response
generation patterns.
"""
import logging
from unittest.mock import Mock, patch
from django.test import RequestFactory

from hi.apps.location.location_edit_response_renderer import LocationEditResponseRenderer
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.apps.location.models import LocationAttribute
from hi.apps.attribute.enums import AttributeValueType, AttributeType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestLocationEditResponseRenderer(BaseTestCase):
    """Test LocationEditResponseRenderer template rendering and response logic."""
    
    def setUp(self):
        super().setUp()
        self.location = LocationSyntheticData.create_test_location(
            name="Test Location Renderer"
        )
        self.renderer = LocationEditResponseRenderer()
        self.request_factory = RequestFactory()
        self.request = self.request_factory.get('/')
        
    def test_renderer_initialization(self):
        """Test renderer initializes with form handler - dependency injection."""
        self.assertIsNotNone(self.renderer.form_handler)
        from hi.apps.location.location_edit_form_handler import LocationEditFormHandler
        self.assertIsInstance(self.renderer.form_handler, LocationEditFormHandler)
        
    def test_build_template_context_basic_structure(self):
        """Test template context building includes all required components - context assembly."""
        # Create forms using form handler
        location_form, file_attributes, regular_formset = self.renderer.form_handler.create_location_forms(
            self.location
        )
        
        context = self.renderer.build_template_context(
            location=self.location,
            location_form=location_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_formset,
            success_message="Test success",
            error_message="Test error",
            has_errors=True
        )
        
        # Check all required context keys
        required_keys = [
            'location', 'location_form', 'owner_form', 'file_attributes',
            'regular_attributes_formset', 'success_message', 'error_message',
            'has_errors', 'non_field_errors', 'attr_context', 'owner'
        ]
        
        for key in required_keys:
            with self.subTest(key=key):
                self.assertIn(key, context)
                
        # Check generic aliases
        self.assertIs(context['owner_form'], context['location_form'])
        self.assertIs(context['owner'], context['location'])
        
    def test_build_template_context_attribute_context_integration(self):
        """Test template context includes AttributeEditContext - template generalization."""
        location_form, file_attributes, regular_formset = self.renderer.form_handler.create_location_forms(
            self.location
        )
        
        context = self.renderer.build_template_context(
            location=self.location,
            location_form=location_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_formset
        )
        
        # Should have attr_context from LocationAttributeEditContext
        self.assertIn('attr_context', context)
        attr_context = context['attr_context']
        
        from hi.apps.location.location_attribute_edit_context import LocationAttributeEditContext
        self.assertIsInstance(attr_context, LocationAttributeEditContext)
        self.assertEqual(attr_context.location, self.location)
        
    def test_build_template_context_error_collection(self):
        """Test template context collects form errors - error messaging logic."""
        # Create forms with validation errors
        form_data = {
            'name': '',  # Invalid empty name
            f'location-{self.location.id}-TOTAL_FORMS': '0',
            f'location-{self.location.id}-INITIAL_FORMS': '0',
            f'location-{self.location.id}-MIN_NUM_FORMS': '0',
            f'location-{self.location.id}-MAX_NUM_FORMS': '1000',
        }
        
        location_form, file_attributes, regular_formset = self.renderer.form_handler.create_location_forms(
            self.location, form_data
        )
        
        # Trigger validation
        location_form.is_valid()
        regular_formset.is_valid()
        
        context = self.renderer.build_template_context(
            location=self.location,
            location_form=location_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_formset,
            has_errors=True
        )
        
        # Should include non_field_errors
        self.assertIn('non_field_errors', context)
        self.assertIsInstance(context['non_field_errors'], list)
        
    @patch('hi.apps.location.location_edit_response_renderer.render_to_string')
    @patch('hi.apps.location.location_edit_response_renderer.reverse')
    def test_render_content_fragments_template_rendering(self, mock_reverse, mock_render):
        """Test content fragment rendering uses correct templates - template integration."""
        mock_reverse.return_value = '/location/123/attribute/upload/'
        mock_render.side_effect = ['<content_body>', '<upload_form>']
        
        context = {'location': self.location, 'test': 'data'}
        
        content_body, upload_form = self.renderer.render_content_fragments(
            request=self.request,
            context=context,
            location=self.location
        )
        
        # Should call render_to_string twice with correct templates
        self.assertEqual(mock_render.call_count, 2)
        
        # First call: content body template
        first_call = mock_render.call_args_list[0]
        self.assertEqual(first_call[0][0], 'location/panes/location_edit_content_body.html')
        self.assertEqual(first_call[0][1], context)
        self.assertEqual(first_call[1]['request'], self.request)
        
        # Second call: upload form template
        second_call = mock_render.call_args_list[1]
        self.assertEqual(second_call[0][0], 'attribute/components/upload_form.html')
        self.assertIn('file_upload_url', second_call[0][1])
        
        # Should generate upload URL for this location
        mock_reverse.assert_called_once_with(
            'location_attribute_upload',
            kwargs={'location_id': self.location.id}
        )
        
        self.assertEqual(content_body, '<content_body>')
        self.assertEqual(upload_form, '<upload_form>')
        
    def test_render_update_fragments_with_fresh_forms(self):
        """Test update fragments rendering creates fresh forms when none provided - success case logic."""
        with patch.object(self.renderer, 'render_content_fragments') as mock_render_fragments:
            mock_render_fragments.return_value = ('<content>', '<upload>')
            
            content_body, upload_form = self.renderer.render_update_fragments(
                request=self.request,
                location=self.location,
                success_message="Success!"
            )
            
            # Should call render_content_fragments
            mock_render_fragments.assert_called_once()
            call_args = mock_render_fragments.call_args
            
            # Should have created fresh forms (not None)
            context = call_args[1]['context']
            self.assertIsNotNone(context['location_form'])
            self.assertIsNotNone(context['regular_attributes_formset'])
            self.assertEqual(context['success_message'], "Success!")
            
    def test_render_update_fragments_with_existing_forms(self):
        """Test update fragments rendering uses provided forms - error case logic."""
        # Create forms with errors
        form_data = {
            'name': '',
            f'location-{self.location.id}-TOTAL_FORMS': '0',
            f'location-{self.location.id}-INITIAL_FORMS': '0',
            f'location-{self.location.id}-MIN_NUM_FORMS': '0',
            f'location-{self.location.id}-MAX_NUM_FORMS': '1000',
        }
        
        location_form, file_attributes, regular_formset = self.renderer.form_handler.create_location_forms(
            self.location, form_data
        )
        
        with patch.object(self.renderer, 'render_content_fragments') as mock_render_fragments:
            mock_render_fragments.return_value = ('<error_content>', '<upload>')
            
            self.renderer.render_update_fragments(
                request=self.request,
                location=self.location,
                location_form=location_form,
                regular_attributes_formset=regular_formset,
                error_message="Error!",
                has_errors=True
            )
            
            # Should use provided forms
            mock_render_fragments.assert_called_once()
            call_args = mock_render_fragments.call_args
            context = call_args[1]['context']
            
            self.assertIs(context['location_form'], location_form)
            self.assertIs(context['regular_attributes_formset'], regular_formset)
            self.assertEqual(context['error_message'], "Error!")
            self.assertTrue(context['has_errors'])
            
    @patch('hi.apps.location.location_edit_response_renderer.antinode')
    def test_render_success_response_antinode_integration(self, mock_antinode):
        """Test success response uses antinode with correct parameters - response generation."""
        mock_response = Mock()
        mock_antinode.response.return_value = mock_response
        
        with patch.object(self.renderer, 'render_update_fragments') as mock_render:
            mock_render.return_value = ('<success_content>', '<success_upload>')
            
            response = self.renderer.render_success_response(self.request, self.location)
            
            # Should call render_update_fragments with success message
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            self.assertEqual(call_args[1]['success_message'], "Changes saved successfully")
            
            # Should create antinode response with insert_map
            mock_antinode.response.assert_called_once()
            response_args = mock_antinode.response.call_args
            
            self.assertIn('insert_map', response_args[1])
            insert_map = response_args[1]['insert_map']
            
            # Should have both content and upload form updates using contextual IDs
            # Get the attr_context to check for contextual IDs
            context = self.renderer.form_handler.create_success_context(
                location=self.location,
                location_form=Mock(),
                file_attributes=[],
                regular_attributes_formset=Mock()
            )
            attr_context = context['attr_context']
            
            self.assertIn(attr_context.content_html_id, insert_map)
            self.assertIn(attr_context.upload_form_container_html_id, insert_map)
            self.assertEqual(insert_map[attr_context.content_html_id], '<success_content>')
            self.assertEqual(insert_map[attr_context.upload_form_container_html_id], '<success_upload>')
            
            self.assertEqual(response, mock_response)
            
    @patch('hi.apps.location.location_edit_response_renderer.antinode')
    def test_render_error_response_antinode_integration(self, mock_antinode):
        """Test error response uses antinode with 400 status - error response generation."""
        mock_response = Mock()
        mock_antinode.response.return_value = mock_response
        
        # Create forms with errors
        location_form, _, regular_formset = self.renderer.form_handler.create_location_forms(self.location)
        
        with patch.object(self.renderer, 'render_update_fragments') as mock_render:
            mock_render.return_value = ('<error_content>', '<error_upload>')
            
            response = self.renderer.render_error_response(
                self.request, self.location, location_form, regular_formset
            )
            
            # Should call render_update_fragments with error parameters
            mock_render.assert_called_once()
            self.assertEqual(response, mock_response)
            call_args = mock_render.call_args
            self.assertEqual(call_args[1]['error_message'], "Please correct the errors below")
            self.assertTrue(call_args[1]['has_errors'])
            self.assertIs(call_args[1]['location_form'], location_form)
            self.assertIs(call_args[1]['regular_attributes_formset'], regular_formset)
            
            # Should create antinode response with 400 status
            mock_antinode.response.assert_called_once()
            response_args = mock_antinode.response.call_args
            
            self.assertEqual(response_args[1]['status'], 400)
            self.assertIn('insert_map', response_args[1])
            
    def test_renderer_with_location_having_file_attributes(self):
        """Test renderer handles locations with file attributes - file attribute integration."""
        # Create location with file attribute
        file_attr = LocationAttribute.objects.create(
            location=self.location,
            name='test_document',
            value='Test Document',
            value_type_str=str(AttributeValueType.FILE),
            attribute_type_str=str(AttributeType.CUSTOM),
        )
        
        # Create forms and context
        location_form, file_attributes, regular_formset = self.renderer.form_handler.create_location_forms(
            self.location
        )
        
        context = self.renderer.build_template_context(
            location=self.location,
            location_form=location_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_formset
        )
        
        # File attributes should be included in context
        self.assertIn(file_attr, context['file_attributes'])
        
    def test_renderer_context_consistency_across_operations(self):
        """Test renderer maintains context consistency across different operations - state management."""
        # Test that different operations produce consistent context structure
        
        # Test success case context
        location_form, file_attributes, regular_formset = self.renderer.form_handler.create_location_forms(self.location)
        success_context = self.renderer.build_template_context(
            location=self.location,
            location_form=location_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_formset,
            success_message="Success!"
        )
        
        # Test error case context
        error_context = self.renderer.build_template_context(
            location=self.location,
            location_form=location_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_formset,
            error_message="Error!",
            has_errors=True
        )
        
        # Test initial case context
        initial_context = self.renderer.form_handler.create_initial_context(self.location)
        
        # All contexts should reference the same location and have attr_context
        for context_name, context in [('success', success_context), ('error', error_context), ('initial', initial_context)]:
            with self.subTest(context=context_name):
                self.assertEqual(context['location'], self.location)
                self.assertIn('attr_context', context)
                # attr_context should be the same type across all operations
                from hi.apps.location.location_attribute_edit_context import LocationAttributeEditContext
                self.assertIsInstance(context['attr_context'], LocationAttributeEditContext)
                
    def test_renderer_template_path_consistency(self):
        """Test renderer uses consistent template paths - template organization."""
        with patch('hi.apps.location.location_edit_response_renderer.render_to_string') as mock_render:
            mock_render.return_value = '<rendered>'
            
            context = {'test': 'data'}
            self.renderer.render_content_fragments(self.request, context, self.location)
            
            # Should use location-specific content template
            content_call = mock_render.call_args_list[0]
            self.assertEqual(content_call[0][0], 'location/panes/location_edit_content_body.html')
            
            # Should use generic upload form template
            upload_call = mock_render.call_args_list[1]
            self.assertEqual(upload_call[0][0], 'attribute/components/upload_form.html')
            
    def test_renderer_error_handling_robustness(self):
        """Test renderer handles various error conditions gracefully - error resilience."""
        # Test with None values
        with patch.object(self.renderer.form_handler, 'collect_form_errors') as mock_collect:
            mock_collect.return_value = []
            
            context = self.renderer.build_template_context(
                location=self.location,
                location_form=None,  # Should handle None gracefully
                file_attributes=LocationAttribute.objects.none(),
                regular_attributes_formset=None,
                success_message=None,
                error_message=None,
                has_errors=False
            )
            
            # Should not crash and should include basic required keys
            self.assertEqual(context['location'], self.location)
            self.assertIn('attr_context', context)
            
