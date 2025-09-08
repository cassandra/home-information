"""
Abstract base test classes for multi-instance attribute editing framework.

These test classes are designed specifically for the multi-edit architecture used
by the config module, where multiple subsystems are edited simultaneously using
AttributeMultiEditViewMixin and page-level contexts.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from django.test import RequestFactory
from django.http import QueryDict

from hi.apps.attribute.edit_context import AttributePageEditContext, AttributeItemEditContext
from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
from hi.apps.attribute.edit_template_context_builder import AttributeEditTemplateContextBuilder
from hi.apps.attribute.models import AttributeModel


class AttributeMultiFrameworkTestMixin(ABC):
    """Base mixin providing common setup for multi-edit attribute framework testing."""
    
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
    
    @abstractmethod
    def create_owner_instance_list(self, **kwargs) -> List[Any]:
        """Create a list of owner instances (e.g., multiple Subsystems) for multi-edit testing."""
        pass
    
    @abstractmethod
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create an attribute instance for testing."""
        pass
    
    @abstractmethod
    def create_item_edit_context(self, owner) -> AttributeItemEditContext:
        """Create item edit context for testing."""
        pass
    
    @abstractmethod
    def create_page_edit_context(self, owner_list: List[Any]) -> AttributePageEditContext:
        """Create page edit context for multi-edit testing."""
        pass
    
    @abstractmethod
    def create_multi_valid_form_data(self, owner_list: List[Any], **overrides) -> Dict[str, Any]:
        """Create valid form data for multi-edit scenarios."""
        pass
    
    @abstractmethod
    def create_multi_invalid_form_data(self, owner_list: List[Any]) -> Dict[str, Any]:
        """Create invalid form data for multi-edit scenarios."""
        pass


class AttributeMultiEditFormHandlerTestMixin(AttributeMultiFrameworkTestMixin, ABC):
    """Abstract base test mixin for testing AttributeEditFormHandler multi-edit functionality."""
    
    def test_create_multi_edit_form_data_basic_workflow(self):
        """Test basic multi-edit form data creation - core framework functionality."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        handler = AttributeEditFormHandler()
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list
        )
        
        # Should create form data for each owner
        self.assertEqual(len(multi_edit_form_data_list), len(owner_list))
        
        # Each form data should have the required components
        for form_data in multi_edit_form_data_list:
            self.assertIsNotNone(form_data.regular_attributes_formset)
            # Owner forms may or may not exist depending on the module
            
    def test_create_multi_edit_form_data_with_post_data(self):
        """Test multi-edit form data creation with POST data - bound form scenario."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        handler = AttributeEditFormHandler()
        
        post_data = QueryDict(mutable=True)
        form_data_dict = self.create_multi_valid_form_data(owner_list)
        for key, value in form_data_dict.items():
            if isinstance(value, list):
                post_data.setlist(key, value)
            else:
                post_data[key] = value
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list,
            form_data=post_data
        )
        
        # Should create bound forms
        self.assertEqual(len(multi_edit_form_data_list), len(owner_list))
        for form_data in multi_edit_form_data_list:
            self.assertTrue(form_data.regular_attributes_formset.is_bound)
            
    def test_validate_forms_multi_with_valid_data_success(self):
        """Test multi-edit form validation with valid data - success path validation."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        handler = AttributeEditFormHandler()
        
        post_data = QueryDict(mutable=True)
        form_data_dict = self.create_multi_valid_form_data(owner_list)
        for key, value in form_data_dict.items():
            if isinstance(value, list):
                post_data.setlist(key, value)
            else:
                post_data[key] = value
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list,
            form_data=post_data
        )
        
        is_valid = handler.validate_forms_multi(multi_edit_form_data_list=multi_edit_form_data_list)
        self.assertTrue(is_valid)
        
    def test_validate_forms_multi_with_invalid_data_failure(self):
        """Test multi-edit form validation with invalid data - error path validation."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        handler = AttributeEditFormHandler()
        
        post_data = QueryDict(mutable=True)
        form_data_dict = self.create_multi_invalid_form_data(owner_list)
        for key, value in form_data_dict.items():
            if isinstance(value, list):
                post_data.setlist(key, value)
            else:
                post_data[key] = value
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list,
            form_data=post_data
        )
        
        is_valid = handler.validate_forms_multi(multi_edit_form_data_list=multi_edit_form_data_list)
        self.assertFalse(is_valid)
        
    def test_save_forms_multi_database_integration(self):
        """Test multi-edit form saving creates/updates database records - database integration."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        handler = AttributeEditFormHandler()
        
        post_data = QueryDict(mutable=True)
        form_data_dict = self.create_multi_valid_form_data(owner_list)
        for key, value in form_data_dict.items():
            if isinstance(value, list):
                post_data.setlist(key, value)
            else:
                post_data[key] = value
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list,
            form_data=post_data
        )
        
        # Ensure forms are valid before saving
        self.assertTrue(handler.validate_forms_multi(multi_edit_form_data_list=multi_edit_form_data_list))
        
        # Save forms
        request = self.create_hi_request('POST', '/test/', post_data)
        handler.save_forms_multi(
            multi_edit_form_data_list=multi_edit_form_data_list,
            request=request
        )
        
        # Verify data was saved - this will be module-specific
        # Subclasses can add specific assertions


class AttributeMultiEditResponseRendererTestMixin(AttributeMultiFrameworkTestMixin, ABC):
    """Abstract base test mixin for testing AttributeEditResponseRenderer multi-edit functionality."""
    
    def test_render_form_success_response_multi_structure(self):
        """Test multi-edit success response structure - page response format."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        page_context = self.create_page_edit_context(owner_list)
        
        handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list
        )
        
        request = self.create_hi_request('POST', '/test/')
        
        response = renderer.render_form_success_response_multi(
            attr_page_context=page_context,
            multi_edit_form_data_list=multi_edit_form_data_list,
            request=request,
            message=None  # Use default message
        )
        
        # Should return JSON response for HTMX
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Response should contain page-level update structure
        import json
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)
        self.assertTrue(len(data) > 0)
        
    def test_render_form_error_response_multi_with_validation_errors(self):
        """Test multi-edit error response with form validation errors - error handling."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        page_context = self.create_page_edit_context(owner_list)
        
        handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()
        
        post_data = QueryDict(mutable=True)
        form_data_dict = self.create_multi_invalid_form_data(owner_list)
        for key, value in form_data_dict.items():
            if isinstance(value, list):
                post_data.setlist(key, value)
            else:
                post_data[key] = value
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list,
            form_data=post_data
        )
        
        # Ensure forms are invalid
        is_valid = handler.validate_forms_multi(multi_edit_form_data_list=multi_edit_form_data_list)
        self.assertFalse(is_valid)
        
        request = self.create_hi_request('POST', '/test/', post_data)
        
        response = renderer.render_form_error_response_multi(
            attr_page_context=page_context,
            multi_edit_form_data_list=multi_edit_form_data_list,
            request=request
        )
        
        # Should return error response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'application/json')


class AttributeMultiEditTemplateContextBuilderTestMixin(AttributeMultiFrameworkTestMixin, ABC):
    """Abstract base test mixin for testing AttributeEditTemplateContextBuilder multi-edit functionality."""
    
    def test_build_multi_edit_template_context_structure(self):
        """Test multi-edit template context building - context assembly."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        page_context = self.create_page_edit_context(owner_list)
        
        handler = AttributeEditFormHandler()
        builder = AttributeEditTemplateContextBuilder()
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list
        )
        
        template_context = builder.build_response_template_context_multi(
            attr_page_context=page_context,
            multi_edit_form_data_list=multi_edit_form_data_list
        )
        
        # Should contain multi-edit context keys
        self.assertIsInstance(template_context, dict)
        self.assertIn('multi_edit_form_data_list', template_context)
        self.assertIn('attr_page_context', template_context)
        
        # Should have form data for each owner
        multi_edit_data = template_context['multi_edit_form_data_list']
        self.assertEqual(len(multi_edit_data), len(owner_list))


class AttributeMultiEditViewMixinTestMixin(AttributeMultiFrameworkTestMixin, ABC):
    """Abstract base test mixin for testing AttributeMultiEditViewMixin functionality."""
    
    @abstractmethod
    def create_view_instance(self):
        """Create a view instance that uses AttributeMultiEditViewMixin."""
        pass
    
    def test_post_attribute_form_multi_success_workflow(self):
        """Test successful multi-edit form POST handling - view integration success path."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        page_context = self.create_page_edit_context(owner_list)
        
        view = self.create_view_instance()
        
        # Create valid POST data
        post_data = QueryDict(mutable=True)
        form_data_dict = self.create_multi_valid_form_data(owner_list)
        for key, value in form_data_dict.items():
            if isinstance(value, list):
                post_data.setlist(key, value)
            else:
                post_data[key] = value
        
        request = self.create_hi_request('POST', '/test/', post_data)
        
        response = view.post_attribute_form(
            request=request,
            attr_page_context=page_context,
            attr_item_context_list=item_context_list
        )
        
        # Should return success response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
    def test_post_attribute_form_multi_validation_failure(self):
        """Test multi-edit form POST with validation errors - view integration error path."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        page_context = self.create_page_edit_context(owner_list)
        
        view = self.create_view_instance()
        
        # Create invalid POST data
        post_data = QueryDict(mutable=True)
        form_data_dict = self.create_multi_invalid_form_data(owner_list)
        for key, value in form_data_dict.items():
            if isinstance(value, list):
                post_data.setlist(key, value)
            else:
                post_data[key] = value
        
        request = self.create_hi_request('POST', '/test/', post_data)
        
        response = view.post_attribute_form(
            request=request,
            attr_page_context=page_context,
            attr_item_context_list=item_context_list
        )
        
        # Should return error response
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'application/json')
        
