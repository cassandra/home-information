"""
Tests for attribute template filters and tags.

Focuses on high-value business logic: attribute preview generation with multiline
truncation, template filter integration, and URL generation logic.
"""
import logging
from unittest.mock import patch
from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase

from hi.apps.attribute.templatetags.attribute_extras import (
    attribute_preview, file_title_field_name, history_target_id, 
    history_toggle_id, attr_history_url, attr_restore_url
)
from hi.apps.attribute.edit_context import AttributeEditContext

logging.disable(logging.CRITICAL)


class MockOwner:
    """Simple mock owner for testing template tags without Django model dependencies."""
    
    def __init__(self, id, name):
        self.id = id
        self.name = name


class TestAttributePreviewFilter(TestCase):
    """Test the attribute_preview filter - complex text processing logic."""
    
    def test_attribute_preview_empty_and_none_values(self):
        """Test preview filter handles empty/none values - edge case handling."""
        self.assertEqual(attribute_preview(None), "(empty)")
        self.assertEqual(attribute_preview(""), "(empty)")
        self.assertEqual(attribute_preview("   "), "   ")  # Whitespace is preserved
        
    def test_attribute_preview_single_line_within_limit(self):
        """Test preview with single line within character limit - basic case."""
        short_text = "This is a short line"
        self.assertEqual(attribute_preview(short_text), short_text)
        self.assertEqual(attribute_preview(short_text, 100), short_text)
        
    def test_attribute_preview_single_line_exceeds_limit(self):
        """Test preview with single line exceeding character limit - truncation logic."""
        long_text = "This is a very long line that exceeds the default character limit of sixty chars"
        
        # Default limit (60 chars) - text is 80 chars long
        preview = attribute_preview(long_text)
        self.assertTrue(preview.startswith("This is a very long line that exceeds the default charac"))
        self.assertIn("... +20 char", preview)  # 80 - 60 = 20 extra chars
        self.assertIn("...", preview)
        
        # Custom limit
        preview_custom = attribute_preview(long_text, 20)
        self.assertTrue(preview_custom.startswith("This is a very long "))
        self.assertIn("chars", preview_custom)
        self.assertIn("+60 char", preview_custom)  # 80 - 20 = 60 extra chars
        
    def test_attribute_preview_multiline_basic(self):
        """Test preview with multiple lines - multiline indicator logic."""
        multiline_text = "First line\nSecond line\nThird line"
        
        preview = attribute_preview(multiline_text)
        self.assertEqual(preview, "First line ... +2 lines")
        
    def test_attribute_preview_multiline_with_truncation(self):
        """Test preview with long first line and multiple lines - complex indicator logic."""
        complex_text = "This is a very long first line that exceeds the character limit\nSecond line\nThird line"
        
        preview = attribute_preview(complex_text, 30)
        self.assertTrue(preview.startswith("This is a very long first line"))
        self.assertIn("... +", preview)
        self.assertIn("chars", preview)
        self.assertIn("lines", preview)
        
    def test_attribute_preview_multiline_empty_lines(self):
        """Test preview with empty lines in multiline text - edge case handling."""
        text_with_empty = "First line\n\n\nFourth line"
        
        preview = attribute_preview(text_with_empty)
        self.assertEqual(preview, "First line ... +3 lines")
        
    def test_attribute_preview_exact_limit_boundary(self):
        """Test preview with text exactly at character limit - boundary condition."""
        exactly_60_chars = "A" * 60  # Exactly 60 characters
        
        preview = attribute_preview(exactly_60_chars)
        self.assertEqual(preview, exactly_60_chars)  # Should not truncate
        
        sixty_one_chars = "A" * 61  # One character over
        preview_over = attribute_preview(sixty_one_chars)
        self.assertTrue(preview_over.endswith("... +1 char"))
        
    def test_attribute_preview_singular_vs_plural_indicators(self):
        """Test correct singular/plural forms in indicators - text processing logic."""
        # Single extra line
        single_extra_line = "First line\nSecond line"
        preview = attribute_preview(single_extra_line)
        self.assertIn("+1 line", preview)  # Singular
        self.assertNotIn("lines", preview)
        
        # Multiple extra lines
        multiple_extra_lines = "First\nSecond\nThird\nFourth"
        preview_multi = attribute_preview(multiple_extra_lines)
        self.assertIn("+3 lines", preview_multi)  # Plural
        
        # Single extra character
        single_char_over = "A" * 61
        preview_char = attribute_preview(single_char_over, 60)
        self.assertIn("+1 char", preview_char)  # Singular
        
    def test_attribute_preview_non_string_input(self):
        """Test preview filter with non-string input - type handling."""
        # Should convert to string
        self.assertEqual(attribute_preview(123), "123")
        self.assertEqual(attribute_preview(True), "True")
        self.assertEqual(attribute_preview([1, 2, 3]), "[1, 2, 3]")


class TestAttributeContextFilters(TestCase):
    """Test filters that work with AttributeEditContext objects."""
    
    def setUp(self):
        self.mock_owner = MockOwner(id=123, name="Test Owner")
        self.context = AttributeEditContext(self.mock_owner, "entity")
        self.attribute_id = 456
        
    def test_file_title_field_name_filter(self):
        """Test file_title_field_name filter delegates to context method."""
        result = file_title_field_name(self.context, self.attribute_id)
        expected = self.context.file_title_field_name(self.attribute_id)
        self.assertEqual(result, expected)
        self.assertEqual(result, "file_title_123_456")
        
    def test_history_target_id_filter(self):
        """Test history_target_id filter delegates to context method."""
        result = history_target_id(self.context, self.attribute_id)
        expected = self.context.history_target_id(self.attribute_id)
        self.assertEqual(result, expected)
        self.assertEqual(result, "hi-entity-attr-history-123-456")
        
    def test_history_toggle_id_filter(self):
        """Test history_toggle_id filter delegates to context method."""
        result = history_toggle_id(self.context, self.attribute_id)
        expected = self.context.history_toggle_id(self.attribute_id)
        self.assertEqual(result, expected)
        self.assertEqual(result, "history-extra-123-456")


class TestAttributeUrlTags(TestCase):
    """Test template tags that generate URLs - URL construction logic."""
    
    def setUp(self):
        self.mock_owner = MockOwner(id=123, name="Test Owner")
        self.context = AttributeEditContext(self.mock_owner, "entity")
        self.attribute_id = 456
        self.history_id = 789
        
    @patch('django.urls.reverse')
    def test_attr_history_url_tag_basic(self, mock_reverse):
        """Test attr_history_url tag constructs correct URL parameters."""
        mock_reverse.return_value = "/entity/123/attribute/456/history/"
        
        result = attr_history_url(self.context, self.attribute_id)
        
        # Should call reverse with correct parameters
        mock_reverse.assert_called_once_with(
            "entity_attribute_history_inline",
            kwargs={
                'entity_id': 123,
                'attribute_id': 456
            }
        )
        self.assertEqual(result, "/entity/123/attribute/456/history/")
        
    @patch('django.urls.reverse')
    def test_attr_restore_url_tag_basic(self, mock_reverse):
        """Test attr_restore_url tag constructs correct URL parameters."""
        mock_reverse.return_value = "/entity/123/attribute/456/restore/789/"
        
        result = attr_restore_url(self.context, self.attribute_id, self.history_id)
        
        # Should call reverse with correct parameters
        mock_reverse.assert_called_once_with(
            "entity_attribute_restore_inline",
            kwargs={
                'entity_id': 123,
                'attribute_id': 456,
                'history_id': 789
            }
        )
        self.assertEqual(result, "/entity/123/attribute/456/restore/789/")
        
    @patch('django.urls.reverse')
    def test_attr_history_url_tag_different_owner_types(self, mock_reverse):
        """Test URL tags work correctly with different owner types."""
        location_context = AttributeEditContext(self.mock_owner, "location")
        mock_reverse.return_value = "/location/123/attribute/456/history/"
        
        result = attr_history_url(location_context, self.attribute_id)
        
        # Should use location-specific URL name and parameter
        mock_reverse.assert_called_once_with(
            "location_attribute_history_inline",
            kwargs={
                'location_id': 123,
                'attribute_id': 456
            }
        )
        self.assertEqual(result, "/location/123/attribute/456/history/")
        
    @patch('django.urls.reverse')
    def test_url_tags_handle_reverse_exceptions(self, mock_reverse):
        """Test URL tags handle Django reverse() exceptions gracefully."""
        from django.urls import NoReverseMatch
        mock_reverse.side_effect = NoReverseMatch("URL pattern not found")
        
        # Tags should propagate the exception (Django template system will handle it)
        with self.assertRaises(NoReverseMatch):
            attr_history_url(self.context, self.attribute_id)
            
        with self.assertRaises(NoReverseMatch):
            attr_restore_url(self.context, self.attribute_id, self.history_id)


class TestTemplateIntegration(TestCase):
    """Test template filters and tags integrated with Django template system."""
    
    def setUp(self):
        self.mock_owner = MockOwner(id=123, name="Test Owner")
        self.context = AttributeEditContext(self.mock_owner, "entity")
        
    def test_attribute_preview_filter_in_template(self):
        """Test attribute_preview filter works in actual template rendering."""
        template_str = """
        {% load attribute_extras %}
        Preview: {{ value|attribute_preview:30 }}
        """
        
        template = Template(template_str)
        
        # Test with long multiline value
        long_value = "This is a very long first line that will be truncated\nSecond line\nThird line"
        context = Context({'value': long_value})
        
        rendered = template.render(context).strip()
        self.assertIn("Preview:", rendered)
        self.assertIn("...", rendered)
        self.assertIn("chars", rendered)
        self.assertIn("lines", rendered)
        
    def test_context_filters_in_template(self):
        """Test AttributeEditContext filters work in template rendering."""
        template_str = """
        {% load attribute_extras %}
        Field: {{ attr_context|file_title_field_name:attribute_id }}
        Target: {{ attr_context|history_target_id:attribute_id }}
        Toggle: {{ attr_context|history_toggle_id:attribute_id }}
        """
        
        template = Template(template_str)
        context = Context({
            'attr_context': self.context,
            'attribute_id': 456
        })
        
        rendered = template.render(context)
        self.assertIn("Field: file_title_123_456", rendered)
        self.assertIn("Target: hi-entity-attr-history-123-456", rendered)
        self.assertIn("Toggle: history-extra-123-456", rendered)
        
    @patch('django.urls.reverse')
    def test_url_tags_in_template(self, mock_reverse):
        """Test URL tags work in actual template rendering."""
        mock_reverse.side_effect = lambda name, kwargs: f"/{name.replace('_', '/')}/{kwargs.get('entity_id', 0)}/{kwargs.get('attribute_id', 0)}/"
        
        template_str = """
        {% load attribute_extras %}
        History: {% attr_history_url attr_context attribute_id %}
        Restore: {% attr_restore_url attr_context attribute_id history_id %}
        """
        
        template = Template(template_str)
        context = Context({
            'attr_context': self.context,
            'attribute_id': 456,
            'history_id': 789
        })
        
        rendered = template.render(context)
        self.assertIn("History:", rendered)
        self.assertIn("Restore:", rendered)
        
    def test_template_syntax_error_handling(self):
        """Test template tags handle syntax errors appropriately."""
        # Missing required argument should raise TemplateSyntaxError
        invalid_template = """
        {% load attribute_extras %}
        {% attr_history_url %}
        """
        
        # Django template system should catch argument errors
        with self.assertRaises((TemplateSyntaxError, TypeError)):
            template = Template(invalid_template)
            context = Context({})
            template.render(context)
            
    def test_template_with_none_context_values(self):
        """Test template filters handle None context values gracefully."""
        template_str = """
        {% load attribute_extras %}
        Preview: {{ none_value|attribute_preview }}
        """
        
        template = Template(template_str)
        context = Context({
            'none_value': None,
        })
        
        # Should handle None values without crashing
        rendered = template.render(context)
        self.assertIn("Preview: (empty)", rendered)
        
        # Test that filter with None context raises AttributeError as expected
        template_str_error = """
        {% load attribute_extras %}
        Field: {{ none_context|file_title_field_name:123 }}
        """
        
        template_error = Template(template_str_error)
        context_error = Context({'none_context': None})
        
        # This should raise an AttributeError which Django templates handle
        with self.assertRaises(AttributeError):
            template_error.render(context_error)
            
