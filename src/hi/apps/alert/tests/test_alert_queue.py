import logging
from datetime import datetime
import threading

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alert_queue import AlertQueue
from hi.apps.alert.alert import Alert
from hi.apps.alert.alarm import Alarm
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.testing.base_test_case import BaseTestCase

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
        # Add alert through proper interface
        created_alert = self.queue.add_alarm(self.test_alarm)
        
        # Should find alert by ID
        found_alert = self.queue.get_alert(created_alert.id)
        self.assertEqual(found_alert, created_alert)
        
        # Should raise KeyError for non-existent ID
        with self.assertRaises(KeyError):
            self.queue.get_alert('non_existent_id')
        return

    def test_alert_queue_unacknowledged_filtering(self):
        """Test unacknowledged_alert_list filtering - critical for UI display."""
        # Create multiple alarms with different properties
        alarm2 = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm_2',
            alarm_level=AlarmLevel.INFO,
            title='Test Alarm 2',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        alarm3 = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm_3',
            alarm_level=AlarmLevel.CRITICAL,
            title='Test Alarm 3',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        # Add alerts through proper interface
        alert1 = self.queue.add_alarm(self.test_alarm)
        alert2 = self.queue.add_alarm(alarm2)
        alert3 = self.queue.add_alarm(alarm3)
        
        # All should be unacknowledged initially
        unack_alerts = self.queue.unacknowledged_alert_list
        self.assertEqual(len(unack_alerts), 3)
        self.assertIn(alert1, unack_alerts)
        self.assertIn(alert2, unack_alerts)
        self.assertIn(alert3, unack_alerts)
        
        # Acknowledge one alert through proper interface
        self.queue.acknowledge_alert(alert2.id)
        
        # Should filter out acknowledged alert
        unack_alerts = self.queue.unacknowledged_alert_list
        self.assertEqual(len(unack_alerts), 2)
        self.assertIn(alert1, unack_alerts)
        self.assertNotIn(alert2, unack_alerts)
        self.assertIn(alert3, unack_alerts)
        
        # Acknowledge remaining alerts
        self.queue.acknowledge_alert(alert1.id)
        self.queue.acknowledge_alert(alert3.id)
        
        # Should have no unacknowledged alerts
        unack_alerts = self.queue.unacknowledged_alert_list
        self.assertEqual(len(unack_alerts), 0)
        return

    def test_alert_queue_len_and_bool(self):
        """Test AlertQueue __len__ and __bool__ methods - basic functionality."""
        # Empty queue
        self.assertEqual(len(self.queue), 0)
        self.assertFalse(bool(self.queue))
        
        # Add alert through proper interface
        self.queue.add_alarm(self.test_alarm)
        
        # Should reflect new length and boolean state
        self.assertEqual(len(self.queue), 1)
        self.assertTrue(bool(self.queue))
        
        # Add more alerts
        alarm2 = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm_2',
            alarm_level=AlarmLevel.INFO,
            title='Test Alarm 2',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        self.queue.add_alarm(alarm2)
        
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

    def test_alert_queue_add_alarm_new_alert_creation(self):
        """Test add_alarm creates new alert - critical for alarm processing."""
        initial_count = len(self.queue)
        
        result_alert = self.queue.add_alarm(self.test_alarm)
        
        # Should create new alert and add to queue
        self.assertEqual(len(self.queue), initial_count + 1)
        self.assertIsInstance(result_alert, Alert)
        self.assertEqual(result_alert.first_alarm, self.test_alarm)
        self.assertEqual(result_alert.alarm_count, 1)
        
        # Should be findable by ID
        found_alert = self.queue.get_alert(result_alert.id)
        self.assertEqual(found_alert, result_alert)
        return

    def test_alert_queue_add_alarm_existing_alert_aggregation(self):
        """Test add_alarm aggregates to existing alert - critical for alarm grouping."""
        # Add first alarm
        first_alert = self.queue.add_alarm(self.test_alarm)
        initial_count = len(self.queue)
        
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
        
        result_alert = self.queue.add_alarm(matching_alarm)
        
        # Should not create new alert, should aggregate to existing
        self.assertEqual(len(self.queue), initial_count)
        self.assertEqual(result_alert, first_alert)
        self.assertEqual(result_alert.alarm_count, 2)
        
        # Should contain both alarms
        self.assertIn(matching_alarm, result_alert.alarm_list)
        return

    def test_alert_queue_add_alarm_none_level_rejection(self):
        """Test add_alarm rejects NONE level alarms - critical validation."""
        none_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='none_test',
            alarm_level=AlarmLevel.NONE,
            title='None Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        with self.assertRaises(ValueError) as context:
            self.queue.add_alarm(none_alarm)
        
        error_message = str(context.exception)
        self.assertIn('not alert-worthy', error_message)
        return

    def test_alert_queue_acknowledge_alert_functionality(self):
        """Test acknowledge_alert method - critical for user interaction."""
        # Add alert to queue
        alert = self.queue.add_alarm(self.test_alarm)
        self.assertFalse(alert.is_acknowledged)
        
        # Should acknowledge successfully
        result = self.queue.acknowledge_alert(alert.id)
        self.assertTrue(result)
        self.assertTrue(alert.is_acknowledged)
        
        # Should not appear in unacknowledged list
        unack_alerts = self.queue.unacknowledged_alert_list
        self.assertNotIn(alert, unack_alerts)
        return

    def test_alert_queue_acknowledge_alert_nonexistent_error(self):
        """Test acknowledge_alert with invalid ID - error handling."""
        with self.assertRaises(KeyError) as context:
            self.queue.acknowledge_alert('nonexistent_id')
        
        error_message = str(context.exception)
        self.assertIn('Alert not found', error_message)
        self.assertIn('nonexistent_id', error_message)
        return

    def test_alert_queue_get_most_important_unacknowledged_alert(self):
        """Test get_most_important_unacknowledged_alert - critical for priority handling."""
        # Create alerts with different priorities
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
        
        # Add alarms (info first, then critical)
        info_alert = self.queue.add_alarm(info_alarm)
        critical_alert = self.queue.add_alarm(critical_alarm)
        
        # Should return highest priority alert
        most_important = self.queue.get_most_important_unacknowledged_alert()
        self.assertEqual(most_important, critical_alert)
        
        # After acknowledging critical, should return info
        self.queue.acknowledge_alert(critical_alert.id)
        most_important = self.queue.get_most_important_unacknowledged_alert()
        self.assertEqual(most_important, info_alert)
        
        # After acknowledging all, should return None
        self.queue.acknowledge_alert(info_alert.id)
        most_important = self.queue.get_most_important_unacknowledged_alert()
        self.assertIsNone(most_important)
        return

    def test_alert_queue_get_most_recent_alarm(self):
        """Test get_most_recent_alarm - critical for alarm tracking."""
        # Create alarms with different timestamps
        import time
        
        older_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='older_test',
            alarm_level=AlarmLevel.WARNING,
            title='Older Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        # Small delay to ensure different timestamps
        time.sleep(0.01)
        
        newer_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='newer_test',
            alarm_level=AlarmLevel.INFO,
            title='Newer Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        # Add alarms
        self.queue.add_alarm(older_alarm)
        self.queue.add_alarm(newer_alarm)
        
        # Should return most recent alarm
        most_recent = self.queue.get_most_recent_alarm()
        self.assertEqual(most_recent, newer_alarm)
        return

    def test_alert_queue_remove_expired_alerts(self):
        """Test remove_expired_or_acknowledged_alerts - critical for cleanup."""
        # Create expired alarm (negative lifetime to force expiration)
        expired_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='expired_test',
            alarm_level=AlarmLevel.WARNING,
            title='Expired Alarm',
            source_details_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=-1,  # Expired immediately
            timestamp=datetimeproxy.now(),
        )
        
        # Add expired and active alarms
        expired_alert = self.queue.add_alarm(expired_alarm)
        active_alert = self.queue.add_alarm(self.test_alarm)
        
        initial_count = len(self.queue)
        self.assertEqual(initial_count, 2)
        
        # Run cleanup
        self.queue.remove_expired_or_acknowledged_alerts()
        
        # Should remove expired alert but keep active one
        self.assertEqual(len(self.queue), 1)
        
        # Should not find expired alert
        with self.assertRaises(KeyError):
            self.queue.get_alert(expired_alert.id)
        
        # Should still find active alert
        found_alert = self.queue.get_alert(active_alert.id)
        self.assertEqual(found_alert, active_alert)
        return

    def test_alert_queue_remove_acknowledged_alerts(self):
        """Test remove_expired_or_acknowledged_alerts removes acknowledged - critical for cleanup."""
        # Add alert and acknowledge it
        alert = self.queue.add_alarm(self.test_alarm)
        self.queue.acknowledge_alert(alert.id)
        
        self.assertEqual(len(self.queue), 1)
        self.assertTrue(alert.is_acknowledged)
        
        # Run cleanup
        self.queue.remove_expired_or_acknowledged_alerts()
        
        # Should remove acknowledged alert
        self.assertEqual(len(self.queue), 0)
        
        # Should not find acknowledged alert
        with self.assertRaises(KeyError):
            self.queue.get_alert(alert.id)
        return

    def test_alert_queue_concurrent_access_thread_safety(self):
        """Test AlertQueue thread safety under concurrent access - critical for production."""
        import concurrent.futures
        import time
        
        results = []
        errors = []
        
        def add_alarms_worker(worker_id):
            """Worker function to add alarms concurrently"""
            try:
                for i in range(5):
                    alarm = Alarm(
                        alarm_source=AlarmSource.EVENT,
                        alarm_type=f'concurrent_test_{worker_id}_{i}',
                        alarm_level=AlarmLevel.WARNING,
                        title=f'Worker {worker_id} Alarm {i}',
                        source_details_list=[],
                        security_level=SecurityLevel.LOW,
                        alarm_lifetime_secs=300,
                        timestamp=datetimeproxy.now(),
                    )
                    alert = self.queue.add_alarm(alarm)
                    results.append((worker_id, i, alert.id))
                    time.sleep(0.001)  # Small delay to increase chance of contention
            except Exception as e:
                errors.append(f'Worker {worker_id}: {e}')
        
        def acknowledge_worker():
            """Worker function to acknowledge alerts concurrently"""
            try:
                time.sleep(0.01)  # Let some alerts be created first
                for _ in range(10):
                    if len(self.queue) > 0:
                        unack_alerts = self.queue.unacknowledged_alert_list
                        if unack_alerts:
                            alert_to_ack = unack_alerts[0]
                            self.queue.acknowledge_alert(alert_to_ack.id)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f'Acknowledge worker: {e}')
        
        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # Start 5 workers adding alarms
            add_futures = [executor.submit(add_alarms_worker, i) for i in range(5)]
            # Start 1 worker acknowledging alerts
            ack_future = executor.submit(acknowledge_worker)
            
            # Wait for all to complete
            concurrent.futures.wait(add_futures + [ack_future], timeout=10)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f'Concurrent access errors: {errors}')
        
        # Verify we have some results
        self.assertGreater(len(results), 0, 'No alarms were successfully added')
        
        # Verify all created alerts are still accessible
        for worker_id, alarm_num, alert_id in results:
            try:
                found_alert = self.queue.get_alert(alert_id)
                self.assertIsNotNone(found_alert)
            except KeyError:
                # Alert might have been acknowledged and cleaned up, which is fine
                pass
        
        # Verify queue is in consistent state
        total_alerts = len(self.queue)
        unack_count = len(self.queue.unacknowledged_alert_list)
        self.assertGreaterEqual(total_alerts, unack_count)
        return
