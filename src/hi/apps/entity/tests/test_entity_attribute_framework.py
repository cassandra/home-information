"""
Concrete test implementations for Entity attribute editing framework.

These tests extend the abstract base classes to provide comprehensive testing
of the attribute framework as implemented for Entity models. Tests both the
framework components and Entity-specific customizations.

Following project testing guidelines:
- No mocked objects, use real Entity and EntityAttribute models
- Focus on high-value business logic and integration points
- Use EntityAttributeSyntheticData for test data generation
- Test meaningful Entity-specific edge cases and workflows
"""
import logging

from django.core.files.uploadedfile import SimpleUploadedFile

from hi.apps.attribute.tests.attribute_framework_test_base import (
    AttributeEditFormHandlerTestMixin,
    AttributeEditResponseRendererTestMixin,
    AttributeEditTemplateContextBuilderTestMixin,
    AttributeViewMixinTestMixin,
)
from hi.testing.base_test_case import BaseTestCase
from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.attribute.models import AttributeModel
from hi.apps.entity.entity_attribute_edit_context import EntityAttributeItemEditContext
from hi.apps.entity.models import EntityAttribute
from hi.apps.entity.tests.synthetic_data import EntityAttributeSyntheticData
from hi.apps.entity.views import EntityEditView

logging.disable(logging.CRITICAL)


class EntityAttributeEditFormHandlerTest(AttributeEditFormHandlerTestMixin, BaseTestCase):
    """Test AttributeEditFormHandler with Entity-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Entity instance for testing."""
        return EntityAttributeSyntheticData.create_test_entity(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create EntityAttribute instance for testing."""
        value_type = kwargs.get('value_type_str', str(AttributeValueType.TEXT))
        
        # Use synthetic data method for file attributes to ensure proper file handling
        if value_type == str(AttributeValueType.FILE):
            return EntityAttributeSyntheticData.create_test_file_attribute(entity=owner, **kwargs)
        
        # For non-file attributes, use direct creation
        defaults = {
            'entity': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': value_type,
        }
        defaults.update(kwargs)
        return EntityAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create EntityAttributeItemEditContext for testing."""
        return EntityAttributeItemEditContext(entity=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Entity editing."""
        return EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Entity editing - empty name."""
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(owner)
        form_data['name'] = ''  # Invalid empty name
        return form_data
        
    def test_entity_specific_form_validation_business_logic(self):
        """Test Entity-specific form validation rules - business logic validation."""
        entity = self.create_owner_instance(name="Entity Validation Test")
        context = self.create_item_edit_context(entity)
        handler = self._get_handler()
        
        # Test entity name validation
        invalid_data = self.create_valid_form_data(entity)
        invalid_data['name'] = ''  # Entity requires name
        
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=invalid_data
        )
        
        is_valid = handler.validate_forms(edit_form_data=form_data)
        self.assertFalse(is_valid)
        
        # Entity form should have name error
        if form_data.owner_form:
            self.assertIn('name', form_data.owner_form.errors)
            
    def test_entity_attribute_formset_creation_patterns(self):
        """Test Entity-specific formset creation patterns - Entity formset logic."""
        entity = self.create_owner_instance(name="Formset Test Entity")
        
        # Create mixed attribute types
        self.create_attribute_instance(
            entity, name="text_prop", value="text_value",
            value_type_str=str(AttributeValueType.TEXT)
        )
        self.create_attribute_instance(
            entity, name="file_prop", value="File Title",
            value_type_str=str(AttributeValueType.FILE)
        )
        
        context = self.create_item_edit_context(entity)
        handler = self._get_handler()
        
        form_data = handler.create_edit_form_data(attr_item_context=context)
        
        # File attributes should be excluded from regular formset
        # Check if formset has initial data or get from the formset's queryset  
        if form_data.regular_attributes_formset.initial:
            formset_data = list(form_data.regular_attributes_formset.initial)
            formset_names = [attr.get('name') for attr in formset_data]
        else:
            # Get names from the formset's queryset
            formset_names = [attr.name for attr in form_data.regular_attributes_formset.queryset]
        
        self.assertIn("text_prop", formset_names)
        self.assertNotIn("file_prop", formset_names)
        
        # File attributes should be in separate queryset
        file_attr_names = [attr.name for attr in form_data.file_attributes]
        self.assertIn("file_prop", file_attr_names)
        self.assertNotIn("text_prop", file_attr_names)
        
    def test_entity_file_upload_integration(self):
        """Test Entity file upload handling - Entity file operations."""
        entity = self.create_owner_instance(name="File Upload Entity")
        context = self.create_item_edit_context(entity)
        
        # Entity should support file uploads
        self.assertIsNotNone(context.attribute_upload_form_class)
        self.assertTrue(context.uses_file_uploads)
        
        # Test file creation through form handler
        test_file = SimpleUploadedFile(
            "entity_test.txt",
            b"Entity test file content",
            content_type="text/plain"
        )
        
        _ = self.create_hi_request(
            method='POST',
            path='/entity/test/',
            data={
                'name': 'entity_document',
                'value': 'Entity Test Document'
            },
            files={'file_value': test_file}
        )
        
        # Should handle file upload processing
        
        # File handling is tested at the view level, but we can test the context setup
        self.assertIsNotNone(context.file_upload_url)
        
    def _get_handler(self):
        """Get handler instance for testing."""
        from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
        return AttributeEditFormHandler()


class EntityAttributeEditResponseRendererTest(AttributeEditResponseRendererTestMixin, BaseTestCase):
    """Test AttributeEditResponseRenderer with Entity-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Entity instance for testing."""
        return EntityAttributeSyntheticData.create_test_entity(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create EntityAttribute instance for testing."""
        defaults = {
            'entity': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return EntityAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create EntityAttributeItemEditContext for testing."""
        return EntityAttributeItemEditContext(entity=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Entity editing."""
        return EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Entity editing."""
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(owner)
        form_data['name'] = ''  # Invalid empty name
        return form_data
        
    def test_entity_specific_response_content(self):
        """Test Entity-specific response content and templates - Entity response handling."""
        entity = self.create_owner_instance(name="Response Test Entity")
        context = self.create_item_edit_context(entity)
        renderer = self._get_renderer()
        
        request = self.create_hi_request('POST', '/entity/test/')
        
        response = renderer.render_form_success_response(
            attr_item_context=context,
            request=request,
            message=None  # Use default message
        )
        
        # Should use Entity-specific template context
        self.assertEqual(response.status_code, 200)
        
        # Verify response contains Entity-specific data
        import json
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)
        
    def _get_renderer(self):
        """Get renderer instance for testing."""
        from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
        return AttributeEditResponseRenderer()
    

class EntityAttributeEditTemplateContextBuilderTest(
        AttributeEditTemplateContextBuilderTestMixin,
        BaseTestCase ):
    """Test AttributeEditTemplateContextBuilder with Entity-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Entity instance for testing."""
        return EntityAttributeSyntheticData.create_test_entity(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create EntityAttribute instance for testing."""
        defaults = {
            'entity': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return EntityAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create EntityAttributeItemEditContext for testing."""
        return EntityAttributeItemEditContext(entity=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Entity editing."""
        return EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Entity editing."""
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(owner)
        form_data['name'] = ''
        return form_data
        
    def test_entity_specific_template_context_keys(self):
        """Test Entity-specific template context keys - Entity template integration."""
        entity = self.create_owner_instance(name="Template Context Entity")
        context = self.create_item_edit_context(entity)
        builder = self._get_builder()
        
        template_context = builder.build_initial_template_context(
            attr_item_context=context
        )
        
        # Should include Entity-specific keys
        self.assertIn('entity', template_context)
        self.assertIs(template_context['entity'], entity)
        self.assertIn('entity_form', template_context)
        
        # Should include generic keys
        self.assertIn('owner', template_context)
        self.assertIn('attr_item_context', template_context)
        
    def test_entity_form_error_context_assembly(self):
        """Test Entity form error context assembly - Entity error handling."""
        entity = self.create_owner_instance(name="Error Context Entity")
        context = self.create_item_edit_context(entity)
        builder = self._get_builder()
        handler = self._get_handler()
        
        # Create form with errors
        invalid_data = self.create_invalid_form_data(entity)
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=invalid_data
        )
        
        # Trigger validation to create errors
        handler.validate_forms(edit_form_data=form_data)
        
        template_context = builder.build_response_template_context(
            attr_item_context=context,
            edit_form_data=form_data,
            error_message="Entity validation failed",
            has_errors=True
        )
        
        # Should properly handle Entity form errors
        self.assertTrue(template_context.get('has_errors', False))
        self.assertIn('error_message', template_context)
        
        # Entity form should be available with errors
        if template_context.get('owner_form'):
            entity_form = template_context['owner_form']
            self.assertTrue(hasattr(entity_form, 'errors'))
            
    def _get_builder(self):
        """Get builder instance for testing."""
        from hi.apps.attribute.edit_template_context_builder import AttributeEditTemplateContextBuilder
        return AttributeEditTemplateContextBuilder()
        
    def _get_handler(self):
        """Get handler instance for testing."""
        from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
        return AttributeEditFormHandler()


class EntityAttributeViewMixinTest(AttributeViewMixinTestMixin, BaseTestCase):
    """Test AttributeEditViewMixin with Entity-specific view implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Entity instance for testing."""
        return EntityAttributeSyntheticData.create_test_entity(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create EntityAttribute instance for testing."""
        defaults = {
            'entity': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return EntityAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create EntityAttributeItemEditContext for testing."""
        return EntityAttributeItemEditContext(entity=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Entity editing."""
        return EntityAttributeSyntheticData.create_form_data_for_entity_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Entity editing."""
        form_data = EntityAttributeSyntheticData.create_form_data_for_entity_edit(owner)
        form_data['name'] = ''
        return form_data
        
    def create_test_view_instance(self):
        """Create EntityEditView instance for testing."""
        return EntityEditView()
        
    def test_entity_edit_view_integration_workflow(self):
        """Test complete EntityEditView integration - Entity view integration."""
        entity = self.create_owner_instance(name="View Integration Entity")
        
        # Create attributes for comprehensive testing
        self.create_attribute_instance(
            entity, name="description", value="Original description"
        )
        
        view = self.create_test_view_instance()
        context = self.create_item_edit_context(entity)
        
        # Test GET request (initial template context)
        _ = self.create_hi_request('GET', f'/entity/{entity.id}/edit/')
        
        template_context = view.create_initial_template_context(
            attr_item_context=context
        )
        
        # Should provide complete Entity editing context
        self.assertIn('entity', template_context)
        self.assertIn('entity_form', template_context)
        self.assertIn('regular_attributes_formset', template_context)
        
    def test_entity_attribute_history_view_integration(self):
        """Test Entity attribute history integration - Entity history functionality."""
        entity = self.create_owner_instance(name="History Integration Entity")
        attribute = self.create_attribute_instance(
            entity, name="history_attr", value="current_value"
        )
        
        view = self.create_test_view_instance()
        context = self.create_item_edit_context(entity)
        
        request = self.create_hi_request('GET', f'/entity/{entity.id}/attr/{attribute.id}/history/')
        
        response = view.get_history(
            request=request,
            attribute=attribute,
            attr_item_context=context
        )
        
        # Should handle Entity attribute history
        self.assertEqual(response.status_code, 200)
        
    def test_entity_concurrent_editing_workflow(self):
        """Test Entity concurrent editing scenarios - Entity concurrency handling."""
        entity = self.create_owner_instance(name="Concurrent Test Entity")
        self.create_attribute_instance(
            entity, name="concurrent_attr", value="original"
        )
        
        view = self.create_test_view_instance()
        context = self.create_item_edit_context(entity)
        
        # Simulate form submission while entity is modified externally
        form_data = self.create_valid_form_data(entity, name="Form Update")
        
        # External modification
        entity.name = "External Update"
        entity.save()
        
        request = self.create_hi_request('POST', f'/entity/{entity.id}/edit/', form_data)
        
        response = view.post_attribute_form(
            request=request,
            attr_item_context=context
        )
        
        # Should handle gracefully (may succeed or fail depending on validation)
        self.assertIn(response.status_code, [200, 400])
        
    
