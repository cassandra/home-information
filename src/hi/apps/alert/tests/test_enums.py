import logging

from hi.apps.alert.enums import AlarmLevel, AlarmSource, AlertState
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlarmLevel(BaseTestCase):

    def test_alarm_level_priority_ordering(self):
        """Test AlarmLevel priority ordering - critical for alert prioritization."""
        # Test that priorities are in correct order
        self.assertLess(AlarmLevel.NONE.priority, AlarmLevel.INFO.priority)
        self.assertLess(AlarmLevel.INFO.priority, AlarmLevel.WARNING.priority)
        self.assertLess(AlarmLevel.WARNING.priority, AlarmLevel.CRITICAL.priority)
        
        # Test specific priority values
        self.assertEqual(AlarmLevel.NONE.priority, 0)
        self.assertEqual(AlarmLevel.INFO.priority, 10)
        self.assertEqual(AlarmLevel.WARNING.priority, 100)
        self.assertEqual(AlarmLevel.CRITICAL.priority, 1000)
        return

    def test_alarm_level_labels(self):
        """Test AlarmLevel labels - important for UI display."""
        self.assertEqual(AlarmLevel.NONE.label, 'None')
        self.assertEqual(AlarmLevel.INFO.label, 'Info')
        self.assertEqual(AlarmLevel.WARNING.label, 'Warning')
        self.assertEqual(AlarmLevel.CRITICAL.label, 'Critical')
        return


class TestAlarmSource(BaseTestCase):

    def test_alarm_source_enum_values(self):
        """Test AlarmSource enum values - critical for alarm categorization."""
        self.assertEqual(AlarmSource.EVENT.label, 'Event')
        
        # Should have proper enum behavior
        self.assertIsInstance(AlarmSource.EVENT, AlarmSource)
        return


class TestAlertState(BaseTestCase):

    def test_alert_state_priority_ordering(self):
        """Test AlertState priority ordering - critical for state prioritization."""
        # Test that priorities are in correct ascending order
        
        # Verify specific critical priorities
        self.assertEqual(AlertState.ERROR.priority, -12)
        self.assertEqual(AlertState.ENABLED.priority, 0)
        self.assertEqual(AlertState.INFO.priority, 10)
        self.assertEqual(AlertState.ALERT.priority, 100)
        self.assertEqual(AlertState.ALARM.priority, 1000)
        
        # Test that INFO_RECENT < INFO
        self.assertLess(AlertState.INFO_RECENT.priority, AlertState.INFO.priority)
        
        # Test that ALERT_RECENT < ALERT
        self.assertLess(AlertState.ALERT_RECENT.priority, AlertState.ALERT.priority)
        
        # Test that ALARM_RECENT < ALARM
        self.assertLess(AlertState.ALARM_RECENT.priority, AlertState.ALARM.priority)
        return

    def test_alert_state_get_recent_variant_logic(self):
        """Test get_recent_variant static method - complex business logic for state transitions."""
        # Test conversion to recent variants
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.INFO),
            AlertState.INFO_RECENT
        )
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.ALERT),
            AlertState.ALERT_RECENT
        )
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.ALARM),
            AlertState.ALARM_RECENT
        )
        
        # Test states that don't have recent variants return unchanged
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.ENABLED),
            AlertState.ENABLED
        )
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.DISABLED),
            AlertState.DISABLED
        )
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.ERROR),
            AlertState.ERROR
        )
        
        # Test that recent variants don't have further variants (return unchanged)
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.INFO_RECENT),
            AlertState.INFO_RECENT
        )
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.ALERT_RECENT),
            AlertState.ALERT_RECENT
        )
        self.assertEqual(
            AlertState.get_recent_variant(AlertState, AlertState.ALARM_RECENT),
            AlertState.ALARM_RECENT
        )
        return

    def test_alert_state_labels(self):
        """Test AlertState labels - important for UI display."""
        # Test key labels that would be displayed to users
        self.assertEqual(AlertState.ERROR.label, 'Error')
        self.assertEqual(AlertState.ENABLED.label, 'Enabled')
        self.assertEqual(AlertState.DISABLED.label, 'Disabled')
        self.assertEqual(AlertState.INFO.label, 'Info')
        self.assertEqual(AlertState.INFO_RECENT.label, 'Info (recent)')
        self.assertEqual(AlertState.ALERT.label, 'Alert')
        self.assertEqual(AlertState.ALERT_RECENT.label, 'Alert (recent)')
        self.assertEqual(AlertState.ALARM.label, 'Alarm')
        self.assertEqual(AlertState.ALARM_RECENT.label, 'Alarm (recent)')
        return
