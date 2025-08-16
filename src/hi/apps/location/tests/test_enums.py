import logging

from hi.apps.location.enums import LocationViewType, SvgItemType, SvgStyleName
from hi.apps.entity.enums import EntityStateType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestLocationViewType(BaseTestCase):

    def test_location_view_type_entity_state_priority_lists(self):
        """Test entity state type priority lists - critical for sensor display ordering."""
        # DEFAULT should have comprehensive list
        default_priorities = LocationViewType.DEFAULT.entity_state_type_priority_list
        self.assertGreater(len(default_priorities), 5)
        self.assertIn(EntityStateType.MOVEMENT, default_priorities)
        self.assertIn(EntityStateType.TEMPERATURE, default_priorities)
        
        # SECURITY should focus on security-related states
        security_priorities = LocationViewType.SECURITY.entity_state_type_priority_list
        self.assertIn(EntityStateType.MOVEMENT, security_priorities)
        self.assertIn(EntityStateType.PRESENCE, security_priorities)
        self.assertIn(EntityStateType.OPEN_CLOSE, security_priorities)
        
        # CLIMATE should focus on climate-related states
        climate_priorities = LocationViewType.CLIMATE.entity_state_type_priority_list
        self.assertIn(EntityStateType.TEMPERATURE, climate_priorities)
        self.assertIn(EntityStateType.HUMIDITY, climate_priorities)
        self.assertIn(EntityStateType.AIR_PRESSURE, climate_priorities)
        
        # SUPPRESS should have empty list
        suppress_priorities = LocationViewType.SUPPRESS.entity_state_type_priority_list
        self.assertEqual(len(suppress_priorities), 0)
        return

    def test_location_view_type_specialization_logic(self):
        """Test view type specialization - business logic for filtering sensor types."""
        # Each view type should have unique focus
        view_types = [
            (LocationViewType.SECURITY, [EntityStateType.MOVEMENT, EntityStateType.PRESENCE]),
            (LocationViewType.LIGHTS, [EntityStateType.LIGHT_LEVEL]),
            (LocationViewType.SOUNDS, [EntityStateType.SOUND_LEVEL]),
            (LocationViewType.ENERGY, [EntityStateType.ELECTRIC_USAGE, EntityStateType.WATER_FLOW]),
        ]
        
        for view_type, expected_states in view_types:
            with self.subTest(view_type=view_type):
                priorities = view_type.entity_state_type_priority_list
                for expected_state in expected_states:
                    self.assertIn(expected_state, priorities)
        return

    def test_location_view_type_labels(self):
        """Test LocationViewType labels - important for UI display."""
        self.assertEqual(LocationViewType.DEFAULT.label, 'Default')
        self.assertEqual(LocationViewType.SECURITY.label, 'Security')
        self.assertEqual(LocationViewType.LIGHTS.label, 'Lights')
        self.assertEqual(LocationViewType.CLIMATE.label, 'Climate')
        self.assertEqual(LocationViewType.ENERGY.label, 'Energy')
        self.assertEqual(LocationViewType.SUPPRESS.label, 'Suppress')
        return


class TestSvgItemType(BaseTestCase):

    def test_svg_item_type_classification_properties(self):
        """Test SvgItemType classification logic - critical for SVG rendering."""
        # ICON should be icon, not path
        self.assertTrue(SvgItemType.ICON.is_icon)
        self.assertFalse(SvgItemType.ICON.is_path)
        self.assertFalse(SvgItemType.ICON.is_path_closed)
        
        # OPEN_PATH should be path, not icon, not closed
        self.assertFalse(SvgItemType.OPEN_PATH.is_icon)
        self.assertTrue(SvgItemType.OPEN_PATH.is_path)
        self.assertFalse(SvgItemType.OPEN_PATH.is_path_closed)
        
        # CLOSED_PATH should be path, not icon, and closed
        self.assertFalse(SvgItemType.CLOSED_PATH.is_icon)
        self.assertTrue(SvgItemType.CLOSED_PATH.is_path)
        self.assertTrue(SvgItemType.CLOSED_PATH.is_path_closed)
        return

    def test_svg_item_type_path_detection_logic(self):
        """Test is_path property logic - critical for SVG path processing."""
        path_types = [SvgItemType.OPEN_PATH, SvgItemType.CLOSED_PATH]
        non_path_types = [SvgItemType.ICON]
        
        for svg_type in path_types:
            with self.subTest(svg_type=svg_type):
                self.assertTrue(svg_type.is_path)
        
        for svg_type in non_path_types:
            with self.subTest(svg_type=svg_type):
                self.assertFalse(svg_type.is_path)
        return

    def test_svg_item_type_labels(self):
        """Test SvgItemType labels - important for UI display."""
        self.assertEqual(SvgItemType.ICON.label, 'Icon')
        self.assertEqual(SvgItemType.OPEN_PATH.label, 'Open Path ')
        self.assertEqual(SvgItemType.CLOSED_PATH.label, 'Closed Path ')
        return


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
        
    def test_location_view_type_filtering_behavior(self):
        """Test how view types would filter entity states in real scenarios."""
        # Test that specialized views are truly subsets of DEFAULT
        default_states = set(LocationViewType.DEFAULT.entity_state_type_priority_list)
        
        specialized_views = [
            LocationViewType.SECURITY, LocationViewType.LIGHTS, LocationViewType.SOUNDS,
            LocationViewType.CLIMATE, LocationViewType.ENERGY
        ]
        
        for view_type in specialized_views:
            view_states = set(view_type.entity_state_type_priority_list)
            # Each specialized view should be a subset of DEFAULT
            self.assertTrue(view_states.issubset(default_states),
                            f'{view_type} states should be subset of DEFAULT states')
            
            # Specialized views should have fewer states than DEFAULT
            self.assertLess(len(view_states), len(default_states),
                            f'{view_type} should filter down from DEFAULT')
        
        # Test that LIGHTS view only includes lighting-related states
        lights_states = set(LocationViewType.LIGHTS.entity_state_type_priority_list)
        non_lighting_states = {EntityStateType.MOVEMENT, EntityStateType.ELECTRIC_USAGE,
                               EntityStateType.TEMPERATURE, EntityStateType.WATER_FLOW}
        
        # LIGHTS should not include non-lighting states
        intersection = lights_states.intersection(non_lighting_states)
        self.assertEqual(len(intersection), 0,
                         'LIGHTS view should not include non-lighting entity states')
        return
        
    def test_enum_string_conversion_consistency(self):
        """Test enum string representations work correctly for database storage."""
        # Test LocationViewType string conversion
        view_types = [LocationViewType.DEFAULT, LocationViewType.SECURITY,
                      LocationViewType.CLIMATE, LocationViewType.SUPPRESS]
        
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
