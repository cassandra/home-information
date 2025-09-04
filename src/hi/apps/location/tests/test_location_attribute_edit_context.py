"""
Tests for LocationAttributeItemEditContext.

Focuses on Location-specific context generation, URL patterns, and integration
with LocationAttribute model relationships.
"""
import logging
from hi.apps.location.location_attribute_edit_context import LocationAttributeItemEditContext
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestLocationAttributeItemEditContext(BaseTestCase):
    """Test LocationAttributeItemEditContext location-specific functionality."""
    
    def setUp(self):
        super().setUp()
        self.location = LocationSyntheticData.create_test_location(
            name="Test Location",
            svg_fragment_filename="test-location.svg"
        )
        self.context = LocationAttributeItemEditContext(self.location)
        
    def test_location_context_initialization(self):
        """Test LocationAttributeItemEditContext initializes with correct owner type."""
        self.assertEqual(self.context.owner_type, "location")
        self.assertEqual(self.context.owner, self.location)
        self.assertEqual(self.context.owner_id, self.location.id)
        
    def test_location_property_accessor(self):
        """Test typed location property accessor - provides type safety."""
        self.assertIs(self.context.location, self.location)
        self.assertEqual(self.context.location.name, "Test Location")
        self.assertEqual(self.context.location.svg_fragment_filename, "test-location.svg")
        
    def test_location_specific_url_patterns(self):
        """Test location-specific URL name generation - routing integration."""
        self.assertEqual(self.context.history_url_name, "location_attribute_history_inline")
        self.assertEqual(self.context.restore_url_name, "location_attribute_restore_inline")
        self.assertEqual(self.context.owner_id_param_name, "location_id")
        
    def test_location_specific_dom_ids(self):
        """Test location-specific DOM ID generation - JavaScript integration."""
        attribute_id = 123
        
        history_id = self.context.history_target_id(attribute_id)
        self.assertEqual(history_id, f"hi-location-attr-history-{self.location.id}-123")
        
        toggle_id = self.context.history_toggle_id(attribute_id)
        self.assertEqual(toggle_id, f"history-extra-{self.location.id}-123")
        
    def test_location_template_context_assembly(self):
        """Test location-specific template context generation - template integration."""
        template_context = self.context.to_template_context()
        
        # Should include generic keys
        self.assertIn('attr_item_context', template_context)
        self.assertIn('owner', template_context)
        
        # Should include location-specific key
        self.assertIn('location', template_context)
        self.assertIs(template_context['location'], self.location)
        
        # Should NOT include entity key
        self.assertNotIn('entity', template_context)
        
    def test_location_context_with_different_locations(self):
        """Test context works correctly with different location instances."""
        location2 = LocationSyntheticData.create_test_location(
            name="Another Location",
            svg_fragment_filename="another-location.svg"
        )
        context2 = LocationAttributeItemEditContext(location2)
        
        # Should have different IDs and names
        self.assertNotEqual(self.context.owner_id, context2.owner_id)
        
        # But same URL patterns
        self.assertEqual(self.context.history_url_name, context2.history_url_name)
        self.assertEqual(self.context.owner_id_param_name, context2.owner_id_param_name)
        
        # DOM IDs should differ by location ID
        attribute_id = 456
        history1 = self.context.history_target_id(attribute_id)
        history2 = context2.history_target_id(attribute_id)
        self.assertNotEqual(history1, history2)
        self.assertIn(str(self.location.id), history1)
        self.assertIn(str(location2.id), history2)
        
    def test_location_context_form_field_naming(self):
        """Test location-specific form field name generation."""
        attribute_id = 789
        field_name = self.context.file_title_field_name(attribute_id)
        expected = f"file_title_{self.location.id}_{attribute_id}"
        self.assertEqual(field_name, expected)
        
    def test_location_context_consistency_across_operations(self):
        """Test context maintains consistency across different operations - state management."""
        attribute_id = 999
        
        # All operations should use the same location ID
        history_id = self.context.history_target_id(attribute_id)
        toggle_id = self.context.history_toggle_id(attribute_id)
        field_name = self.context.file_title_field_name(attribute_id)
        
        location_id_str = str(self.location.id)
        self.assertIn(location_id_str, history_id)
        self.assertIn(location_id_str, toggle_id)
        self.assertIn(location_id_str, field_name)
        
    def test_location_context_inheritance_behavior(self):
        """Test LocationAttributeItemEditContext properly inherits base functionality."""
        # Should inherit all base class methods
        self.assertTrue(hasattr(self.context, 'owner_id'))
        self.assertTrue(hasattr(self.context, 'owner_id_param_name'))
        self.assertTrue(hasattr(self.context, 'history_url_name'))
        self.assertTrue(hasattr(self.context, 'restore_url_name'))
        self.assertTrue(hasattr(self.context, 'history_target_id'))
        self.assertTrue(hasattr(self.context, 'history_toggle_id'))
        self.assertTrue(hasattr(self.context, 'file_title_field_name'))
        self.assertTrue(hasattr(self.context, 'to_template_context'))
        
    def test_location_context_edge_cases(self):
        """Test location context handles edge cases gracefully."""
        # Test with location having special characters in name
        special_location = LocationSyntheticData.create_test_location(
            name="Location with & special chars!",
            svg_fragment_filename="special-location.svg"
        )
        special_context = LocationAttributeItemEditContext(special_location)
        
        # DOM IDs should still be generated properly
        history_id = special_context.history_target_id(123)
        self.assertIn("hi-location-attr-history", history_id)
        self.assertIn(str(special_location.id), history_id)
        
    def test_location_context_with_location_attributes(self):
        """Test context integration with actual LocationAttribute relationships."""
        # Create location with attributes using synthetic data
        location_with_attrs = LocationSyntheticData.create_test_location(
            name="Location with Attributes"
        )
        
        context = LocationAttributeItemEditContext(location_with_attrs)
        
        # Context should work with the location regardless of attribute count
        self.assertEqual(context.location, location_with_attrs)
        self.assertEqual(context.owner_type, "location")
        
        # Template context should be consistent
        template_ctx = context.to_template_context()
        self.assertIs(template_ctx['location'], location_with_attrs)
        
    def test_location_context_multiple_instances_isolation(self):
        """Test multiple LocationAttributeItemEditContext instances don't interfere - instance isolation."""
        location1 = LocationSyntheticData.create_test_location(name="Location 1")
        location2 = LocationSyntheticData.create_test_location(name="Location 2")
        
        context1 = LocationAttributeItemEditContext(location1)
        context2 = LocationAttributeItemEditContext(location2)
        
        # Contexts should be independent
        self.assertNotEqual(context1.owner_id, context2.owner_id)
                
    def test_location_context_type_consistency(self):
        """Test LocationAttributeItemEditContext maintains type consistency - type safety."""
        # owner_type should always be 'location'
        self.assertEqual(self.context.owner_type, "location")
        
        # location property should return the same instance as owner
        self.assertIs(self.context.location, self.context.owner)
        
        # Template context should have location key pointing to same instance
        template_ctx = self.context.to_template_context()
        self.assertIs(template_ctx['location'], self.context.owner)
        self.assertIs(template_ctx['owner'], self.context.owner)
        
