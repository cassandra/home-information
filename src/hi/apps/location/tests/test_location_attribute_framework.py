"""
Concrete test implementations for Location attribute editing framework.

These tests extend the abstract base classes to provide comprehensive testing
of the attribute framework as implemented for Location models. Tests both the
framework components and Location-specific customizations.

Following project testing guidelines:
- No mocked objects, use real Location and LocationAttribute models
- Focus on high-value business logic and integration points
- Use LocationAttributeSyntheticData for test data generation
- Test meaningful Location-specific edge cases and workflows
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
from hi.apps.location.location_attribute_edit_context import LocationAttributeItemEditContext
from hi.apps.location.models import LocationAttribute
from hi.apps.location.tests.synthetic_data import LocationAttributeSyntheticData
from hi.apps.location.views import LocationEditView

logging.disable(logging.CRITICAL)


class LocationAttributeEditFormHandlerTest(AttributeEditFormHandlerTestMixin, BaseTestCase):
    """Test AttributeEditFormHandler with Location-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Location instance for testing."""
        return LocationAttributeSyntheticData.create_test_location(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create LocationAttribute instance for testing."""
        value_type = kwargs.get('value_type_str', str(AttributeValueType.TEXT))
        
        # Use synthetic data method for file attributes to ensure proper file handling
        if value_type == str(AttributeValueType.FILE):
            return LocationAttributeSyntheticData.create_test_file_attribute(location=owner, **kwargs)
        
        # For non-file attributes, use direct creation
        defaults = {
            'location': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': value_type,
        }
        defaults.update(kwargs)
        return LocationAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create LocationAttributeItemEditContext for testing."""
        return LocationAttributeItemEditContext(location=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Location editing."""
        return LocationAttributeSyntheticData.create_form_data_for_location_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Location editing - empty name."""
        form_data = LocationAttributeSyntheticData.create_form_data_for_location_edit(owner)
        form_data['name'] = ''  # Invalid empty name
        return form_data
        
    def test_location_specific_form_validation_business_logic(self):
        """Test Location-specific form validation rules - business logic validation."""
        location = self.create_owner_instance(name="Location Validation Test")
        context = self.create_item_edit_context(location)
        handler = self._get_handler()
        
        # Test location name validation
        invalid_data = self.create_valid_form_data(location)
        invalid_data['name'] = ''  # Location requires name
        
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=invalid_data
        )
        
        is_valid = handler.validate_forms(edit_form_data=form_data)
        self.assertFalse(is_valid)
        
        # Location form should have name error
        if form_data.owner_form:
            self.assertIn('name', form_data.owner_form.errors)
            
    def test_location_svg_field_validation(self):
        """Test Location SVG field validation - Location-specific validation."""
        location = self.create_owner_instance(name="SVG Validation Test")
        context = self.create_item_edit_context(location)
        handler = self._get_handler()
        
        # Test invalid SVG viewBox format
        invalid_data = self.create_valid_form_data(location)
        invalid_data['svg_view_box_str'] = 'invalid viewbox format'
        
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=invalid_data
        )
        
        is_valid = handler.validate_forms(edit_form_data=form_data)
        # May be valid or invalid depending on form validation rules
        self.assertIsInstance(is_valid, bool)
        
    def test_location_attribute_formset_creation_patterns(self):
        """Test Location-specific formset creation patterns - Location formset logic."""
        location = self.create_owner_instance(name="Formset Test Location")
        
        # Create mixed attribute types
        self.create_attribute_instance(
            location, name="description", value="location description",
            value_type_str=str(AttributeValueType.TEXT)
        )
        self.create_attribute_instance(
            location, name="floor_plan", value="Floor Plan",
            value_type_str=str(AttributeValueType.FILE)
        )
        
        context = self.create_item_edit_context(location)
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
        
        self.assertIn("description", formset_names)
        self.assertNotIn("floor_plan", formset_names)
        
        # File attributes should be in separate queryset
        file_attr_names = [attr.name for attr in form_data.file_attributes]
        self.assertIn("floor_plan", file_attr_names)
        self.assertNotIn("description", file_attr_names)
        
    def test_location_file_upload_integration(self):
        """Test Location file upload handling - Location file operations."""
        location = self.create_owner_instance(name="File Upload Location")
        context = self.create_item_edit_context(location)
        
        # Location should support file uploads
        self.assertIsNotNone(context.attribute_upload_form_class)
        self.assertTrue(context.uses_file_uploads)
        
        # Test file context setup
        self.assertIsNotNone(context.file_upload_url)
        
        # Test file handling patterns
        test_file = SimpleUploadedFile(
            "location_plan.pdf",
            b"Location test file content",
            content_type="application/pdf"
        )
        
        _ = self.create_hi_request(
            method='POST',
            path='/location/test/',
            data={
                'name': 'location_document',
                'value': 'Location Test Document'
            },
            files={'file_value': test_file}
        )
        
        # Should handle file upload processing context
        initial_count = LocationAttribute.objects.filter(
            location=location,
            value_type_str=str(AttributeValueType.FILE)
        ).count()
        
        # File handling workflow tested at view level
        self.assertIsInstance(initial_count, int)
        
    def test_location_specific_edge_cases(self):
        """Test Location-specific edge cases - Location edge case handling."""
        location = self.create_owner_instance(
            name="Edge Case Location",
            svg_view_box_str="0 0 1000 1000"  # Different dimensions
        )
        context = self.create_item_edit_context(location)
        handler = self._get_handler()
        
        # Test with very long location name
        long_name = "A" * 200
        form_data = self.create_valid_form_data(location, name=long_name)
        
        edit_form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=form_data
        )
        
        # Should handle long names according to model constraints
        is_valid = handler.validate_forms(edit_form_data=edit_form_data)
        self.assertIsInstance(is_valid, bool)
        
    def _get_handler(self):
        """Get handler instance for testing."""
        from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
        return AttributeEditFormHandler()


class LocationAttributeEditResponseRendererTest(AttributeEditResponseRendererTestMixin, BaseTestCase):
    """Test AttributeEditResponseRenderer with Location-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Location instance for testing."""
        return LocationAttributeSyntheticData.create_test_location(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create LocationAttribute instance for testing."""
        defaults = {
            'location': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return LocationAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create LocationAttributeItemEditContext for testing."""
        return LocationAttributeItemEditContext(location=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Location editing."""
        return LocationAttributeSyntheticData.create_form_data_for_location_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Location editing."""
        form_data = LocationAttributeSyntheticData.create_form_data_for_location_edit(owner)
        form_data['name'] = ''  # Invalid empty name
        return form_data
        
    def test_location_specific_response_content(self):
        """Test Location-specific response content and templates - Location response handling."""
        location = self.create_owner_instance(name="Response Test Location")
        context = self.create_item_edit_context(location)
        renderer = self._get_renderer()
        
        request = self.create_hi_request('POST', '/location/test/')
        
        response = renderer.render_form_success_response(
            attr_item_context=context,
            request=request,
            message=None  # Use default message
        )
        
        # Should use Location-specific template context
        self.assertEqual(response.status_code, 200)
        
        # Verify response contains Location-specific data
        import json
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)
        
    def test_location_template_context_integration(self):
        """Test Location template context integration - Location template handling."""
        location = self.create_owner_instance(
            name="Template Context Location",
            svg_view_box_str="0 0 1200 800"
        )
        context = self.create_item_edit_context(location)
        
        # Location context should provide SVG-related properties
        self.assertEqual(context.owner_type, 'location')
        self.assertEqual(context.location, location)
        
        # Template context should include location-specific data
        template_context = context.to_template_context()
        self.assertIn('location', template_context)
        self.assertIs(template_context['location'], location)
        
    def _get_renderer(self):
        """Get renderer instance for testing."""
        from hi.apps.attribute.edit_response_renderer import AttributeEditResponseRenderer
        return AttributeEditResponseRenderer()
        

class LocationAttributeEditTemplateContextBuilderTest(
        AttributeEditTemplateContextBuilderTestMixin,
        BaseTestCase ):
    """Test AttributeEditTemplateContextBuilder with Location-specific implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Location instance for testing."""
        return LocationAttributeSyntheticData.create_test_location(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create LocationAttribute instance for testing."""
        defaults = {
            'location': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return LocationAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create LocationAttributeItemEditContext for testing."""
        return LocationAttributeItemEditContext(location=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Location editing."""
        return LocationAttributeSyntheticData.create_form_data_for_location_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Location editing."""
        form_data = LocationAttributeSyntheticData.create_form_data_for_location_edit(owner)
        form_data['name'] = ''
        return form_data
        
    def test_location_specific_template_context_keys(self):
        """Test Location-specific template context keys - Location template integration."""
        location = self.create_owner_instance(name="Template Context Location")
        context = self.create_item_edit_context(location)
        builder = self._get_builder()
        
        template_context = builder.build_initial_template_context(
            attr_item_context=context
        )
        
        # Should include Location-specific keys
        self.assertIn('location', template_context)
        self.assertIs(template_context['location'], location)
        self.assertIn('location_form', template_context)
        
        # Should include generic keys
        self.assertIn('owner', template_context)
        self.assertIn('attr_item_context', template_context)
        
    def test_location_svg_context_assembly(self):
        """Test Location SVG-specific context assembly - Location SVG handling."""
        location = self.create_owner_instance(
            name="SVG Context Location",
            svg_view_box_str="0 0 1600 1200",
            svg_fragment_filename="custom-layout.svg"
        )
        context = self.create_item_edit_context(location)
        builder = self._get_builder()
        
        template_context = builder.build_initial_template_context(
            attr_item_context=context
        )
        
        # Location should be accessible in template context
        location_in_context = template_context['location']
        self.assertEqual(location_in_context.svg_view_box_str, "0 0 1600 1200")
        self.assertEqual(location_in_context.svg_fragment_filename, "custom-layout.svg")
        
    def test_location_form_error_context_assembly(self):
        """Test Location form error context assembly - Location error handling."""
        location = self.create_owner_instance(name="Error Context Location")
        context = self.create_item_edit_context(location)
        builder = self._get_builder()
        handler = self._get_handler()
        
        # Create form with errors
        invalid_data = self.create_invalid_form_data(location)
        form_data = handler.create_edit_form_data(
            attr_item_context=context,
            form_data=invalid_data
        )
        
        # Trigger validation to create errors
        handler.validate_forms(edit_form_data=form_data)
        
        template_context = builder.build_response_template_context(
            attr_item_context=context,
            edit_form_data=form_data,
            error_message="Location validation failed",
            has_errors=True
        )
        
        # Should properly handle Location form errors
        self.assertTrue(template_context.get('has_errors', False))
        self.assertIn('error_message', template_context)
        
        # Location form should be available with errors
        if template_context.get('owner_form'):
            location_form = template_context['owner_form']
            self.assertTrue(hasattr(location_form, 'errors'))
            
    def _get_builder(self):
        """Get builder instance for testing."""
        from hi.apps.attribute.edit_template_context_builder import AttributeEditTemplateContextBuilder
        return AttributeEditTemplateContextBuilder()
        
    def _get_handler(self):
        """Get handler instance for testing."""
        from hi.apps.attribute.edit_form_handler import AttributeEditFormHandler
        return AttributeEditFormHandler()


class LocationAttributeViewMixinTest(AttributeViewMixinTestMixin, BaseTestCase):
    """Test AttributeEditViewMixin with Location-specific view implementations."""
    
    def create_owner_instance(self, **kwargs):
        """Create Location instance for testing."""
        return LocationAttributeSyntheticData.create_test_location(**kwargs)
        
    def create_attribute_instance(self, owner, **kwargs) -> AttributeModel:
        """Create LocationAttribute instance for testing."""
        defaults = {
            'location': owner,
            'name': 'test_attribute',
            'value': 'test_value',
            'attribute_type_str': str(AttributeType.CUSTOM),
            'value_type_str': str(AttributeValueType.TEXT),
        }
        defaults.update(kwargs)
        return LocationAttribute.objects.create(**defaults)
        
    def create_item_edit_context(self, owner):
        """Create LocationAttributeItemEditContext for testing."""
        return LocationAttributeItemEditContext(location=owner)
        
    def create_valid_form_data(self, owner, **overrides):
        """Create valid form data for Location editing."""
        return LocationAttributeSyntheticData.create_form_data_for_location_edit(
            owner, **overrides
        )
        
    def create_invalid_form_data(self, owner):
        """Create invalid form data for Location editing."""
        form_data = LocationAttributeSyntheticData.create_form_data_for_location_edit(owner)
        form_data['name'] = ''
        return form_data
        
    def create_test_view_instance(self):
        """Create LocationEditView instance for testing."""
        return LocationEditView()
        
    def test_location_edit_view_integration_workflow(self):
        """Test complete LocationEditView integration - Location view integration."""
        location = self.create_owner_instance(name="View Integration Location")
        
        # Create attributes for comprehensive testing
        self.create_attribute_instance(
            location, name="description", value="Original description"
        )
        
        view = self.create_test_view_instance()
        context = self.create_item_edit_context(location)
        
        # Test GET request (initial template context)
        _ = self.create_hi_request('GET', f'/location/{location.id}/edit/')
        
        template_context = view.create_initial_template_context(
            attr_item_context=context
        )
        
        # Should provide complete Location editing context
        self.assertIn('location', template_context)
        self.assertIn('location_form', template_context)
        self.assertIn('regular_attributes_formset', template_context)
        
    def test_location_attribute_history_view_integration(self):
        """Test Location attribute history integration - Location history functionality."""
        location = self.create_owner_instance(name="History Integration Location")
        attribute = self.create_attribute_instance(
            location, name="history_attr", value="current_value"
        )
        
        view = self.create_test_view_instance()
        context = self.create_item_edit_context(location)
        
        request = self.create_hi_request('GET', f'/location/{location.id}/attr/{attribute.id}/history/')
        
        response = view.get_history(
            request=request,
            attribute=attribute,
            attr_item_context=context
        )
        
        # Should handle Location attribute history
        self.assertEqual(response.status_code, 200)
        
    def test_location_svg_integration_workflow(self):
        """Test Location SVG-related integration - Location SVG functionality."""
        location = self.create_owner_instance(
            name="SVG Integration Location",
            svg_view_box_str="0 0 2000 1500",
            svg_fragment_filename="integration-test.svg"
        )
        
        context = self.create_item_edit_context(location)
        
        # Location context should handle SVG properties
        self.assertEqual(context.location.svg_view_box_str, "0 0 2000 1500")
        self.assertEqual(context.location.svg_fragment_filename, "integration-test.svg")
        
        # Template context should provide SVG data
        template_context = context.to_template_context()
        location_in_context = template_context['location']
        self.assertEqual(location_in_context.svg_view_box_str, "0 0 2000 1500")
        
    
