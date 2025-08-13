import logging
from datetime import datetime
import threading
import time

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alert_queue import AlertQueue
from hi.apps.alert.alert import Alert
from hi.apps.alert.alarm import Alarm
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlertQueue(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.queue = AlertQueue()
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

    def test_alert_queue_initialization(self):
        """Test AlertQueue initialization - critical state setup."""
        self.assertEqual(len(self.queue), 0)
        self.assertFalse(bool(self.queue))
        self.assertEqual(len(self.queue.unacknowledged_alert_list), 0)
        self.assertIsInstance(self.queue._active_alerts_lock, type(threading.Lock()))
        return

    def test_alert_queue_get_alert_by_id(self):
        """Test get_alert method - critical for alert lookup."""
        alert = Alert(self.test_alarm)
        self.queue._alert_list.append(alert)
        
        # Should find alert by ID
        found_alert = self.queue.get_alert(alert.id)
        self.assertEqual(found_alert, alert)
        
        # Should raise KeyError for non-existent ID
        with self.assertRaises(KeyError):
            self.queue.get_alert('non_existent_id')
        return

    def test_alert_queue_unacknowledged_filtering(self):
        """Test unacknowledged_alert_list filtering - critical for UI display."""
        # Create multiple alerts with different acknowledgment states
        alert1 = Alert(self.test_alarm)
        alert2 = Alert(Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm_2',
            alarm_level=AlarmLevel.INFO,
            title='Test Alarm 2',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        ))
        alert3 = Alert(Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm_3',
            alarm_level=AlarmLevel.CRITICAL,
            title='Test Alarm 3',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        ))
        
        # Add alerts to queue
        self.queue._alert_list = [alert1, alert2, alert3]
        
        # All should be unacknowledged initially
        unack_alerts = self.queue.unacknowledged_alert_list
        self.assertEqual(len(unack_alerts), 3)
        self.assertIn(alert1, unack_alerts)
        self.assertIn(alert2, unack_alerts)
        self.assertIn(alert3, unack_alerts)
        
        # Acknowledge one alert
        alert2.is_acknowledged = True
        
        # Should filter out acknowledged alert
        unack_alerts = self.queue.unacknowledged_alert_list
        self.assertEqual(len(unack_alerts), 2)
        self.assertIn(alert1, unack_alerts)
        self.assertNotIn(alert2, unack_alerts)
        self.assertIn(alert3, unack_alerts)
        
        # Acknowledge all alerts
        alert1.is_acknowledged = True
        alert3.is_acknowledged = True
        
        # Should have no unacknowledged alerts
        unack_alerts = self.queue.unacknowledged_alert_list
        self.assertEqual(len(unack_alerts), 0)
        return

    def test_alert_queue_len_and_bool(self):
        """Test AlertQueue __len__ and __bool__ methods - basic functionality."""
        # Empty queue
        self.assertEqual(len(self.queue), 0)
        self.assertFalse(bool(self.queue))
        
        # Add alert
        alert = Alert(self.test_alarm)
        self.queue._alert_list.append(alert)
        
        # Should reflect new length and boolean state
        self.assertEqual(len(self.queue), 1)
        self.assertTrue(bool(self.queue))
        
        # Add more alerts
        alert2 = Alert(Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm_2',
            alarm_level=AlarmLevel.INFO,
            title='Test Alarm 2',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        ))
        self.queue._alert_list.append(alert2)
        
        self.assertEqual(len(self.queue), 2)
        self.assertTrue(bool(self.queue))
        return

    def test_alert_queue_max_size_constraint(self):
        """Test MAX_ALERT_LIST_SIZE constraint - critical for memory management."""
        # The AlertQueue doesn't appear to enforce the MAX_ALERT_LIST_SIZE in the current code,
        # but we should test that the constant exists and can be used for future enforcement
        self.assertEqual(AlertQueue.MAX_ALERT_LIST_SIZE, 50)
        
        # If size enforcement were implemented, it would be critical business logic
        # For now, just verify the constant exists as part of the class design
        return

    def test_alert_queue_last_changed_datetime_tracking(self):
        """Test last_changed_datetime tracking - important for change detection."""
        # Should have initial timestamp
        initial_time = self.queue._last_changed_datetime
        self.assertIsInstance(initial_time, datetime)
        
        # Time should be recent (within last few seconds)
        time_diff = abs((datetimeproxy.now() - initial_time).total_seconds())
        self.assertLess(time_diff, 5.0)
        return

    def test_alert_queue_thread_safety_lock(self):
        """Test thread safety lock existence - critical for concurrent access."""
        # Should have proper threading lock
        self.assertIsInstance(self.queue._active_alerts_lock, type(threading.Lock()))
        
        # Lock should be usable
        with self.queue._active_alerts_lock:
            # Should be able to acquire and release
            pass
        return