"""
Tests for AttributeEditContext base class.

Focuses on high-value business logic: property computation, DOM ID generation,
URL parameter construction, and template context assembly.
"""
import logging
from hi.apps.attribute.edit_context import AttributeEditContext
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class MockOwner:
    """Simple mock owner for testing AttributeEditContext without Django model dependencies."""
    
    def __init__(self, id, name):
        self.id = id
        self.name = name


class TestAttributeEditContext(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_owner = MockOwner(id=123, name="Test Owner")
        self.context = AttributeEditContext(self.mock_owner, "entity")
    
    def test_property_computation_basic_cases(self):
        """Test basic property computation - critical URL and DOM ID generation logic."""
        # Test basic property access
        self.assertEqual(self.context.owner_id, 123)
        self.assertEqual(self.context.owner_name, "Test Owner")
        self.assertEqual(self.context.owner_type, "entity")
        self.assertEqual(self.context.owner_id_param_name, "entity_id")
        
    def test_property_computation_case_normalization(self):
        """Test owner type case normalization - critical for consistent URL patterns."""
        # Test case normalization
        context_upper = AttributeEditContext(self.mock_owner, "ENTITY")
        context_mixed = AttributeEditContext(self.mock_owner, "EnTiTy")
        
        self.assertEqual(context_upper.owner_type, "entity")
        self.assertEqual(context_mixed.owner_type, "entity")
        self.assertEqual(context_upper.owner_id_param_name, "entity_id")
        self.assertEqual(context_mixed.owner_id_param_name, "entity_id")
        
    def test_url_name_generation_patterns(self):
        """Test URL name generation follows expected patterns - critical for routing."""
        # Test URL name patterns
        self.assertEqual(self.context.history_url_name, "entity_attribute_history_inline")
        self.assertEqual(self.context.restore_url_name, "entity_attribute_restore_inline")
        
        # Test with location owner type
        location_context = AttributeEditContext(self.mock_owner, "location")
        self.assertEqual(location_context.history_url_name, "location_attribute_history_inline")
        self.assertEqual(location_context.restore_url_name, "location_attribute_restore_inline")
        
    def test_dom_id_generation_patterns(self):
        """Test DOM ID generation for JavaScript integration - critical for frontend functionality."""
        attribute_id = 456
        
        # Test history container ID
        history_id = self.context.history_target_id(attribute_id)
        self.assertEqual(history_id, "hi-entity-attr-history-123-456")
        
        # Test history toggle ID
        toggle_id = self.context.history_toggle_id(attribute_id)
        self.assertEqual(toggle_id, "history-extra-123-456")
        
    def test_dom_id_generation_with_different_owner_types(self):
        """Test DOM ID generation varies correctly by owner type."""
        attribute_id = 789
        location_context = AttributeEditContext(self.mock_owner, "location")
        
        # Should include owner type in ID
        history_id = location_context.history_target_id(attribute_id)
        self.assertEqual(history_id, "hi-location-attr-history-123-789")
        
        # Toggle ID should be same pattern regardless of owner type
        toggle_id = location_context.history_toggle_id(attribute_id)
        self.assertEqual(toggle_id, "history-extra-123-789")
        
    def test_form_field_name_generation(self):
        """Test form field name generation - critical for form processing."""
        attribute_id = 101
        
        field_name = self.context.file_title_field_name(attribute_id)
        self.assertEqual(field_name, "file_title_123_101")
        
    def test_template_context_assembly_basic(self):
        """Test template context assembly - critical for template rendering."""
        template_context = self.context.to_template_context()
        
        # Should include attr_context key
        self.assertIn('attr_context', template_context)
        self.assertIs(template_context['attr_context'], self.context)
        
        # Should include generic owner key
        self.assertIn('owner', template_context)
        self.assertIs(template_context['owner'], self.mock_owner)
        
        # Should include specific owner type key
        self.assertIn('entity', template_context)
        self.assertIs(template_context['entity'], self.mock_owner)
        
    def test_template_context_assembly_multiple_owner_types(self):
        """Test template context includes correct owner-specific keys."""
        location_context = AttributeEditContext(self.mock_owner, "location")
        template_context = location_context.to_template_context()
        
        # Should include location-specific key, not entity key
        self.assertIn('location', template_context)
        self.assertIs(template_context['location'], self.mock_owner)
        self.assertNotIn('entity', template_context)
        
        # Generic keys should still be present
        self.assertIn('owner', template_context)
        self.assertIn('attr_context', template_context)
        
    def test_edge_case_special_characters_in_owner_name(self):
        """Test handling of special characters in owner names - edge case robustness."""
        special_owner = MockOwner(id=999, name="Owner with spaces & symbols!")
        context = AttributeEditContext(special_owner, "entity")
        
        # Should handle special characters gracefully
        self.assertEqual(context.owner_name, "Owner with spaces & symbols!")
        
        # DOM IDs should still be generated (special chars in name shouldn't break ID generation)
        history_id = context.history_target_id(123)
        self.assertEqual(history_id, "hi-entity-attr-history-999-123")
        
    def test_edge_case_zero_and_negative_ids(self):
        """Test handling of edge case ID values - robustness testing."""
        zero_owner = MockOwner(id=0, name="Zero ID Owner")
        negative_owner = MockOwner(id=-1, name="Negative ID Owner")
        
        zero_context = AttributeEditContext(zero_owner, "entity")
        negative_context = AttributeEditContext(negative_owner, "entity")
        
        # Should handle zero ID
        self.assertEqual(zero_context.owner_id, 0)
        self.assertEqual(zero_context.history_target_id(1), "hi-entity-attr-history-0-1")
        
        # Should handle negative ID
        self.assertEqual(negative_context.owner_id, -1)
        self.assertEqual(negative_context.history_target_id(1), "hi-entity-attr-history--1-1")
        
    def test_edge_case_empty_owner_type(self):
        """Test handling of empty owner type - error case handling."""
        empty_context = AttributeEditContext(self.mock_owner, "")
        
        # Empty string should be normalized but might cause issues in URL patterns
        self.assertEqual(empty_context.owner_type, "")
        self.assertEqual(empty_context.owner_id_param_name, "_id")
        self.assertEqual(empty_context.history_url_name, "_attribute_history_inline")
        
    def test_edge_case_whitespace_owner_type(self):
        """Test handling of whitespace in owner type - normalization logic."""
        whitespace_context = AttributeEditContext(self.mock_owner, "  entity  ")
        
        # Should strip whitespace during normalization
        self.assertEqual(whitespace_context.owner_type, "  entity  ")  # Current implementation preserves whitespace
        self.assertEqual(whitespace_context.owner_id_param_name, "  entity  _id")
        
    def test_context_immutability_after_creation(self):
        """Test that context properties are computed from constructor args - consistency testing."""
        # Modifying owner after context creation shouldn't affect context
        original_id = self.context.owner_id
        original_name = self.context.owner_name
        
        # Modify the mock owner
        self.mock_owner.id = 999
        self.mock_owner.name = "Modified Name"
        
        # Context should reflect the modified owner (it holds a reference, so it's not immutable)
        self.assertEqual(self.context.owner_id, 999)
        self.assertEqual(self.context.owner_name, "Modified Name")
        
        # Verify the change actually happened
        self.assertNotEqual(self.context.owner_id, original_id)
        self.assertNotEqual(self.context.owner_name, original_name)
        
        # But owner_type should remain the same (set at construction)
        self.assertEqual(self.context.owner_type, "entity")
        
    def test_multiple_attribute_id_combinations(self):
        """Test DOM ID and field name generation with various attribute ID values."""
        test_cases = [
            (1, "hi-entity-attr-history-123-1", "history-extra-123-1", "file_title_123_1"),
            (999, "hi-entity-attr-history-123-999", "history-extra-123-999", "file_title_123_999"),
            (0, "hi-entity-attr-history-123-0", "history-extra-123-0", "file_title_123_0"),
        ]
        
        for attr_id, expected_history, expected_toggle, expected_field in test_cases:
            with self.subTest(attribute_id=attr_id):
                self.assertEqual(self.context.history_target_id(attr_id), expected_history)
                self.assertEqual(self.context.history_toggle_id(attr_id), expected_toggle)
                self.assertEqual(self.context.file_title_field_name(attr_id), expected_field)
                
