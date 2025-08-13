import logging

from hi.apps.event.enums import EventType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEventType(BaseTestCase):

    def test_event_type_enum_values(self):
        """Test EventType enum values - critical for event classification."""
        # Test that expected event types exist
        expected_types = {
            EventType.SECURITY,
            EventType.MAINTENANCE,
            EventType.INFORMATION,
            EventType.AUTOMATION
        }
        
        actual_types = set(EventType)
        self.assertEqual(actual_types, expected_types)
        return

    def test_event_type_string_conversion(self):
        """Test EventType string conversion - critical for database storage."""
        # Test that enum converts to expected string values
        self.assertEqual(str(EventType.SECURITY), 'security')
        self.assertEqual(str(EventType.MAINTENANCE), 'maintenance')
        self.assertEqual(str(EventType.INFORMATION), 'information')
        self.assertEqual(str(EventType.AUTOMATION), 'automation')
        return
