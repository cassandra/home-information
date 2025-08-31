"""
Unit tests for EntityEditResponseRenderer.

Tests the template rendering and response generation logic including
context building, fragment rendering, and antinode response construction.
"""
import logging
from unittest.mock import Mock, patch
from django.http import HttpRequest
from django.urls import reverse

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.entity.entity_edit_form_handler import EntityEditFormHandler
from hi.apps.entity.entity_edit_response_renderer import EntityEditResponseRenderer
from hi.constants import DIVID
from hi.testing.base_test_case import BaseTestCase
from .synthetic_data import EntityAttributeSyntheticData

logging.disable(logging.CRITICAL)


class TestEntityEditResponseRendererInitialization(BaseTestCase):
    """Test renderer initialization and dependencies."""

    def test_renderer_initializes_form_handler(self):
        """Test that renderer initializes with form handler dependency."""
        renderer = EntityEditResponseRenderer()
        
        self.assertIsNotNone(renderer.form_handler)
        # Verify it has the expected type
        from hi.apps.entity.entity_edit_form_handler import EntityEditFormHandler
        self.assertIsInstance(renderer.form_handler, EntityEditFormHandler)


class TestEntityEditResponseRendererContextBuilding(BaseTestCase):
    """Test template context building logic."""

    def setUp(self):
        super().setUp()
        self.renderer = EntityEditResponseRenderer()
        self.entity = EntityAttributeSyntheticData.create_test_entity()

    def test_build_template_context_basic_structure(self):
        """Test that context includes all required keys."""
        # Create forms for context
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        entity_form, file_attributes, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(
            self.entity, form_data
        )
        
        context = self.renderer.build_template_context(
            entity=self.entity,
            entity_form=entity_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_attributes_formset
        )
        
        required_keys = [
            'entity', 'entity_form', 'file_attributes', 'regular_attributes_formset',
            'success_message', 'error_message', 'has_errors', 'non_field_errors'
        ]
        
        for key in required_keys:
            self.assertIn(key, context, f"Missing required key: {key}")

    def test_build_template_context_with_success_message(self):
        """Test context building with success message."""
        entity_form, file_attributes, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(self.entity)
        
        context = self.renderer.build_template_context(
            entity=self.entity,
            entity_form=entity_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_attributes_formset,
            success_message="Operation completed successfully"
        )
        
        self.assertEqual(context['success_message'], "Operation completed successfully")
        self.assertIsNone(context['error_message'])
        self.assertFalse(context['has_errors'])

    def test_build_template_context_with_error_message(self):
        """Test context building with error message."""
        entity_form, file_attributes, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(self.entity)
        
        context = self.renderer.build_template_context(
            entity=self.entity,
            entity_form=entity_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_attributes_formset,
            error_message="Validation failed",
            has_errors=True
        )
        
        self.assertEqual(context['error_message'], "Validation failed")
        self.assertIsNone(context['success_message'])
        self.assertTrue(context['has_errors'])

    def test_build_template_context_collects_form_errors(self):
        """Test that context building collects form errors from real invalid forms."""
        # Create forms with invalid data to trigger real form errors
        form_handler = EntityEditFormHandler()
        
        # Create invalid form data - empty name should trigger validation errors
        invalid_form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, 
            name=''  # Invalid - required field
        )
        
        entity_form, file_attributes, regular_attributes_formset = form_handler.create_entity_forms(
            self.entity, 
            invalid_form_data
        )
        
        # Trigger form validation
        entity_form.is_valid()
        regular_attributes_formset.is_valid()
        
        # Build context with these invalid forms
        context = self.renderer.build_template_context(
            entity=self.entity,
            entity_form=entity_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_attributes_formset
        )
        
        # The context should have the forms (with their field errors) but since the collect_form_errors
        # method only looks for non-field errors and we created field errors, non_field_errors should be empty
        self.assertIn('non_field_errors', context)
        self.assertIsInstance(context['non_field_errors'], list)

    def test_build_template_context_correct_object_references(self):
        """Test that context contains correct object references."""
        entity_form, file_attributes, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(self.entity)
        
        context = self.renderer.build_template_context(
            entity=self.entity,
            entity_form=entity_form,
            file_attributes=file_attributes,
            regular_attributes_formset=regular_attributes_formset
        )
        
        # Verify object references are correct
        self.assertIs(context['entity'], self.entity)
        self.assertIs(context['entity_form'], entity_form)
        self.assertIs(context['file_attributes'], file_attributes)
        self.assertIs(context['regular_attributes_formset'], regular_attributes_formset)


class TestEntityEditResponseRendererFragmentRendering(BaseTestCase):
    """Test template fragment rendering logic."""

    def setUp(self):
        super().setUp()
        self.renderer = EntityEditResponseRenderer()
        self.entity = EntityAttributeSyntheticData.create_test_entity()
        self.request = Mock(spec=HttpRequest)

    @patch('hi.apps.entity.entity_edit_response_renderer.render_to_string')
    def test_render_content_fragments_calls_correct_templates(self, mock_render):
        """Test that fragment rendering calls correct templates with proper context."""
        mock_render.side_effect = ['<content_body_html>', '<upload_form_html>']
        
        context = {'entity': self.entity, 'test': 'context'}
        
        content_body, upload_form = self.renderer.render_content_fragments(
            request=self.request,
            context=context,
            entity=self.entity
        )
        
        # Verify template calls
        self.assertEqual(mock_render.call_count, 2)
        
        # First call should be for content body
        first_call = mock_render.call_args_list[0]
        self.assertEqual(first_call[0][0], 'entity/panes/entity_edit_content_body.html')
        self.assertEqual(first_call[0][1], context)
        self.assertEqual(first_call[1]['request'], self.request)
        
        # Second call should be for upload form
        second_call = mock_render.call_args_list[1]
        self.assertEqual(second_call[0][0], 'attribute/components/upload_form.html')
        self.assertIn('file_upload_url', second_call[0][1])
        self.assertEqual(second_call[1]['request'], self.request)

    @patch('hi.apps.entity.entity_edit_response_renderer.render_to_string')
    def test_render_content_fragments_generates_upload_url(self, mock_render):
        """Test that fragment rendering generates correct upload URL."""
        mock_render.side_effect = ['<content_body_html>', '<upload_form_html>']
        
        context = {'entity': self.entity}
        
        self.renderer.render_content_fragments(
            request=self.request,
            context=context,
            entity=self.entity
        )
        
        # Check upload form template call
        upload_form_call = mock_render.call_args_list[1]
        upload_context = upload_form_call[0][1]
        
        expected_url = reverse('entity_attribute_upload', kwargs={'entity_id': self.entity.id})
        self.assertEqual(upload_context['file_upload_url'], expected_url)

    @patch('hi.apps.entity.entity_edit_response_renderer.render_to_string')
    def test_render_content_fragments_returns_rendered_content(self, mock_render):
        """Test that fragment rendering returns the rendered content."""
        mock_render.side_effect = ['<rendered_content_body>', '<rendered_upload_form>']
        
        context = {'entity': self.entity}
        
        content_body, upload_form = self.renderer.render_content_fragments(
            request=self.request,
            context=context,
            entity=self.entity
        )
        
        self.assertEqual(content_body, '<rendered_content_body>')
        self.assertEqual(upload_form, '<rendered_upload_form>')


class TestEntityEditResponseRendererUpdateFragments(BaseTestCase):
    """Test the main fragment update rendering method."""

    def setUp(self):
        super().setUp()
        self.renderer = EntityEditResponseRenderer()
        self.entity = EntityAttributeSyntheticData.create_test_entity()
        self.request = Mock(spec=HttpRequest)

    @patch.object(EntityEditResponseRenderer, 'render_content_fragments')
    def test_render_update_fragments_with_provided_forms(self, mock_render_fragments):
        """Test fragment rendering when forms are provided."""
        mock_render_fragments.return_value = ('<content>', '<upload>')
        
        # Create forms
        entity_form, _, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(self.entity)
        
        content_body, upload_form = self.renderer.render_update_fragments(
            request=self.request,
            entity=self.entity,
            entity_form=entity_form,
            regular_attributes_formset=regular_attributes_formset,
            success_message="Test success"
        )
        
        # Verify render_content_fragments was called
        mock_render_fragments.assert_called_once()
        
        # Verify return values
        self.assertEqual(content_body, '<content>')
        self.assertEqual(upload_form, '<upload>')

    @patch.object(EntityEditResponseRenderer, 'render_content_fragments')
    def test_render_update_fragments_creates_fresh_forms_when_none_provided(self, mock_render_fragments):
        """Test that fresh forms are created when none are provided."""
        mock_render_fragments.return_value = ('<content>', '<upload>')
        
        content_body, upload_form = self.renderer.render_update_fragments(
            request=self.request,
            entity=self.entity,
            success_message="Test success"
        )
        
        # Should have called render_content_fragments with created forms
        mock_render_fragments.assert_called_once()
        
        # Verify the call was made with proper context including success message
        call_args = mock_render_fragments.call_args
        context = call_args[1]['context']
        self.assertEqual(context['success_message'], "Test success")

    @patch.object(EntityEditResponseRenderer, 'render_content_fragments')
    def test_render_update_fragments_gets_file_attributes_when_forms_provided(self, mock_render_fragments):
        """Test that file attributes are retrieved even when forms are provided."""
        mock_render_fragments.return_value = ('<content>', '<upload>')
        
        # Create forms
        entity_form, _, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(self.entity)
        
        self.renderer.render_update_fragments(
            request=self.request,
            entity=self.entity,
            entity_form=entity_form,
            regular_attributes_formset=regular_attributes_formset
        )
        
        # Should still retrieve file attributes for context
        call_args = mock_render_fragments.call_args
        context = call_args[1]['context']
        self.assertIn('file_attributes', context)

    @patch.object(EntityEditResponseRenderer, 'render_content_fragments')
    def test_render_update_fragments_builds_complete_context(self, mock_render_fragments):
        """Test that fragment rendering builds complete template context."""
        mock_render_fragments.return_value = ('<content>', '<upload>')
        
        self.renderer.render_update_fragments(
            request=self.request,
            entity=self.entity,
            success_message="Success!",
            error_message="Error!",
            has_errors=True
        )
        
        # Verify context was built with all parameters
        call_args = mock_render_fragments.call_args
        context = call_args[1]['context']
        
        self.assertEqual(context['entity'], self.entity)
        self.assertEqual(context['success_message'], "Success!")
        self.assertEqual(context['error_message'], "Error!")
        self.assertTrue(context['has_errors'])


class TestEntityEditResponseRendererSuccessResponse(BaseTestCase):
    """Test success response generation."""

    def setUp(self):
        super().setUp()
        self.renderer = EntityEditResponseRenderer()
        self.entity = EntityAttributeSyntheticData.create_test_entity()
        self.request = Mock(spec=HttpRequest)

    @patch('hi.apps.entity.entity_edit_response_renderer.antinode.response')
    @patch.object(EntityEditResponseRenderer, 'render_update_fragments')
    def test_render_success_response_structure(self, mock_render_fragments, mock_antinode_response):
        """Test that success response has correct structure."""
        mock_render_fragments.return_value = ('<content_html>', '<upload_html>')
        mock_response = Mock()
        mock_antinode_response.return_value = mock_response
        
        result = self.renderer.render_success_response(self.request, self.entity)
        
        # Verify fragment rendering was called with success message
        mock_render_fragments.assert_called_once_with(
            request=self.request,
            entity=self.entity,
            success_message="Changes saved successfully"
        )
        
        # Verify antinode response was called with correct parameters
        mock_antinode_response.assert_called_once_with(
            insert_map={
                DIVID['ATTR_V2_CONTENT']: '<content_html>',
                DIVID['ATTR_V2_UPLOAD_FORM_CONTAINER']: '<upload_html>'
            }
        )
        
        self.assertIs(result, mock_response)

    @patch('hi.apps.entity.entity_edit_response_renderer.antinode.response')
    @patch.object(EntityEditResponseRenderer, 'render_update_fragments')
    def test_render_success_response_uses_correct_divids(self, mock_render_fragments, mock_antinode_response):
        """Test that success response uses correct DIVID constants."""
        mock_render_fragments.return_value = ('<content>', '<upload>')
        
        self.renderer.render_success_response(self.request, self.entity)
        
        # Verify DIVID constants are used correctly
        call_args = mock_antinode_response.call_args
        insert_map = call_args[1]['insert_map']
        
        expected_keys = [DIVID['ATTR_V2_CONTENT'], DIVID['ATTR_V2_UPLOAD_FORM_CONTAINER']]
        for key in expected_keys:
            self.assertIn(key, insert_map)


class TestEntityEditResponseRendererErrorResponse(BaseTestCase):
    """Test error response generation."""

    def setUp(self):
        super().setUp()
        self.renderer = EntityEditResponseRenderer()
        self.entity = EntityAttributeSyntheticData.create_test_entity()
        self.request = Mock(spec=HttpRequest)

    @patch('hi.apps.entity.entity_edit_response_renderer.antinode.response')
    @patch.object(EntityEditResponseRenderer, 'render_update_fragments')
    def test_render_error_response_structure(self, mock_render_fragments, mock_antinode_response):
        """Test that error response has correct structure."""
        mock_render_fragments.return_value = ('<error_content>', '<error_upload>')
        mock_response = Mock()
        mock_antinode_response.return_value = mock_response
        
        # Create forms with errors
        form_data = {'name': ''}  # Invalid data
        entity_form, _, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(
            self.entity, form_data
        )
        
        result = self.renderer.render_error_response(
            self.request, self.entity, entity_form, regular_attributes_formset
        )
        
        # Verify fragment rendering was called with error parameters
        mock_render_fragments.assert_called_once_with(
            request=self.request,
            entity=self.entity,
            entity_form=entity_form,
            regular_attributes_formset=regular_attributes_formset,
            error_message="Please correct the errors below",
            has_errors=True
        )
        
        # Verify antinode response includes status 400
        mock_antinode_response.assert_called_once_with(
            insert_map={
                DIVID['ATTR_V2_CONTENT']: '<error_content>',
                DIVID['ATTR_V2_UPLOAD_FORM_CONTAINER']: '<error_upload>'
            },
            status=400
        )
        
        self.assertIs(result, mock_response)

    @patch('hi.apps.entity.entity_edit_response_renderer.antinode.response')
    @patch.object(EntityEditResponseRenderer, 'render_update_fragments')
    def test_render_error_response_preserves_form_errors(self, mock_render_fragments, mock_antinode_response):
        """Test that error response preserves form validation errors."""
        mock_render_fragments.return_value = ('<content>', '<upload>')
        
        # Create forms with validation errors
        invalid_data = {'name': ''}  # Required field missing
        entity_form, _, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(
            self.entity, invalid_data
        )
        
        # Trigger validation to generate errors
        entity_form.is_valid()
        regular_attributes_formset.is_valid()
        
        self.renderer.render_error_response(
            self.request, self.entity, entity_form, regular_attributes_formset
        )
        
        # Verify forms with errors were passed to fragment rendering
        call_args = mock_render_fragments.call_args
        self.assertIs(call_args[1]['entity_form'], entity_form)
        self.assertIs(call_args[1]['regular_attributes_formset'], regular_attributes_formset)
        self.assertTrue(call_args[1]['has_errors'])

    @patch('hi.apps.entity.entity_edit_response_renderer.antinode.response')
    @patch.object(EntityEditResponseRenderer, 'render_update_fragments')
    def test_render_error_response_400_status_code(self, mock_render_fragments, mock_antinode_response):
        """Test that error response returns 400 status code."""
        mock_render_fragments.return_value = ('<content>', '<upload>')
        
        entity_form, _, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(self.entity)
        
        self.renderer.render_error_response(
            self.request, self.entity, entity_form, regular_attributes_formset
        )
        
        # Verify 400 status code
        call_args = mock_antinode_response.call_args
        self.assertEqual(call_args[1]['status'], 400)


class TestEntityEditResponseRendererIntegration(BaseTestCase):
    """Test integration scenarios with real forms and data."""

    def setUp(self):
        super().setUp()
        self.renderer = EntityEditResponseRenderer()
        self.entity = EntityAttributeSyntheticData.create_entity_with_mixed_attributes()
        self.request = Mock(spec=HttpRequest)

    def test_end_to_end_success_scenario(self):
        """Test complete success scenario with real form data."""
        # Create valid form data
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity, name='Updated Entity Name'
        )
        
        entity_form, _, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(
            self.entity, form_data
        )
        
        # Validate forms
        self.assertTrue(entity_form.is_valid())
        self.assertTrue(regular_attributes_formset.is_valid())
        
        # Test success response generation
        with patch('hi.apps.entity.entity_edit_response_renderer.render_to_string') as mock_render, \
             patch('hi.apps.entity.entity_edit_response_renderer.antinode.response') as mock_response:
            
            mock_render.side_effect = ['<success_content>', '<success_upload>']
            mock_response.return_value = Mock()
            
            result = self.renderer.render_success_response(self.request, self.entity)
            
            # Verify templates were rendered
            self.assertEqual(mock_render.call_count, 2)
            
            # Verify success response was created
            mock_response.assert_called_once()
            
            self.assertIsNotNone(result)

    def test_end_to_end_error_scenario(self):
        """Test complete error scenario with invalid form data."""
        # Create invalid form data
        invalid_data = {'name': ''}  # Required field missing
        
        entity_form, _, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(
            self.entity, invalid_data
        )
        
        # Validate forms (should fail)
        self.assertFalse(entity_form.is_valid())
        
        # Test error response generation
        with patch('hi.apps.entity.entity_edit_response_renderer.render_to_string') as mock_render, \
             patch('hi.apps.entity.entity_edit_response_renderer.antinode.response') as mock_response:
            
            mock_render.side_effect = ['<error_content>', '<error_upload>']
            mock_response.return_value = Mock()
            
            result = self.renderer.render_error_response(
                self.request, self.entity, entity_form, regular_attributes_formset
            )
            
            # Verify error response was created with 400 status
            call_args = mock_response.call_args
            self.assertEqual(call_args[1]['status'], 400)
            
            self.assertIsNotNone(result)

    def test_context_includes_file_attributes_correctly(self):
        """Test that context correctly includes file attributes."""
        # Entity should have file attributes from synthetic data
        file_attributes = self.entity.attributes.filter(
            value_type_str=str(AttributeValueType.FILE)
        )
        self.assertGreater(file_attributes.count(), 0)
        
        # Test context building
        entity_form, file_attrs_qs, regular_attributes_formset = self.renderer.form_handler.create_entity_forms(self.entity)
        
        context = self.renderer.build_template_context(
            entity=self.entity,
            entity_form=entity_form,
            file_attributes=file_attrs_qs,
            regular_attributes_formset=regular_attributes_formset
        )
        
        # Verify file attributes are in context
        context_file_attrs = list(context['file_attributes'])
        self.assertEqual(len(context_file_attrs), file_attributes.count())
        
        # Verify they are the correct file attributes
        for attr in context_file_attrs:
            self.assertEqual(attr.value_type, AttributeValueType.FILE)
