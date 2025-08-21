import logging

from hi.apps.console.enums import Theme, DisplayUnits
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestTheme(BaseTestCase):

    def test_theme_enum_values(self):
        """Test Theme enum values - important for UI consistency."""
        self.assertEqual(Theme.DEFAULT.label, 'Default')
        
        # Should have proper enum behavior
        self.assertIsInstance(Theme.DEFAULT, Theme)
        return


class TestDisplayUnits(BaseTestCase):

    def test_display_units_enum_values(self):
        """Test DisplayUnits enum values - critical for measurement display."""
        self.assertEqual(DisplayUnits.IMPERIAL.label, 'Imperial')
        self.assertEqual(DisplayUnits.METRIC.label, 'Metric')
        
        # Should have proper enum behavior
        self.assertIsInstance(DisplayUnits.IMPERIAL, DisplayUnits)
        self.assertIsInstance(DisplayUnits.METRIC, DisplayUnits)
        return

    def test_display_units_completeness(self):
        """Test DisplayUnits covers expected measurement systems - critical for internationalization."""
        # Should have both major measurement systems
        units_list = list(DisplayUnits)
        self.assertEqual(len(units_list), 2)
        self.assertIn(DisplayUnits.IMPERIAL, units_list)
        self.assertIn(DisplayUnits.METRIC, units_list)
        return
