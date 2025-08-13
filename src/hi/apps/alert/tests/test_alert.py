import logging
from datetime import timedelta

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alert import Alert
from hi.apps.alert.alarm import Alarm
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlert(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.test_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
            title='Test Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        return

    def test_alert_initialization_with_first_alarm(self):
        """Test Alert initialization with first alarm - critical object creation logic."""
        alert = Alert(self.test_alarm)
        
        # Should have proper ID and timing
        self.assertIsNotNone(alert.id)
        self.assertEqual(alert.start_datetime, self.test_alarm.timestamp)
        self.assertEqual(alert.end_datetime, self.test_alarm.timestamp + timedelta(seconds=300))
        
        # Should set up alarm tracking correctly
        self.assertEqual(alert.first_alarm, self.test_alarm)
        self.assertEqual(alert.alarm_count, 1)
        self.assertIn(self.test_alarm, alert.alarm_list)
        self.assertFalse(alert.is_acknowledged)
        return

    def test_alert_signature_matching_logic(self):
        """Test alert signature matching - critical for alarm aggregation."""
        alert = Alert(self.test_alarm)
        
        # Create matching alarm (same signature)
        matching_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',  # Same type
            alarm_level=AlarmLevel.WARNING,  # Same level
            title='Another Test Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        # Create non-matching alarm (different signature)
        non_matching_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='different_alarm',  # Different type
            alarm_level=AlarmLevel.WARNING,
            title='Different Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        self.assertTrue(alert.is_matching_alarm(matching_alarm))
        self.assertFalse(alert.is_matching_alarm(non_matching_alarm))
        return

    def test_alert_add_alarm_aggregation(self):
        """Test adding alarms to alert - complex aggregation logic with deque management."""
        alert = Alert(self.test_alarm)
        initial_end_time = alert.end_datetime
        
        # Create matching alarm
        second_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
            title='Second Test Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=600,  # Different lifetime
            timestamp=datetimeproxy.now(),
        )
        
        alert.add_alarm(second_alarm)
        
        # Should update alarm count and end time
        self.assertEqual(alert.alarm_count, 2)
        self.assertGreater(alert.end_datetime, initial_end_time)
        
        # Should maintain first alarm but add new one
        self.assertEqual(alert.first_alarm, self.test_alarm)
        self.assertIn(second_alarm, alert.alarm_list)
        
        # Latest alarm should be first in list (most recent)
        self.assertEqual(alert.get_latest_alarm(), second_alarm)
        return

    def test_alert_add_alarm_signature_assertion(self):
        """Test add_alarm signature validation - critical error handling."""
        alert = Alert(self.test_alarm)
        
        # Create alarm with different signature
        different_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='different_alarm',  # Different type
            alarm_level=AlarmLevel.WARNING,
            title='Different Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        # Should raise assertion error for signature mismatch
        with self.assertRaises(AssertionError):
            alert.add_alarm(different_alarm)
        return

    def test_alert_title_generation_with_count(self):
        """Test alert title generation logic - business logic for UI display."""
        alert = Alert(self.test_alarm)
        
        # Single alarm should not show count
        expected_title = f'{AlarmLevel.WARNING.label}: Test Alarm'
        self.assertEqual(alert.title, expected_title)
        
        # Add second alarm, should show count
        second_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
            title='Second Test Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        alert.add_alarm(second_alarm)
        expected_title_with_count = f'{AlarmLevel.WARNING.label}: Test Alarm (2)'
        self.assertEqual(alert.title, expected_title_with_count)
        return

    def test_alert_max_alarm_list_size_constraint(self):
        """Test MAX_ALARM_LIST_SIZE constraint - critical for memory management."""
        alert = Alert(self.test_alarm)
        
        # Add alarms up to and beyond the limit
        for i in range(Alert.MAX_ALARM_LIST_SIZE + 5):
            new_alarm = Alarm(
                alarm_source=AlarmSource.EVENT,
                alarm_type='test_alarm',
                alarm_level=AlarmLevel.WARNING,
                title=f'Alarm {i}',
                source_details_list=[],
                security_level=SecurityLevel.LOW,
                alarm_lifetime_secs=300,
                timestamp=datetimeproxy.now(),
            )
            alert.add_alarm(new_alarm)
        
        # Should not exceed max size
        self.assertEqual(alert.alarm_count, Alert.MAX_ALARM_LIST_SIZE)
        self.assertEqual(len(alert.alarm_list), Alert.MAX_ALARM_LIST_SIZE)
        return

    def test_alert_priority_calculation(self):
        """Test alert priority calculation - critical for alert ordering."""
        # Test with different alarm levels
        critical_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='critical_test',
            alarm_level=AlarmLevel.CRITICAL,
            title='Critical Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        info_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='info_test',
            alarm_level=AlarmLevel.INFO,
            title='Info Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        critical_alert = Alert(critical_alarm)
        info_alert = Alert(info_alarm)
        
        # Critical should have higher priority than info
        self.assertGreater(critical_alert.alert_priority, info_alert.alert_priority)
        self.assertEqual(critical_alert.alert_priority, AlarmLevel.CRITICAL.priority)
        self.assertEqual(info_alert.alert_priority, AlarmLevel.INFO.priority)
        return

    def test_alert_acknowledgment_state_management(self):
        """Test alert acknowledgment state - critical for user interaction."""
        alert = Alert(self.test_alarm)
        
        # Should start unacknowledged
        self.assertFalse(alert.is_acknowledged)
        
        # Should be able to acknowledge
        alert.is_acknowledged = True
        self.assertTrue(alert.is_acknowledged)
        
        # Should be able to unacknowledge
        alert.is_acknowledged = False
        self.assertFalse(alert.is_acknowledged)
        return

    def test_alert_has_single_alarm_logic(self):
        """Test has_single_alarm property - business logic for UI display."""
        alert = Alert(self.test_alarm)
        
        # Should be true for single alarm
        self.assertTrue(alert.has_single_alarm)
        
        # Add second alarm, should be false
        second_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
            title='Second Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        alert.add_alarm(second_alarm)
        self.assertFalse(alert.has_single_alarm)
        return
