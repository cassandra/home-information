"""
Cross-owner template compatibility tests.

Verifies that Entity and Location AttributeEditContext implementations work
identically with the same generic templates, ensuring true template generalization.
"""
import logging
from unittest.mock import patch
from hi.apps.entity.entity_attribute_edit_context import EntityAttributeEditContext
from hi.apps.location.location_attribute_edit_context import LocationAttributeEditContext
from hi.apps.entity.tests.synthetic_data import EntityAttributeSyntheticData
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestCrossOwnerTemplateCompatibility(BaseTestCase):
    """Test that Entity and Location contexts work identically with generic templates."""
    
    def setUp(self):
        super().setUp()
        # Create test entities and locations
        self.entity = EntityAttributeSyntheticData.create_test_entity(name="Test Entity")
        self.location = LocationSyntheticData.create_test_location(name="Test Location")
        
        # Create corresponding contexts
        self.entity_context = EntityAttributeEditContext(self.entity)
        self.location_context = LocationAttributeEditContext(self.location)
        
    def test_context_interface_consistency(self):
        """Test both contexts provide identical interface - API compatibility."""
        # Both contexts should have same methods and properties
        entity_methods = set(dir(self.entity_context))
        location_methods = set(dir(self.location_context))
        
        # Should have identical public interface except for the typed property accessors
        public_entity_methods = {m for m in entity_methods if not m.startswith('_')}
        public_location_methods = {m for m in location_methods if not m.startswith('_')}
        
        # Remove the unique typed accessors for comparison
        public_entity_methods.discard('entity')
        public_location_methods.discard('location')
        
        self.assertEqual(public_entity_methods, public_location_methods)
        
    def test_url_pattern_consistency(self):
        """Test URL patterns follow same structure across owner types - routing compatibility."""
        # URL name patterns should be consistent
        self.assertEqual(
            self.entity_context.history_url_name,
            "entity_attribute_history_inline"
        )
        self.assertEqual(
            self.location_context.history_url_name,
            "location_attribute_history_inline"
        )
        
        # Parameter name patterns should be consistent
        self.assertEqual(
            self.entity_context.owner_id_param_name,
            "entity_id"
        )
        self.assertEqual(
            self.location_context.owner_id_param_name,
            "location_id"
        )
        
    def test_dom_id_pattern_consistency(self):
        """Test DOM ID generation follows same patterns - JavaScript compatibility."""
        attribute_id = 123
        
        # History target IDs should follow same pattern
        entity_history = self.entity_context.history_target_id(attribute_id)
        location_history = self.location_context.history_target_id(attribute_id)
        
        # Both should follow pattern: hi-{type}-attr-history-{owner_id}-{attr_id}
        self.assertRegex(entity_history, r'^hi-entity-attr-history-\d+-123$')
        self.assertRegex(location_history, r'^hi-location-attr-history-\d+-123$')
        
        # Toggle IDs should follow same pattern (no owner type in these)
        entity_toggle = self.entity_context.history_toggle_id(attribute_id)
        location_toggle = self.location_context.history_toggle_id(attribute_id)
        
        # Both should follow pattern: history-extra-{owner_id}-{attr_id}
        self.assertRegex(entity_toggle, r'^history-extra-\d+-123$')
        self.assertRegex(location_toggle, r'^history-extra-\d+-123$')
        
    def test_form_field_naming_consistency(self):
        """Test form field naming follows same patterns - form compatibility."""
        attribute_id = 456
        
        entity_field = self.entity_context.file_title_field_name(attribute_id)
        location_field = self.location_context.file_title_field_name(attribute_id)
        
        # Both should follow pattern: file_title_{owner_id}_{attr_id}
        self.assertRegex(entity_field, r'^file_title_\d+_456$')
        self.assertRegex(location_field, r'^file_title_\d+_456$')
        
    def test_template_context_structure_compatibility(self):
        """Test template contexts have same structure - template compatibility."""
        entity_context = self.entity_context.to_template_context()
        location_context = self.location_context.to_template_context()
        
        # Should have same set of keys (except for owner-specific ones)
        entity_keys = set(entity_context.keys())
        location_keys = set(location_context.keys())
        
        # Common keys that both should have
        common_keys = {'attr_context', 'owner'}
        self.assertTrue(common_keys.issubset(entity_keys))
        self.assertTrue(common_keys.issubset(location_keys))
        
        # Entity context should have 'entity' key, Location should have 'location' key
        self.assertIn('entity', entity_keys)
        self.assertNotIn('location', entity_keys)
        
        self.assertIn('location', location_keys)
        self.assertNotIn('entity', location_keys)
        
    def test_template_context_generic_aliases(self):
        """Test generic aliases work consistently - template abstraction."""
        entity_context = self.entity_context.to_template_context()
        location_context = self.location_context.to_template_context()
        
        # Generic 'owner' should point to correct instance
        self.assertIs(entity_context['owner'], self.entity)
        self.assertIs(location_context['owner'], self.location)
        
        # attr_context should be the context instance itself
        self.assertIs(entity_context['attr_context'], self.entity_context)
        self.assertIs(location_context['attr_context'], self.location_context)
        
    def test_cross_owner_template_filter_compatibility(self):
        """Test template filters work identically with both contexts - filter compatibility."""
        from hi.apps.attribute.templatetags.attribute_extras import (
            file_title_field_name, history_target_id, history_toggle_id
        )
        
        attribute_id = 789
        
        # Template filters should work with both contexts
        entity_field = file_title_field_name(self.entity_context, attribute_id)
        location_field = file_title_field_name(self.location_context, attribute_id)
        
        entity_history = history_target_id(self.entity_context, attribute_id)
        location_history = history_target_id(self.location_context, attribute_id)
        
        entity_toggle = history_toggle_id(self.entity_context, attribute_id)
        location_toggle = history_toggle_id(self.location_context, attribute_id)
        
        # All should produce valid results following same patterns
        self.assertRegex(entity_field, r'^file_title_\d+_789$')
        self.assertRegex(location_field, r'^file_title_\d+_789$')
        
        self.assertRegex(entity_history, r'^hi-entity-attr-history-\d+-789$')
        self.assertRegex(location_history, r'^hi-location-attr-history-\d+-789$')
        
        self.assertRegex(entity_toggle, r'^history-extra-\d+-789$')
        self.assertRegex(location_toggle, r'^history-extra-\d+-789$')
        
    @patch('django.urls.reverse')
    def test_cross_owner_template_tag_compatibility(self, mock_reverse):
        """Test template tags work identically with both contexts - tag compatibility."""
        from hi.apps.attribute.templatetags.attribute_extras import (
            attr_history_url, attr_restore_url
        )
        
        mock_reverse.return_value = '/test/url/'
        attribute_id = 999
        history_id = 111
        
        # History URL tag
        attr_history_url(self.entity_context, attribute_id)
        entity_call = mock_reverse.call_args
        
        mock_reverse.reset_mock()
        attr_history_url(self.location_context, attribute_id)
        location_call = mock_reverse.call_args
        
        # Should use different URL names but same parameter structure
        self.assertEqual(entity_call[0][0], 'entity_attribute_history_inline')
        self.assertEqual(location_call[0][0], 'location_attribute_history_inline')
        
        # Both should have same parameter structure
        entity_kwargs = entity_call[1]['kwargs']
        location_kwargs = location_call[1]['kwargs']
        
        self.assertIn('entity_id', entity_kwargs)
        self.assertIn('attribute_id', entity_kwargs)
        self.assertEqual(entity_kwargs['attribute_id'], attribute_id)
        
        self.assertIn('location_id', location_kwargs)
        self.assertIn('attribute_id', location_kwargs)
        self.assertEqual(location_kwargs['attribute_id'], attribute_id)
        
        # Restore URL tag
        mock_reverse.reset_mock()
        attr_restore_url(self.entity_context, attribute_id, history_id)
        entity_restore_call = mock_reverse.call_args
        
        mock_reverse.reset_mock()
        attr_restore_url(self.location_context, attribute_id, history_id)
        location_restore_call = mock_reverse.call_args
        
        # Should follow same pattern with history_id parameter
        entity_restore_kwargs = entity_restore_call[1]['kwargs']
        location_restore_kwargs = location_restore_call[1]['kwargs']
        
        self.assertEqual(entity_restore_kwargs['history_id'], history_id)
        self.assertEqual(location_restore_kwargs['history_id'], history_id)
        
    def test_context_property_computation_consistency(self):
        """Test property computation follows same logic - computation compatibility."""
        # Test various attribute IDs with both contexts
        test_attribute_ids = [1, 100, 999, 0]
        
        for attr_id in test_attribute_ids:
            with self.subTest(attribute_id=attr_id):
                # History target IDs should follow same computation
                entity_history = self.entity_context.history_target_id(attr_id)
                location_history = self.location_context.history_target_id(attr_id)
                
                # Both should include owner ID and attribute ID
                self.assertIn(str(self.entity.id), entity_history)
                self.assertIn(str(attr_id), entity_history)
                
                self.assertIn(str(self.location.id), location_history)
                self.assertIn(str(attr_id), location_history)
                
                # Toggle IDs should be computed identically (no owner type)
                entity_toggle = self.entity_context.history_toggle_id(attr_id)
                location_toggle = self.location_context.history_toggle_id(attr_id)
                
                # Structure should be identical (just different owner IDs)
                entity_parts = entity_toggle.split('-')
                location_parts = location_toggle.split('-')
                
                self.assertEqual(len(entity_parts), len(location_parts))
                self.assertEqual(entity_parts[0], location_parts[0])  # 'history'
                self.assertEqual(entity_parts[1], location_parts[1])  # 'extra'
                self.assertEqual(entity_parts[3], location_parts[3])  # attribute_id
                
    def test_inheritance_hierarchy_consistency(self):
        """Test both contexts inherit from same base class - inheritance compatibility."""
        from hi.apps.attribute.edit_context import AttributeEditContext
        
        self.assertIsInstance(self.entity_context, AttributeEditContext)
        self.assertIsInstance(self.location_context, AttributeEditContext)
        
        # Both should inherit all base methods
        base_methods = [m for m in dir(AttributeEditContext) if not m.startswith('_')]
        
        for method in base_methods:
            with self.subTest(method=method):
                self.assertTrue(hasattr(self.entity_context, method))
                self.assertTrue(hasattr(self.location_context, method))
                
    def test_typed_property_accessors(self):
        """Test typed property accessors work correctly - type safety."""
        # Entity context should provide typed entity accessor
        self.assertIs(self.entity_context.entity, self.entity)
        self.assertEqual(self.entity_context.entity.name, "Test Entity")
        
        # Location context should provide typed location accessor
        self.assertIs(self.location_context.location, self.location)
        self.assertEqual(self.location_context.location.name, "Test Location")
        
        # Both should also work through generic owner property
        self.assertIs(self.entity_context.owner, self.entity)
        self.assertIs(self.location_context.owner, self.location)
        
    def test_edge_case_compatibility(self):
        """Test edge cases work consistently across both contexts - robustness compatibility."""
        # Test with special characters in names
        special_entity = EntityAttributeSyntheticData.create_test_entity(
            name="Entity with & symbols!"
        )
        special_location = LocationSyntheticData.create_test_location(
            name="Location with & symbols!"
        )
        
        entity_ctx = EntityAttributeEditContext(special_entity)
        location_ctx = LocationAttributeEditContext(special_location)
        
        # Both should handle special characters in names
        self.assertEqual(entity_ctx.owner_name, "Entity with & symbols!")
        self.assertEqual(location_ctx.owner_name, "Location with & symbols!")
        
        # DOM IDs should still be generated properly
        entity_id = entity_ctx.history_target_id(1)
        location_id = location_ctx.history_target_id(1)
        
        self.assertIn("hi-entity-attr-history", entity_id)
        self.assertIn("hi-location-attr-history", location_id)
        
    def test_template_generalization_effectiveness(self):
        """Test that template generalization actually works - integration verification."""
        # This test verifies that the same template code can work with both contexts
        
        # Simulate template context usage
        entity_template_ctx = self.entity_context.to_template_context()
        location_template_ctx = self.location_context.to_template_context()
        
        # Both contexts should allow the same template operations
        # Template would access: {{ owner.name }}, {{ attr_context.owner_id }}, etc.
        
        # Generic owner access
        self.assertEqual(entity_template_ctx['owner'].name, "Test Entity")
        self.assertEqual(location_template_ctx['owner'].name, "Test Location")
        
        # Context property access
        self.assertIsInstance(entity_template_ctx['attr_context'].owner_id, int)
        self.assertIsInstance(location_template_ctx['attr_context'].owner_id, int)
        
        # URL parameter access
        self.assertEqual(entity_template_ctx['attr_context'].owner_id_param_name, "entity_id")
        self.assertEqual(location_template_ctx['attr_context'].owner_id_param_name, "location_id")
        
        # This demonstrates that a template using these patterns would work identically
        # with both Entity and Location contexts, achieving true generalization
        
