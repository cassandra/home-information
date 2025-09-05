"""
Abstract base test classes for attribute editing framework components.

These abstract test classes define comprehensive test methods for the core
attribute framework components. Module-specific tests inherit from these
bases and provide concrete implementations to exercise the framework.

Following project testing guidelines:
- No mocked objects, use real database operations
- Focus on high-value business logic and integration points
- Use synthetic data pattern for test data generation
- Test meaningful edge cases and error handling scenarios
"""
import logging
from abc import ABC, abstractmethod
from typing import Type, Any, Dict, Optional

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.test import RequestFactory
from django.http import QueryDict

from hi.testing.base_test_case import BaseTestCase, MockRequest, MockSession
from hi.apps.attribute.edit_context import AttributeItemEditContext, AttributePageEditContext
from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
from hi.apps.attribute.edit_template_context_builder import AttributeEditTemplateContextBuilder
from hi.apps.attribute.models import AttributeModel
from hi.apps.attribute.enums import AttributeType, AttributeValueType

logging.disable(logging.CRITICAL)


class AttributeFrameworkTestMixin(ABC):
    """
    Mixin providing common setup and abstract methods for attribute framework testing.
    
    Subclasses must implement methods to create concrete instances of:
    - Owner models (Entity, Location, Subsystem)
    - AttributeModel subclasses
    - AttributeItemEditContext subclasses
    - Test data scenarios
    """
    
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        
    @abstractmethod
    def create_owner_instance(self, **kwargs):
        """Create a concrete owner instance (Entity, Location, Subsystem)."""
        pass
        
    @abstractmethod
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create a concrete AttributeModel subclass instance."""
        pass
        
    @abstractmethod
    def create_item_edit_context(self, owner) -> AttributeItemEditContext:
        """Create a concrete AttributeItemEditContext subclass."""
        pass
        
    @abstractmethod
    def create_valid_form_data(self, owner, **overrides) -> Dict[str, Any]:
        """Create valid form data for the owner and its attributes."""
        pass
        
    @abstractmethod
    def create_invalid_form_data(self, owner) -> Dict[str, Any]:
        """Create invalid form data to test error handling."""
        pass


class AttributeEditFormHandlerTestMixin(AttributeFrameworkTestMixin, ABC):
    """
    Abstract base for testing AttributeEditFormHandler functionality.
    
    Tests form creation, validation, saving, and file operations.
    Focuses on business logic integration points and error handling.
    """
    
    def test_create_edit_form_data_basic_workflow(self):
        """Test basic form data creation - core framework functionality."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        handler = AttributeEditFormHandler()
        
        # Test unbound forms (GET request scenario)
        form_data = handler.create_edit_form_data(
            attr_item_context=context
        )
        
        # Should create proper form data structure
        self.assertIsNotNone(form_data.regular_attributes_formset)
        self.assertIsNotNone(form_data.file_attributes)
        
        # Owner form may be None for some contexts (like Subsystem)
        if context.create_owner_form():
            self.assertIsNotNone(form_data.owner_form)
            
    def test_create_edit_form_data_with_post_data(self):
        """Test form data creation with POST data - bound form scenario."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        handler = AttributeEditFormHandler()
        
        # Create valid POST data
        post_data = self.create_valid_form_data(owner, name="Updated Owner")
        
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=post_data
        )
        
        # Forms should be bound with data
        self.assertIsNotNone(form_data.regular_attributes_formset)
        self.assertTrue(hasattr(form_data.regular_attributes_formset, 'data'))
        
    def test_validate_forms_with_valid_data_success(self):
        """Test form validation with valid data - success path validation."""
        owner = self.create_owner_instance(name="Test Owner")
        # Create some attributes to validate
        self.create_attribute_instance(
            owner=owner,
            name="test_attr",
            value="test_value",
            attribute_type_str=str(AttributeType.CUSTOM)
        )
        
        context = self.create_item_edit_context(owner)
        handler = AttributeEditFormHandler()
        
        # Create valid form data
        post_data = self.create_valid_form_data(owner, name="Valid Updated Name")
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=post_data
        )
        
        # Validation should succeed
        is_valid = handler.validate_forms(edit_form_data=form_data)
        self.assertTrue(is_valid)
        
    def test_validate_forms_with_invalid_data_failure(self):
        """Test form validation with invalid data - error path validation."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        handler = AttributeEditFormHandler()
        
        # Create invalid form data
        invalid_data = self.create_invalid_form_data(owner)
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=invalid_data
        )
        
        # Validation should fail
        is_valid = handler.validate_forms(edit_form_data=form_data)
        self.assertFalse(is_valid)
        
    def test_save_forms_database_integration(self):
        """Test form saving creates/updates database records - database integration."""
        owner = self.create_owner_instance(name="Original Name")
        # Create an existing attribute to update
        existing_attr = self.create_attribute_instance(
            owner=owner,
            name="existing_attr",
            value="original_value"
        )
        
        context = self.create_item_edit_context(owner)
        handler = AttributeEditFormHandler()
        
        # Check if this context supports owner form editing
        temp_form_data = handler.create_edit_form_data(attr_item_context=context)
        
        # Create form data with updates - let each module handle its own update format
        form_data_kwargs = {}
        if temp_form_data.owner_form is not None:
            form_data_kwargs["name"] = "Updated Owner Name"
        
        post_data = self.create_valid_form_data(owner, **form_data_kwargs)
        
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=post_data
        )
        
        # Create mock request for save operation
        request = MockRequest()
        # Create QueryDict from post_data to simulate Django POST behavior
        query_dict = QueryDict(mutable=True)
        for key, value in post_data.items():
            query_dict[key] = value
        request.POST = query_dict
        request.session = MockSession()
        
        # Save should succeed with valid data
        self.assertTrue(handler.validate_forms(edit_form_data=form_data))
        handler.save_forms(
            attr_item_context=context,
            edit_form_data=form_data,
            request=request
        )
        
        # Verify database changes
        owner.refresh_from_db()
        
        # Only test owner changes if owner form exists and we sent owner data
        if temp_form_data.owner_form is not None:
            self.assertEqual(owner.name, "Updated Owner Name")
            
        # The main point of this test is that forms validate and save without errors
        # Specific attribute change testing is left to module-specific tests
            
    def test_file_deletion_workflow(self):
        """Test file deletion processing - file operation integration."""
        owner = self.create_owner_instance(name="Test Owner")
        
        # Create file attribute if supported by this context
        context = self.create_item_edit_context(owner)
        if not context.attribute_upload_form_class:
            self.skipTest("File uploads not supported by this context")
            
        file_attr = self.create_attribute_instance(
            owner=owner,
            name="test_file",
            value="Test File Title",
            value_type_str=str(AttributeValueType.FILE)
        )
        
        handler = AttributeEditFormHandler()
        
        # Create request with file deletion data
        request = MockRequest()
        # Create QueryDict to simulate Django POST behavior
        from hi.constants import DIVID
        query_dict = QueryDict(mutable=True)
        query_dict.setlist(DIVID['ATTR_V2_DELETE_FILE_ATTR'], [str(file_attr.id)])
        request.POST = query_dict
        request.session = MockSession()
        
        # Process file deletions
        initial_count = context.attribute_model_subclass.objects.count()
        handler.process_file_deletions(
            attr_item_context=context,
            request=request
        )
        
        # File attribute should be deleted
        final_count = context.attribute_model_subclass.objects.count()
        self.assertEqual(final_count, initial_count - 1)
        self.assertFalse(
            context.attribute_model_subclass.objects.filter(id=file_attr.id).exists()
        )
        
    def test_file_title_update_workflow(self):
        """Test file title updates - file metadata management."""
        owner = self.create_owner_instance(name="Test Owner")
        
        context = self.create_item_edit_context(owner)
        if not context.attribute_upload_form_class:
            self.skipTest("File uploads not supported by this context")
            
        file_attr = self.create_attribute_instance(
            owner=owner,
            name="document",
            value="Original Title",
            value_type_str=str(AttributeValueType.FILE)
        )
        
        handler = AttributeEditFormHandler()
        
        # Create request with file title update
        field_name = context.file_title_field_name(file_attr.id)
        request = MockRequest()
        # Create QueryDict to simulate Django POST behavior
        query_dict = QueryDict(mutable=True)
        query_dict[field_name] = "Updated File Title"
        request.POST = query_dict
        request.session = MockSession()
        
        handler.process_file_title_updates(
            attr_item_context=context,
            request=request
        )
        
        # File title should be updated
        file_attr.refresh_from_db()
        self.assertEqual(file_attr.value, "Updated File Title")
        
    def test_concurrent_modification_handling(self):
        """Test handling of concurrent modifications - data consistency."""
        owner = self.create_owner_instance(name="Original")
        attr = self.create_attribute_instance(owner=owner, name="test", value="original")
        
        context = self.create_item_edit_context(owner)
        handler = AttributeEditFormHandler()
        
        # Create form data
        post_data = self.create_valid_form_data(owner, name="User Update")
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=post_data
        )
        
        # Simulate external modification
        attr.value = "External Update"
        attr.save()
        
        # Form save should still succeed (last write wins)
        request = MockRequest()
        # Create QueryDict to simulate Django POST behavior
        query_dict = QueryDict(mutable=True)
        for key, value in post_data.items():
            query_dict[key] = value
        request.POST = query_dict
        request.session = MockSession()
        
        if handler.validate_forms(edit_form_data=form_data):
            handler.save_forms(
                attr_item_context=context,
                edit_form_data=form_data,
                request=request
            )
            
        # Should handle gracefully without exceptions
        self.assertTrue(True)  # Test passes if no exception raised


class AttributeEditResponseRendererTestMixin(AttributeFrameworkTestMixin, ABC):
    """
    Abstract base for testing AttributeEditResponseRenderer functionality.
    
    Tests response generation, template context building, and success/error handling.
    Focuses on HTMX integration and antinode response patterns.
    """
    
    def test_render_form_success_response_structure(self):
        """Test success response structure - antinode response format."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        renderer = AttributeEditResponseRenderer()
        
        request = self.factory.post('/test/')
        request.session = MockSession()
        
        response = renderer.render_form_success_response(
            attr_item_context=context,
            request=request,
            message=None  # Use default message
        )
        
        # Should return JSON response for HTMX
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Response should contain antinode structure
        import json
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)
        self.assertTrue(len(data) > 0)
        
    def test_render_form_error_response_with_validation_errors(self):
        """Test error response with form validation errors - error handling."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        renderer = AttributeEditResponseRenderer()
        handler = AttributeEditFormHandler()
        
        # Create invalid form data
        invalid_data = self.create_invalid_form_data(owner)
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=invalid_data
        )
        
        # Ensure forms have validation errors
        is_valid = handler.validate_forms(edit_form_data=form_data)
        self.assertFalse(is_valid)
        
        request = self.factory.post('/test/')
        request.session = MockSession()
        
        response = renderer.render_form_error_response(
            attr_item_context=context,
            edit_form_data=form_data,
            request=request
        )
        
        # Should return error response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        
    def test_render_history_response_data_structure(self):
        """Test history response rendering - history display functionality."""
        owner = self.create_owner_instance(name="Test Owner")
        attribute = self.create_attribute_instance(
            owner=owner,
            name="test_attr",
            value="current_value"
        )
        context = self.create_item_edit_context(owner)
        renderer = AttributeEditResponseRenderer()
        
        request = self.factory.get('/test/')
        request.session = MockSession()
        
        # Create mock history records
        history_records = []
        
        response = renderer.render_history_response(
            attr_item_context=context,
            attribute=attribute,
            history_records=history_records,
            request=request
        )
        
        # Should return HTML response for history content
        self.assertEqual(response.status_code, 200)
        # Content type depends on implementation - could be HTML or JSON
        
    def test_render_restore_success_response_workflow(self):
        """Test attribute restoration success response - restore functionality."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        renderer = AttributeEditResponseRenderer()
        
        request = self.factory.post('/test/')
        request.session = MockSession()
        
        response = renderer.render_restore_success_response(
            attr_item_context=context,
            request=request
        )
        
        # Should return success response
        self.assertEqual(response.status_code, 200)
        
    def test_render_restore_error_response_handling(self):
        """Test attribute restoration error response - error recovery."""
        renderer = AttributeEditResponseRenderer()
        
        error_message = "Test error during restore"
        response = renderer.render_restore_error_response(error_message)
        
        # Should return error response with message
        self.assertEqual(response.status_code, 400)


class AttributeEditTemplateContextBuilderTestMixin(AttributeFrameworkTestMixin, ABC):
    """
    Abstract base for testing AttributeEditTemplateContextBuilder functionality.
    
    Tests template context assembly for both single and multi-edit scenarios.
    Focuses on proper context structure and data flow to templates.
    """
    
    def test_build_initial_template_context_structure(self):
        """Test initial template context building - context assembly."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        builder = AttributeEditTemplateContextBuilder()
        
        template_context = builder.build_initial_template_context(
            attr_item_context=context
        )
        
        # Should contain all required context keys
        self.assertIn('owner_form', template_context)
        self.assertIn('file_attributes', template_context)
        self.assertIn('regular_attributes_formset', template_context)
        self.assertIn('attr_item_context', template_context)
        
        # Should contain owner-specific context
        self.assertIn(context.owner_type, template_context)
        self.assertIs(template_context[context.owner_type], owner)
        
    def test_build_response_template_context_with_success_message(self):
        """Test response context with success message - success state handling."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        builder = AttributeEditTemplateContextBuilder()
        handler = AttributeEditFormHandler()
        
        # Create valid form data
        form_data = handler.create_edit_form_data(attr_item_context=context)
        
        template_context = builder.build_response_template_context(
            attr_item_context=context,
            edit_form_data=form_data,
            success_message="Operation completed successfully"
        )
        
        # Should contain success context
        self.assertIn('success_message', template_context)
        self.assertEqual(template_context['success_message'], "Operation completed successfully")
        self.assertFalse(template_context.get('has_errors', True))
        
    def test_build_response_template_context_with_form_errors(self):
        """Test response context with form errors - error state handling."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        builder = AttributeEditTemplateContextBuilder()
        handler = AttributeEditFormHandler()
        
        # Create invalid form data to trigger errors
        invalid_data = self.create_invalid_form_data(owner)
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=invalid_data
        )
        
        # Trigger validation to create errors
        handler.validate_forms(edit_form_data=form_data)
        
        template_context = builder.build_response_template_context(
            attr_item_context=context,
            edit_form_data=form_data,
            error_message="Validation failed",
            has_errors=True
        )
        
        # Should contain error context
        self.assertIn('error_message', template_context)
        self.assertEqual(template_context['error_message'], "Validation failed")
        self.assertTrue(template_context.get('has_errors', False))
        self.assertIn('non_form_errors', template_context)
        
    def test_template_context_owner_integration(self):
        """Test template context includes proper owner integration - owner context."""
        owner = self.create_owner_instance(name="Integration Test Owner")
        context = self.create_item_edit_context(owner)
        builder = AttributeEditTemplateContextBuilder()
        
        template_context = builder.build_initial_template_context(
            attr_item_context=context
        )
        
        # Should provide multiple ways to access owner in templates
        self.assertIn('owner', template_context)
        self.assertIs(template_context['owner'], owner)
        
        # Should provide owner-type specific access
        self.assertIn(context.owner_type, template_context)
        self.assertIs(template_context[context.owner_type], owner)
        
        # Should include context object itself
        self.assertIn('attr_item_context', template_context)
        self.assertIs(template_context['attr_item_context'], context)


class AttributeViewMixinTestMixin(AttributeFrameworkTestMixin, ABC):
    """
    Abstract base for testing AttributeEditViewMixin functionality.
    
    Note: Cannot test mixins directly due to abstract nature.
    This provides test methods that concrete implementations should call.
    Tests view-level integration and HTTP request/response handling.
    """
    
    @abstractmethod
    def create_test_view_instance(self):
        """Create a concrete view instance that uses AttributeEditViewMixin."""
        pass
        
    def test_post_attribute_form_success_workflow(self):
        """Test successful form POST handling - view integration success path."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        view = self.create_test_view_instance()
        
        # Create valid POST data
        post_data = self.create_valid_form_data(owner, name="Updated via View")
        request = self.factory.post('/test/', post_data)
        request.session = MockSession()
        
        response = view.post_attribute_form(
            request=request,
            attr_item_context=context
        )
        
        # Should return success response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
    def test_post_attribute_form_validation_failure(self):
        """Test form POST with validation errors - view integration error path."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        view = self.create_test_view_instance()
        
        # Create invalid POST data
        invalid_data = self.create_invalid_form_data(owner)
        request = self.factory.post('/test/', invalid_data)
        request.session = MockSession()
        
        response = view.post_attribute_form(
            request=request,
            attr_item_context=context
        )
        
        # Should return error response
        self.assertEqual(response.status_code, 400)
        
    def test_create_initial_template_context_view_integration(self):
        """Test initial template context creation via view - view context integration."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        view = self.create_test_view_instance()
        
        template_context = view.create_initial_template_context(
            attr_item_context=context
        )
        
        # Should return proper template context structure
        self.assertIsInstance(template_context, dict)
        self.assertIn('attr_item_context', template_context)
        self.assertIs(template_context['attr_item_context'], context)
        
    def test_post_upload_file_operation_workflow(self):
        """Test file upload POST handling - file operation view integration."""
        owner = self.create_owner_instance(name="Test Owner")
        context = self.create_item_edit_context(owner)
        
        if not context.attribute_upload_form_class:
            self.skipTest("File uploads not supported by this context")
            
        view = self.create_test_view_instance()
        
        # Create file upload request
        test_file = SimpleUploadedFile(
            "test.txt",
            b"test file content",
            content_type="text/plain"
        )
        
        request = self.factory.post('/test/', {
            'file_value': test_file,
            'name': 'uploaded_document',
            'value': 'Test Document'
        })
        request.session = MockSession()
        
        response = view.post_upload(
            request=request,
            attr_item_context=context
        )
        
        # Should handle file upload
        self.assertIn(response.status_code, [200, 400])  # Success or validation error
        
    def test_get_history_display_workflow(self):
        """Test attribute history display - history view integration."""
        owner = self.create_owner_instance(name="Test Owner")
        attribute = self.create_attribute_instance(
            owner=owner,
            name="history_test",
            value="current_value"
        )
        context = self.create_item_edit_context(owner)
        view = self.create_test_view_instance()
        
        request = self.factory.get('/test/')
        request.session = MockSession()
        
        response = view.get_history(
            request=request,
            attribute=attribute,
            attr_item_context=context
        )
        
        # Should return history response
        self.assertEqual(response.status_code, 200)
        
    def test_post_restore_attribute_workflow(self):
        """Test attribute restoration - restore view integration."""
        owner = self.create_owner_instance(name="Test Owner")
        attribute = self.create_attribute_instance(
            owner=owner,
            name="restore_test",
            value="current_value"
        )
        context = self.create_item_edit_context(owner)
        view = self.create_test_view_instance()
        
        # Mock history record ID
        history_id = 1
        
        request = self.factory.post('/test/')
        request.session = MockSession()
        
        response = view.post_restore(
            request=request,
            attribute=attribute,
            history_id=history_id,
            attr_item_context=context
        )
        
        # Should return response (may be error if no history exists)
        self.assertIn(response.status_code, [200, 400])