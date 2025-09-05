"""
Concrete test implementations for Subsystem attribute editing framework.

These tests extend the abstract base classes to provide comprehensive testing
of the attribute framework as implemented for Subsystem models. Tests both the
framework components and Subsystem-specific customizations, including the unique
multi-formset scenario.

Following project testing guidelines:
- No mocked objects, use real Subsystem and SubsystemAttribute models
- Focus on high-value business logic and integration points
- Use SubsystemAttributeSyntheticData for test data generation
- Test meaningful Subsystem-specific edge cases and multi-editing workflows
"""
import logging
from typing import Any, Dict, List

from django.core.files.uploadedfile import SimpleUploadedFile

from hi.testing.attribute_framework_test_base import (
    AttributeEditFormHandlerTestMixin,
    AttributeEditResponseRendererTestMixin,
    AttributeEditTemplateContextBuilderTestMixin,
)
from hi.testing.base_test_case import BaseTestCase
from hi.apps.attribute.view_mixins import AttributeMultiEditViewMixin
from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.attribute.models import AttributeModel
from hi.apps.attribute.edit_context import AttributePageEditContext
from hi.apps.config.subsystem_attribute_edit_context import (
    SubsystemAttributeItemEditContext,
    SubsystemAttributePageEditContext
)
from hi.apps.config.models import Subsystem, SubsystemAttribute
from hi.apps.config.tests.synthetic_data import SubsystemAttributeSyntheticData

logging.disable(logging.CRITICAL)


class SubsystemAttributeEditFormHandlerTest(AttributeEditFormHandlerTestMixin, BaseTestCase):
    """Test AttributeEditFormHandler with Subsystem-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Subsystem instance for testing."""
        return SubsystemAttributeSyntheticData.create_test_subsystem(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create SubsystemAttribute instance for testing."""
        defaults = {
            'subsystem': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.PREDEFINED),  # Subsystems use SYSTEM attributes
            'value_type_str': kwargs.pop('value_type_str', str(AttributeValueType.TEXT)),
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create SubsystemAttributeItemEditContext for testing."""
        return SubsystemAttributeItemEditContext(subsystem=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Subsystem editing."""
        return SubsystemAttributeSyntheticData.create_form_data_for_single_subsystem_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Subsystem editing - empty attribute name."""
        form_data = SubsystemAttributeSyntheticData.create_form_data_for_single_subsystem_edit(owner)
        # Make first attribute have invalid empty name on a non-empty form
        # This ensures it's treated as a form that should be validated
        prefix = f'subsystem-{owner.id}'
        form_data[f'{prefix}-0-name'] = ''
        # Keep other fields to ensure form is not treated as empty
        form_data[f'{prefix}-0-value'] = 'some value'
        return form_data
        
    def test_subsystem_no_owner_form_behavior(self):
        """Test Subsystem-specific no owner form behavior - Subsystem owner form logic."""
        subsystem = self.create_owner_instance(name="No Owner Form Test")
        context = self.create_item_edit_context(subsystem)
        handler = self._get_handler()
        
        form_data = handler.create_edit_form_data(attr_item_context=context)
        
        # Subsystem should not have owner form (no editable properties on Subsystem itself)
        self.assertIsNone(form_data.owner_form)
        self.assertIsNotNone(form_data.regular_attributes_formset)
        
    def test_subsystem_system_attribute_validation(self):
        """Test Subsystem SYSTEM attribute type validation - Subsystem attribute validation."""
        subsystem = self.create_owner_instance(name="System Attribute Test")
        
        # Create SYSTEM type attribute
        system_attr = self.create_attribute_instance(
            subsystem, 
            name="system_config", 
            value="config_value",
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        context = self.create_item_edit_context(subsystem)
        handler = self._get_handler()
        
        # Test valid system attribute data
        valid_data = self.create_valid_form_data(subsystem)
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=valid_data
        )
        
        is_valid = handler.validate_forms(edit_form_data=form_data)
        self.assertTrue(is_valid)
        
    def test_subsystem_attribute_formset_patterns(self):
        """Test Subsystem-specific formset patterns - Subsystem formset logic."""
        subsystem = self.create_owner_instance(name="Formset Test Subsystem")
        
        # Create system configuration attributes
        config_attr = self.create_attribute_instance(
            subsystem, name="endpoint", value="https://api.system.com",
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        secret_attr = self.create_attribute_instance(
            subsystem, name="secret_key", value="secret123",
            value_type_str=str(AttributeValueType.SECRET),
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        context = self.create_item_edit_context(subsystem)
        handler = self._get_handler()
        
        form_data = handler.create_edit_form_data(attr_item_context=context)
        
        # All attributes should be in regular formset (no file separation for subsystems)
        # Check if formset has initial data or get from the formset's queryset  
        if form_data.regular_attributes_formset.initial:
            formset_data = list(form_data.regular_attributes_formset.initial)
            formset_names = [attr.get('name') for attr in formset_data]
        else:
            # Get names from the formset's queryset
            formset_names = [attr.name for attr in form_data.regular_attributes_formset.queryset]
        
        self.assertIn("endpoint", formset_names)
        self.assertIn("secret_key", formset_names)
        
        # No file attributes expected for subsystems
        self.assertEqual(form_data.file_attributes.count(), 0)
        
    def test_subsystem_no_file_upload_support(self):
        """Test Subsystem file upload handling - Subsystem file operations."""
        subsystem = self.create_owner_instance(name="No File Upload Subsystem")
        context = self.create_item_edit_context(subsystem)
        
        # Subsystem should not support file uploads
        self.assertIsNone(context.attribute_upload_form_class)
        self.assertFalse(context.uses_file_uploads)
        self.assertIsNone(context.file_upload_url)
        
    def test_subsystem_multi_formset_workflow(self):
        """Test Subsystem multi-formset workflow - unique to config module."""
        # Create multiple subsystems for multi-editing scenario
        subsystem_list = SubsystemAttributeSyntheticData.create_multiple_subsystems_scenario()
        
        handler = self._get_handler()
        
        # Create multi-edit form data
        multi_form_data = SubsystemAttributeSyntheticData.create_form_data_for_subsystem_multi_edit(
            subsystem_list
        )
        
        # Test multi-edit form data creation (would be used by multi-edit views)
        item_context_list = [
            SubsystemAttributeItemEditContext(subsystem=sub) for sub in subsystem_list
        ]
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list
        )
        
        # Should create form data for each subsystem
        self.assertEqual(len(multi_edit_form_data_list), len(subsystem_list))
        
        # Each should have appropriate structure
        for form_data in multi_edit_form_data_list:
            self.assertIsNotNone(form_data.regular_attributes_formset)
            self.assertIsNone(form_data.owner_form)  # No owner forms for subsystems
            
    def test_subsystem_system_level_configuration(self):
        """Test system-level configuration scenarios - Subsystem system config."""
        subsystem = SubsystemAttributeSyntheticData.create_system_configuration_scenario()
        context = self.create_item_edit_context(subsystem)
        handler = self._get_handler()
        
        # Test form creation with system configuration
        form_data = handler.create_edit_form_data(attr_item_context=context)
        
        # Should handle system attributes properly
        self.assertIsNotNone(form_data.regular_attributes_formset)
        
        # Test validation of system configuration
        valid_data = self.create_valid_form_data(subsystem)
        bound_form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=valid_data
        )
        
        is_valid = handler.validate_forms(edit_form_data=bound_form_data)
        self.assertTrue(is_valid)
        
    def _get_handler(self):
        """Get handler instance for testing."""
        from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
        return AttributeEditFormHandler()


class SubsystemAttributeEditResponseRendererTest(AttributeEditResponseRendererTestMixin, BaseTestCase):
    """Test AttributeEditResponseRenderer with Subsystem-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Subsystem instance for testing."""
        return SubsystemAttributeSyntheticData.create_test_subsystem(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create SubsystemAttribute instance for testing."""
        defaults = {
            'subsystem': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create SubsystemAttributeItemEditContext for testing."""
        return SubsystemAttributeItemEditContext(subsystem=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Subsystem editing."""
        return SubsystemAttributeSyntheticData.create_form_data_for_single_subsystem_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Subsystem editing."""
        form_data = SubsystemAttributeSyntheticData.create_form_data_for_single_subsystem_edit(owner)
        prefix = f'subsystem-{owner.id}'
        form_data[f'{prefix}-0-name'] = ''  # Invalid empty name
        return form_data
        
    def test_subsystem_specific_response_content(self):
        """Test Subsystem-specific response content and templates - Subsystem response handling."""
        subsystem = self.create_owner_instance(name="Response Test Subsystem")
        context = self.create_item_edit_context(subsystem)
        renderer = self._get_renderer()
        
        request = self.factory.post('/config/subsystem/test/')
        request.session = self._get_mock_session()
        
        response = renderer.render_form_success_response(
            attr_item_context=context,
            request=request,
            message=None  # Use default message
        )
        
        # Should use Subsystem-specific template context
        self.assertEqual(response.status_code, 200)
        
        # Verify response contains Subsystem-specific data
        import json
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)
        
    def test_subsystem_multi_edit_response_patterns(self):
        """Test Subsystem multi-edit response patterns - unique to config module."""
        subsystem_list = SubsystemAttributeSyntheticData.create_multiple_subsystems_scenario()
        page_context = SubsystemAttributePageEditContext("test_subsystem")
        item_context_list = [
            SubsystemAttributeItemEditContext(subsystem=sub) for sub in subsystem_list
        ]
        
        renderer = self._get_renderer()
        handler = self._get_handler()
        
        # Create multi-edit form data list
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list
        )
        
        request = self.factory.post('/config/subsystem/multi/test/')
        request.session = self._get_mock_session()
        
        response = renderer.render_form_success_response_multi(
            attr_page_context=page_context,
            multi_edit_form_data_list=multi_edit_form_data_list,
            request=request,
            message=None  # Use default message
        )
        
        # Should handle multi-edit success response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
    def test_subsystem_no_file_upload_response(self):
        """Test Subsystem file upload response handling - no file support."""
        subsystem = self.create_owner_instance(name="No File Response Subsystem")
        context = self.create_item_edit_context(subsystem)
        
        # Subsystem contexts don't support file uploads
        self.assertIsNone(context.attribute_upload_form_class)
        self.skipTest("File uploads not supported by Subsystem context")
        
    def _get_renderer(self):
        """Get renderer instance for testing."""
        from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
        return AttributeEditResponseRenderer()
        
    def _get_handler(self):
        """Get handler instance for testing."""
        from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
        return AttributeEditFormHandler()
        
    def _get_mock_session(self):
        """Get mock session for testing."""
        from hi.testing.base_test_case import MockSession
        return MockSession()


class SubsystemAttributeEditTemplateContextBuilderTest(AttributeEditTemplateContextBuilderTestMixin, BaseTestCase):
    """Test AttributeEditTemplateContextBuilder with Subsystem-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Subsystem instance for testing."""
        return SubsystemAttributeSyntheticData.create_test_subsystem(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create SubsystemAttribute instance for testing."""
        defaults = {
            'subsystem': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create SubsystemAttributeItemEditContext for testing."""
        return SubsystemAttributeItemEditContext(subsystem=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Subsystem editing."""
        return SubsystemAttributeSyntheticData.create_form_data_for_single_subsystem_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Subsystem editing."""
        form_data = SubsystemAttributeSyntheticData.create_form_data_for_single_subsystem_edit(owner)
        prefix = f'subsystem-{owner.id}'
        form_data[f'{prefix}-0-name'] = ''
        return form_data
        
    def test_subsystem_specific_template_context_keys(self):
        """Test Subsystem-specific template context keys - Subsystem template integration."""
        subsystem = self.create_owner_instance(name="Template Context Subsystem")
        context = self.create_item_edit_context(subsystem)
        builder = self._get_builder()
        
        template_context = builder.build_initial_template_context(
            attr_item_context=context
        )
        
        # Should include Subsystem-specific keys
        self.assertIn('subsystem', template_context)
        self.assertIs(template_context['subsystem'], subsystem)
        
        # Should NOT include owner form (Subsystem has no editable properties)
        self.assertIsNone(template_context.get('owner_form'))
        self.assertIsNone(template_context.get('subsystem_form'))
        
        # Should include generic keys
        self.assertIn('attr_item_context', template_context)
        self.assertIn('regular_attributes_formset', template_context)
        
    def test_subsystem_multi_edit_template_context(self):
        """Test Subsystem multi-edit template context - unique to config module."""
        subsystem_list = SubsystemAttributeSyntheticData.create_multiple_subsystems_scenario()
        page_context = SubsystemAttributePageEditContext("test_subsystem")
        item_context_list = [
            SubsystemAttributeItemEditContext(subsystem=sub) for sub in subsystem_list
        ]
        
        builder = self._get_builder()
        
        template_context = builder.build_initial_template_context_multi(
            attr_page_context=page_context,
            attr_item_context_list=item_context_list
        )
        
        # Should include multi-edit context
        self.assertIn('multi_edit_form_data_list', template_context)
        self.assertIn('attr_page_context', template_context)
        
        # Should have form data for each subsystem
        multi_edit_data = template_context['multi_edit_form_data_list']
        self.assertEqual(len(multi_edit_data), len(subsystem_list))
        
    def test_subsystem_system_attribute_context_assembly(self):
        """Test Subsystem system attribute context assembly - system attribute handling."""
        subsystem = SubsystemAttributeSyntheticData.create_system_configuration_scenario()
        context = self.create_item_edit_context(subsystem)
        builder = self._get_builder()
        
        template_context = builder.build_initial_template_context(
            attr_item_context=context
        )
        
        # Should properly handle system attributes
        formset = template_context['regular_attributes_formset']
        self.assertIsNotNone(formset)
        
        # Should include subsystem in context
        self.assertIn('subsystem', template_context)
        self.assertEqual(template_context['subsystem'].name, "System Configuration")
        
    def _get_builder(self):
        """Get builder instance for testing."""
        from hi.apps.attribute.edit_template_context_builder import AttributeEditTemplateContextBuilder
        return AttributeEditTemplateContextBuilder()
        
    def _get_handler(self):
        """Get handler instance for testing."""
        from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
        return AttributeEditFormHandler()


    
