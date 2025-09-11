import logging

from hi.apps.location.enums import LocationViewType, SvgStyleName
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSvgStyleName(BaseTestCase):

    def test_svg_style_name_template_generation(self):
        """Test template name generation - critical for SVG styling."""
        # Test template name generation logic
        color_template = SvgStyleName.COLOR.svg_defs_template_name
        greyscale_template = SvgStyleName.GREYSCALE.svg_defs_template_name
        
        self.assertEqual(color_template, 'location/panes/svg_fill_patterns_color.html')
        self.assertEqual(greyscale_template, 'location/panes/svg_fill_patterns_greyscale.html')
        
        # Templates should be different
        self.assertNotEqual(color_template, greyscale_template)
        return

    def test_svg_style_name_css_file_generation(self):
        """Test CSS file name generation - critical for styling."""
        # Test CSS file name generation logic
        color_css = SvgStyleName.COLOR.css_static_file_name
        greyscale_css = SvgStyleName.GREYSCALE.css_static_file_name
        
        self.assertEqual(color_css, 'css/svg-location-color.css')
        self.assertEqual(greyscale_css, 'css/svg-location-greyscale.css')
        
        # CSS files should be different
        self.assertNotEqual(color_css, greyscale_css)
        return

    def test_svg_style_name_labels(self):
        """Test SvgStyleName labels - important for UI display."""
        self.assertEqual(SvgStyleName.COLOR.label, 'Color')
        self.assertEqual(SvgStyleName.GREYSCALE.label, 'Grey Scale ')
        return
        
    def test_svg_style_name_template_generation_consistency(self):
        """Test template and CSS file generation follows consistent patterns."""
        all_styles = [SvgStyleName.COLOR, SvgStyleName.GREYSCALE]
        
        # Test template name pattern consistency
        for style in all_styles:
            template_name = style.svg_defs_template_name
            css_file_name = style.css_static_file_name
            
            # Template should follow location/panes/svg_fill_patterns_{style}.html pattern
            expected_template = f'location/panes/svg_fill_patterns_{style}.html'
            self.assertEqual(template_name, expected_template)
            
            # CSS should follow css/svg-location-{style}.css pattern
            expected_css = f'css/svg-location-{style}.css'
            self.assertEqual(css_file_name, expected_css)
            
            # Verify paths use consistent separators and extensions
            self.assertTrue(template_name.startswith('location/panes/'))
            self.assertTrue(template_name.endswith('.html'))
            self.assertTrue(css_file_name.startswith('css/'))
            self.assertTrue(css_file_name.endswith('.css'))
        
        # Verify each style generates unique file paths
        template_names = [style.svg_defs_template_name for style in all_styles]
        css_names = [style.css_static_file_name for style in all_styles]
        
        self.assertEqual(len(set(template_names)), len(all_styles))
        self.assertEqual(len(set(css_names)), len(all_styles))
        return
        
    def test_enum_string_conversion_consistency(self):
        """Test enum string representations work correctly for database storage."""
        # Test LocationViewType string conversion
        view_types = [LocationViewType.DEFAULT, LocationViewType.AUTOMATION]
        
        for view_type in view_types:
            # String representation should be lowercase of enum name
            self.assertEqual(str(view_type), view_type.name.lower())
            
            # from_name_safe should round-trip correctly
            converted = LocationViewType.from_name_safe(str(view_type))
            self.assertEqual(converted, view_type)
        
        # Test SvgStyleName string conversion
        style_names = [SvgStyleName.COLOR, SvgStyleName.GREYSCALE]
        
        for style_name in style_names:
            # String representation should be lowercase of enum name
            self.assertEqual(str(style_name), style_name.name.lower())
            
            # from_name_safe should round-trip correctly
            converted = SvgStyleName.from_name_safe(str(style_name))
            self.assertEqual(converted, style_name)
        
        # Test invalid string handling
        invalid_view_type = LocationViewType.from_name_safe('INVALID_TYPE')
        invalid_style = SvgStyleName.from_name_safe('INVALID_STYLE')
        
        # Should handle invalid strings gracefully (implementation dependent)
        self.assertIsNotNone(invalid_view_type)
        self.assertIsNotNone(invalid_style)
        return
