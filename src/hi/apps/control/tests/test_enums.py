import logging

from hi.apps.control.enums import ControllerType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestControllerType(BaseTestCase):

    def test_controller_type_default_value(self):
        """Test ControllerType DEFAULT enum - critical for controller behavior."""
        # Should have DEFAULT type
        self.assertEqual(ControllerType.DEFAULT.label, 'Default')
        self.assertEqual(str(ControllerType.DEFAULT), 'default')
        return

    def test_controller_type_from_name_safe(self):
        """Test from_name_safe method - critical for string conversion."""
        # Should convert string to enum safely
        controller_type = ControllerType.from_name_safe('default')
        self.assertEqual(controller_type, ControllerType.DEFAULT)
        
        # Should handle invalid strings by returning default
        invalid_type = ControllerType.from_name_safe('invalid')
        self.assertEqual(invalid_type, ControllerType.DEFAULT)  # Returns default, not None
        return
