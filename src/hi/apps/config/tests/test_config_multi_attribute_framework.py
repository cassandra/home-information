"""
Multi-instance attribute editing framework tests for config module.

These tests are specifically designed for the config module's multi-edit architecture,
where multiple subsystems are edited simultaneously.
"""
from typing import List, Dict, Any

from hi.testing.base_test_case import BaseTestCase
from hi.testing.attribute_multi_framework_test_base import (
    AttributeMultiEditFormHandlerTestMixin,
    AttributeMultiEditResponseRendererTestMixin,
    AttributeMultiEditTemplateContextBuilderTestMixin,
    AttributeMultiEditViewMixinTestMixin,
)

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.attribute.models import AttributeModel
from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
from hi.apps.attribute.edit_template_context_builder import AttributeEditTemplateContextBuilder
from hi.apps.attribute.view_mixins import AttributeMultiEditViewMixin

from hi.apps.config.models import Subsystem, SubsystemAttribute
from hi.apps.config.subsystem_attribute_edit_context import (
    SubsystemAttributeItemEditContext,
    SubsystemAttributePageEditContext,
)
from hi.apps.config.tests.synthetic_data import SubsystemAttributeSyntheticData


class SubsystemMultiAttributeEditFormHandlerTest(AttributeMultiEditFormHandlerTestMixin, BaseTestCase):
    """Test AttributeEditFormHandler with Subsystem-specific multi-edit implementations."""
    
    def create_owner_instance_list(self, **kwargs) -> List[Subsystem]:
        """Create multiple Subsystem instances for multi-edit testing."""
        return SubsystemAttributeSyntheticData.create_multiple_subsystems_scenario()
    
    def create_attribute_instance(self, owner: Subsystem, **kwargs) -> AttributeModel:
        """Create SubsystemAttribute instance for testing."""
        defaults = {
            'subsystem': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'value_type_str': kwargs.pop('value_type_str', str(AttributeValueType.TEXT)),
            'setting_key': 'test.setting.key',
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
    
    def create_item_edit_context(self, owner: Subsystem) -> SubsystemAttributeItemEditContext:
        """Create SubsystemAttributeItemEditContext for testing."""
        return SubsystemAttributeItemEditContext(subsystem=owner)
    
    def create_page_edit_context(self, owner_list: List[Subsystem]) -> SubsystemAttributePageEditContext:
        """Create SubsystemAttributePageEditContext for multi-edit testing."""
        # Page context only needs selected_subsystem_id, not the full list
        selected_subsystem_id = str(owner_list[0].id) if owner_list else None
        return SubsystemAttributePageEditContext(selected_subsystem_id=selected_subsystem_id)
    
    def create_multi_valid_form_data(self, owner_list: List[Subsystem], **overrides) -> Dict[str, Any]:
        """Create valid form data for multi-edit scenarios."""
        return SubsystemAttributeSyntheticData.create_form_data_for_subsystem_multi_edit(
            owner_list, **overrides
        )
    
    def create_multi_invalid_form_data(self, owner_list: List[Subsystem]) -> Dict[str, Any]:
        """Create invalid form data for multi-edit scenarios."""
        return SubsystemAttributeSyntheticData.create_invalid_form_data_multi_subsystem(owner_list)
    
    def test_subsystem_multi_edit_formset_patterns(self):
        """Test Subsystem-specific multi-edit formset patterns - Subsystem multi formset logic."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        
        handler = AttributeEditFormHandler()
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list
        )
        
        # Should create form data for each subsystem
        self.assertEqual(len(multi_edit_form_data_list), len(owner_list))
        
        # Each subsystem should have its own formset
        for i, form_data in enumerate(multi_edit_form_data_list):
            self.assertIsNotNone(form_data.regular_attributes_formset)
            # Subsystems don't have owner forms
            self.assertIsNone(form_data.owner_form)
            
            # Check formset prefix matches subsystem ID
            expected_prefix = f'subsystem-{owner_list[i].id}'
            self.assertEqual(form_data.regular_attributes_formset.prefix, expected_prefix)
    
    def test_subsystem_multi_edit_system_attributes(self):
        """Test Subsystem multi-edit with PREDEFINED attribute types - system attribute handling."""
        # Create subsystems with PREDEFINED attributes
        subsystem1 = SubsystemAttributeSyntheticData.create_test_subsystem(
            name="System Config 1", subsystem_key="system_config_1"
        )
        SubsystemAttributeSyntheticData.create_test_text_attribute(
            subsystem=subsystem1,
            name='system_name',
            value='Config System 1',
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        subsystem2 = SubsystemAttributeSyntheticData.create_test_subsystem(
            name="System Config 2", subsystem_key="system_config_2"
        )
        SubsystemAttributeSyntheticData.create_test_text_attribute(
            subsystem=subsystem2,
            name='system_name', 
            value='Config System 2',
            attribute_type_str=str(AttributeType.PREDEFINED)
        )
        
        owner_list = [subsystem1, subsystem2]
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        
        handler = AttributeEditFormHandler()
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list
        )
        
        # Should handle PREDEFINED attributes properly
        for form_data in multi_edit_form_data_list:
            formset = form_data.regular_attributes_formset
            # Should have forms for existing attributes
            self.assertGreater(len(formset.forms), 0)


class SubsystemMultiAttributeEditResponseRendererTest(AttributeMultiEditResponseRendererTestMixin, BaseTestCase):
    """Test AttributeEditResponseRenderer with Subsystem-specific multi-edit implementations."""
    
    def create_owner_instance_list(self, **kwargs) -> List[Subsystem]:
        """Create multiple Subsystem instances for multi-edit testing."""
        return SubsystemAttributeSyntheticData.create_multiple_subsystems_scenario()
    
    def create_attribute_instance(self, owner: Subsystem, **kwargs) -> AttributeModel:
        """Create SubsystemAttribute instance for testing."""
        defaults = {
            'subsystem': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'value_type_str': kwargs.pop('value_type_str', str(AttributeValueType.TEXT)),
            'setting_key': 'test.setting.key',
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
    
    def create_item_edit_context(self, owner: Subsystem) -> SubsystemAttributeItemEditContext:
        """Create SubsystemAttributeItemEditContext for testing."""
        return SubsystemAttributeItemEditContext(subsystem=owner)
    
    def create_page_edit_context(self, owner_list: List[Subsystem]) -> SubsystemAttributePageEditContext:
        """Create SubsystemAttributePageEditContext for multi-edit testing."""
        # Page context only needs selected_subsystem_id, not the full list
        selected_subsystem_id = str(owner_list[0].id) if owner_list else None
        return SubsystemAttributePageEditContext(selected_subsystem_id=selected_subsystem_id)
    
    def create_multi_valid_form_data(self, owner_list: List[Subsystem], **overrides) -> Dict[str, Any]:
        """Create valid form data for multi-edit scenarios."""
        return SubsystemAttributeSyntheticData.create_form_data_for_subsystem_multi_edit(
            owner_list, **overrides
        )
    
    def create_multi_invalid_form_data(self, owner_list: List[Subsystem]) -> Dict[str, Any]:
        """Create invalid form data for multi-edit scenarios."""
        return SubsystemAttributeSyntheticData.create_invalid_form_data_multi_subsystem(owner_list)
    
    def test_subsystem_multi_edit_response_content(self):
        """Test Subsystem-specific multi-edit response content - Subsystem response handling."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        page_context = self.create_page_edit_context(owner_list)
        
        handler = AttributeEditFormHandler()
        renderer = AttributeEditResponseRenderer()
        
        multi_edit_form_data_list = handler.create_multi_edit_form_data(
            attr_item_context_list=item_context_list
        )
        
        request = MockRequest()
        request.session = MockSession()
        
        response = renderer.render_form_success_response_multi(
            attr_page_context=page_context,
            multi_edit_form_data_list=multi_edit_form_data_list,
            request=request,
            message=None  # Use default message
        )
        
        # Should use Subsystem-specific template context
        self.assertEqual(response.status_code, 200)
        
        # Verify response contains Subsystem-specific data
        import json
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)
        
        # Should contain updates for multiple subsystems
        self.assertTrue(len(data) > 0)


class SubsystemMultiAttributeEditTemplateContextBuilderTest(AttributeMultiEditTemplateContextBuilderTestMixin, BaseTestCase):
    """Test AttributeEditTemplateContextBuilder with Subsystem-specific multi-edit implementations."""
    
    def create_owner_instance_list(self, **kwargs) -> List[Subsystem]:
        """Create multiple Subsystem instances for multi-edit testing."""
        return SubsystemAttributeSyntheticData.create_multiple_subsystems_scenario()
    
    def create_attribute_instance(self, owner: Subsystem, **kwargs) -> AttributeModel:
        """Create SubsystemAttribute instance for testing."""
        defaults = {
            'subsystem': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'value_type_str': kwargs.pop('value_type_str', str(AttributeValueType.TEXT)),
            'setting_key': 'test.setting.key',
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
    
    def create_item_edit_context(self, owner: Subsystem) -> SubsystemAttributeItemEditContext:
        """Create SubsystemAttributeItemEditContext for testing."""
        return SubsystemAttributeItemEditContext(subsystem=owner)
    
    def create_page_edit_context(self, owner_list: List[Subsystem]) -> SubsystemAttributePageEditContext:
        """Create SubsystemAttributePageEditContext for multi-edit testing."""
        # Page context only needs selected_subsystem_id, not the full list
        selected_subsystem_id = str(owner_list[0].id) if owner_list else None
        return SubsystemAttributePageEditContext(selected_subsystem_id=selected_subsystem_id)
    
    def create_multi_valid_form_data(self, owner_list: List[Subsystem], **overrides) -> Dict[str, Any]:
        """Create valid form data for multi-edit scenarios."""
        return SubsystemAttributeSyntheticData.create_form_data_for_subsystem_multi_edit(
            owner_list, **overrides
        )
    
    def create_multi_invalid_form_data(self, owner_list: List[Subsystem]) -> Dict[str, Any]:
        """Create invalid form data for multi-edit scenarios."""
        return SubsystemAttributeSyntheticData.create_invalid_form_data_multi_subsystem(owner_list)
    
    def test_subsystem_multi_edit_template_context_assembly(self):
        """Test Subsystem multi-edit template context assembly - multi subsystem context handling."""
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
        
        # Should include multi-edit context
        self.assertIn('multi_edit_form_data_list', template_context)
        self.assertIn('attr_page_context', template_context)
        
        # Should have form data for each subsystem
        multi_edit_data = template_context['multi_edit_form_data_list']
        self.assertEqual(len(multi_edit_data), len(owner_list))
        
        # Should include selected subsystem ID in page context
        page_ctx = template_context['attr_page_context']
        self.assertIsNotNone(page_ctx.selected_subsystem_id)


class MockConfigMultiEditView(AttributeMultiEditViewMixin):
    """Mock view for testing AttributeMultiEditViewMixin with config context."""
    pass


class SubsystemMultiAttributeViewMixinTest(AttributeMultiEditViewMixinTestMixin, BaseTestCase):
    """Test AttributeMultiEditViewMixin with Subsystem-specific view implementations."""
    
    def create_owner_instance_list(self, **kwargs) -> List[Subsystem]:
        """Create multiple Subsystem instances for multi-edit testing."""
        return SubsystemAttributeSyntheticData.create_multiple_subsystems_scenario()
    
    def create_attribute_instance(self, owner: Subsystem, **kwargs) -> AttributeModel:
        """Create SubsystemAttribute instance for testing."""
        defaults = {
            'subsystem': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.PREDEFINED),
            'value_type_str': kwargs.pop('value_type_str', str(AttributeValueType.TEXT)),
            'setting_key': 'test.setting.key',
        }
        defaults.update(kwargs)
        return SubsystemAttribute.objects.create(**defaults)
    
    def create_item_edit_context(self, owner: Subsystem) -> SubsystemAttributeItemEditContext:
        """Create SubsystemAttributeItemEditContext for testing."""
        return SubsystemAttributeItemEditContext(subsystem=owner)
    
    def create_page_edit_context(self, owner_list: List[Subsystem]) -> SubsystemAttributePageEditContext:
        """Create SubsystemAttributePageEditContext for multi-edit testing."""
        # Page context only needs selected_subsystem_id, not the full list
        selected_subsystem_id = str(owner_list[0].id) if owner_list else None
        return SubsystemAttributePageEditContext(selected_subsystem_id=selected_subsystem_id)
    
    def create_multi_valid_form_data(self, owner_list: List[Subsystem], **overrides) -> Dict[str, Any]:
        """Create valid form data for multi-edit scenarios."""
        return SubsystemAttributeSyntheticData.create_form_data_for_subsystem_multi_edit(
            owner_list, **overrides
        )
    
    def create_multi_invalid_form_data(self, owner_list: List[Subsystem]) -> Dict[str, Any]:
        """Create invalid form data for multi-edit scenarios."""
        return SubsystemAttributeSyntheticData.create_invalid_form_data_multi_subsystem(owner_list)
    
    def create_view_instance(self):
        """Create a view instance that uses AttributeMultiEditViewMixin."""
        return MockConfigMultiEditView()
    
    def test_subsystem_multi_edit_view_integration_workflow(self):
        """Test complete Subsystem multi-edit view integration - unique multi-edit scenario."""
        owner_list = self.create_owner_instance_list()
        item_context_list = [self.create_item_edit_context(owner) for owner in owner_list]
        page_context = self.create_page_edit_context(owner_list)
        
        view = self.create_view_instance()
        
        # Create valid POST data for multiple subsystems
        post_data = QueryDict(mutable=True)
        form_data_dict = self.create_multi_valid_form_data(owner_list)
        for key, value in form_data_dict.items():
            if isinstance(value, list):
                post_data.setlist(key, value)
            else:
                post_data[key] = value
        
        request = MockRequest()
        request.POST = post_data
        request.session = MockSession()
        
        # Test the multi-edit view workflow
        response = view.post_attribute_form(
            request=request,
            attr_page_context=page_context,
            attr_item_context_list=item_context_list
        )
        
        # Should successfully handle multi-subsystem editing
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Verify attributes were saved (basic check)
        for owner in owner_list:
            # Should have at least one attribute after processing
            self.assertTrue(owner.attributes.exists())


# Import MockRequest and MockSession for the module-specific tests
from hi.testing.base_test_case import MockRequest, MockSession
from django.http import QueryDict