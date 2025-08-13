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
