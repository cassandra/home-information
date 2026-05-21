import logging

from hi.apps.event.enums import EventClauseOperator, EventType
from hi.testing.base_test_case import BaseTestCase

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


class TestEventClauseOperatorIsNumeric(BaseTestCase):
    """``is_numeric`` is the load-bearing predicate the form, the JS
    widget swap (via ``data-numeric-ops``), and the matcher all key
    off of. A mistake here misclassifies an operator and silently
    breaks the form's value-validation gate."""

    def test_numeric_operators_are_numeric(self):
        for op in (
                EventClauseOperator.LT, EventClauseOperator.LTE,
                EventClauseOperator.GT, EventClauseOperator.GTE ):
            with self.subTest( op = op ):
                self.assertTrue( op.is_numeric )
            continue
        return

    def test_discrete_operators_are_not_numeric(self):
        for op in (
                EventClauseOperator.EQ,
                EventClauseOperator.NEQ,
                EventClauseOperator.IN ):
            with self.subTest( op = op ):
                self.assertFalse( op.is_numeric )
            continue
        return
