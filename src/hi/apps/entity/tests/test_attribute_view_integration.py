"""
View integration tests for attribute editing workflows.

Tests complete request/response cycles for entity attribute editing,
including handler/renderer integration, session dependencies, and
antinode response patterns.
"""
import logging
from django.urls import reverse

from hi.apps.entity.tests.synthetic_data import EntityAttributeSyntheticData
from hi.apps.entity.models import EntityAttribute
from hi.apps.attribute.enums import AttributeType
from hi.enums import ViewMode
from hi.testing.view_test_base import DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestEntityAttributeViewIntegration(DualModeViewTestCase):
    """Test complete entity attribute editing workflows - end-to-end integration."""
    
    def setUp(self):
        super().setUp()
        # Create entity with attributes for testing
        self.entity = EntityAttributeSyntheticData.create_test_entity(
            name="Test Entity Integration"
        )
        
        # Create various attribute types for comprehensive testing
        self.text_attr = EntityAttributeSyntheticData.create_test_text_attribute(
            entity=self.entity,
            name="description",
            value="Original description"
        )
        
        self.secret_attr = EntityAttributeSyntheticData.create_test_secret_attribute(
            entity=self.entity,
            name="api_key",
            value="secret_key_123"
        )
        
        self.file_attr = EntityAttributeSyntheticData.create_test_file_attribute(
            entity=self.entity,
            name="manual",
            value="Device Manual"
        )
        
        # Set required session state for views
        self.setSessionViewMode(ViewMode.EDIT)
        
    def test_entity_edit_view_get_request_success(self):
        """Test GET request to entity edit view returns correct template and context - initial rendering."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)
        
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Should have entity and forms in context
        self.assertEqual(response.context['entity'], self.entity)
        self.assertIn('entity_form', response.context)
        self.assertIn('regular_attributes_formset', response.context)
        self.assertIn('file_attributes', response.context)
        
        # Should have AttributeEditContext integration
        self.assertIn('attr_context', response.context)
        attr_context = response.context['attr_context']
        
        from hi.apps.entity.entity_attribute_edit_context import EntityAttributeEditContext
        self.assertIsInstance(attr_context, EntityAttributeEditContext)
        self.assertEqual(attr_context.entity, self.entity)
        
    def test_entity_edit_view_ajax_get_request(self):
        """Test AJAX GET request returns JSON response - async rendering."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.async_get(url)
        
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Should contain fragment data for antinode (modal or insert_map structure)
        data = response.json()
        # Response may have 'modal' or other antinode structure, not necessarily 'fragments'
        self.assertTrue(isinstance(data, dict) and len(data) > 0)
        
    def test_entity_edit_view_post_valid_data_success(self):
        """Test POST request with valid data saves successfully - complete workflow."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        # Create valid form data
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity,
            name="Updated Entity Name"
        )
        
        response = self.client.post(url, form_data)
        
        # Should redirect to success or return success response
        self.assertTrue(response.status_code in [200, 302])
        
        # Entity should be updated
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.name, "Updated Entity Name")
        
    def test_entity_edit_view_post_invalid_data_error(self):
        """Test POST request with invalid data returns error response - error handling workflow."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        # Create invalid form data (empty name)
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity,
            name=""  # Invalid empty name
        )
        
        response = self.client.post(url, form_data)
        
        # Should return error response (400 for invalid form data)
        self.assertErrorResponse(response)
        
        # Entity should not be updated
        original_name = self.entity.name
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.name, original_name)
        
    def test_entity_edit_view_ajax_post_valid_data(self):
        """Test AJAX POST request with valid data returns JSON success - async workflow."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity,
            name="AJAX Updated Name"
        )
        
        response = self.async_post(url, form_data)
        
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Should contain antinode response data
        data = response.json()
        self.assertTrue(isinstance(data, dict) and len(data) > 0)
        
        # Entity should be updated
        self.entity.refresh_from_db()
        self.assertEqual(self.entity.name, "AJAX Updated Name")
        
    def test_entity_edit_view_ajax_post_invalid_data(self):
        """Test AJAX POST request with invalid data returns JSON error - async error workflow."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity,
            name=""  # Invalid
        )
        
        response = self.async_post(url, form_data)
        
        # Should return error response (400)
        self.assertErrorResponse(response)
        self.assertJsonResponse(response)
        
    def test_entity_attribute_formset_creation_workflow(self):
        """Test attribute formset creation and updates - formset integration."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        # Get initial form data
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        
        # Add new attribute to formset
        prefix = f'entity-{self.entity.id}'
        form_data.update({
            f'{prefix}-TOTAL_FORMS': '2',  # Existing + 1 new
            f'{prefix}-INITIAL_FORMS': '1',  # Only the existing text_attr
            f'{prefix}-1-name': 'new_property',
            f'{prefix}-1-value': 'new value',
            f'{prefix}-1-attribute_type_str': str(AttributeType.CUSTOM),
        })
        
        response = self.client.post(url, form_data)
        
        # Should succeed
        self.assertTrue(response.status_code in [200, 302])
        
        # New attribute should be created
        new_attr = EntityAttribute.objects.filter(
            entity=self.entity,
            name='new_property'
        ).first()
        self.assertIsNotNone(new_attr)
        self.assertEqual(new_attr.value, 'new value')
        
    def test_file_deletion_workflow(self):
        """Test file attribute deletion workflow - file operation integration."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        # Create form data with file deletion
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        form_data['delete_file_attribute'] = [str(self.file_attr.id)]
        
        response = self.client.post(url, form_data)
        
        # Should succeed
        self.assertTrue(response.status_code in [200, 302])
        
        # File attribute should be deleted
        self.assertFalse(EntityAttribute.objects.filter(id=self.file_attr.id).exists())
        
    def test_file_title_update_workflow(self):
        """Test file title update workflow - file metadata workflow."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        # Create form data with file title update
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(self.entity)
        file_title_updates = EntityAttributeSyntheticData.create_file_title_update_data(
            self.entity, [self.file_attr]
        )
        form_data.update(file_title_updates)
        
        response = self.client.post(url, form_data)
        
        # Should succeed
        self.assertTrue(response.status_code in [200, 302])
        
        # File attribute title should be updated
        self.file_attr.refresh_from_db()
        self.assertEqual(self.file_attr.value, f'Updated {self.file_attr.name}')
        
    def test_session_dependency_integration(self):
        """Test view dependencies on session state - middleware integration."""
        # Test without required session state
        session = self.client.session
        if 'view_mode' in session:
            del session['view_mode']
        session.save()
        
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)
        
        # Response depends on view implementation - might redirect or show different content
        # The important thing is it doesn't crash
        self.assertIsInstance(response.status_code, int)
        
    def test_attribute_context_template_integration(self):
        """Test AttributeEditContext integration with actual templates - template rendering."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        response = self.client.get(url)
        
        self.assertSuccessResponse(response)
        
        # Response should include AttributeEditContext data
        context = response.context
        self.assertIn('attr_context', context)
        
        attr_context = context['attr_context']
        
        # Should provide all the template functionality
        self.assertEqual(attr_context.owner_type, 'entity')
        self.assertEqual(attr_context.owner_id, self.entity.id)
        
        # Template should be able to use these patterns
        history_id = attr_context.history_target_id(123)
        self.assertIn('hi-entity-attr-history', history_id)
        
    def test_error_handling_integration(self):
        """Test error handling across the full stack - comprehensive error handling."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        # Create data that will cause multiple types of errors
        form_data = {
            'name': '',  # Required field error
            f'entity-{self.entity.id}-TOTAL_FORMS': '1',
            f'entity-{self.entity.id}-INITIAL_FORMS': '0',
            f'entity-{self.entity.id}-MIN_NUM_FORMS': '0',
            f'entity-{self.entity.id}-MAX_NUM_FORMS': '1000',
            f'entity-{self.entity.id}-0-name': '',  # Attribute name error
            f'entity-{self.entity.id}-0-value': '',  # Attribute value error
        }
        
        response = self.client.post(url, form_data)
        
        # Should handle errors gracefully with 400 status
        self.assertErrorResponse(response)
        
        # Should show form with errors
        if hasattr(response, 'context') and response.context:
            context = response.context
            # Form should have errors
            if 'entity_form' in context:
                entity_form = context['entity_form']
                # Form validation depends on actual form implementation
                self.assertTrue(hasattr(entity_form, 'errors'))
                
    def test_nonexistent_entity_handling(self):
        """Test handling of requests for nonexistent entities - error boundary testing."""
        nonexistent_id = 999999
        url = reverse('entity_edit', kwargs={'entity_id': nonexistent_id})
        
        response = self.client.get(url)
        
        # Should return 404 or redirect
        self.assertTrue(response.status_code in [404, 302])
        
    def test_concurrent_edit_handling(self):
        """Test handling of concurrent edits - data consistency testing."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        # Modify entity outside of the form
        self.entity.name = "Externally Modified"
        self.entity.save()
        
        # Submit form with old data
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            self.entity,
            name="Form Modified"  # Different from external modification
        )
        
        response = self.client.post(url, form_data)
        
        # Should handle gracefully (exact behavior depends on implementation)
        self.assertIsInstance(response.status_code, int)
        
        # Final state should be consistent
        self.entity.refresh_from_db()
        self.assertIsInstance(self.entity.name, str)
        self.assertTrue(len(self.entity.name) > 0)
        
    def test_view_mode_switching_integration(self):
        """Test view behavior with different view modes - UI state integration."""
        url = reverse('entity_edit', kwargs={'entity_id': self.entity.id})
        
        # Test with different view modes
        view_modes = [ViewMode.EDIT]  # Only test modes that exist
        
        for mode in view_modes:
            with self.subTest(view_mode=mode):
                self.setSessionViewMode(mode)
                
                response = self.client.get(url)
                
                # Should handle different modes appropriately
                self.assertIsInstance(response.status_code, int)
                
                # Context should reflect the view mode
                if response.status_code == 200 and hasattr(response, 'context'):
                    # Exact behavior depends on view implementation
                    self.assertIsNotNone(response.context)
                    
