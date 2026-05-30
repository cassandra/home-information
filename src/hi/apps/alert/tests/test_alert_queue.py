import logging
from datetime import datetime
import threading

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alert_queue import AlertQueue
from hi.apps.alert.alert import Alert
from hi.apps.alert.alarm import Alarm, AlarmSignature
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlertQueue(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.queue = AlertQueue()
        self.test_alarm = self._make_alarm('test_alarm')
        return

    def _make_alarm(self, alarm_type: str, level=AlarmLevel.WARNING,
                    source_alarm_id=None) -> Alarm:
        return Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type=alarm_type,
            alarm_level=level,
            title=f'Alarm {alarm_type}',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
            source_alarm_id=source_alarm_id,
        )

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
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        alarm3 = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm_3',
            alarm_level=AlarmLevel.CRITICAL,
            title='Test Alarm 3',
            sensor_response_list=[],
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
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        self.queue.add_alarm(alarm2)
        
        self.assertEqual(len(self.queue), 2)
        self.assertTrue(bool(self.queue))
        return

    def test_alert_queue_max_size_evicts_oldest_acknowledged(self):
        """At capacity, a new alert evicts the oldest acknowledged alert.
        Unacknowledged alerts are never evicted."""
        # Override the cap to a small number for test speed.
        original_cap = AlertQueue.MAX_ALERT_LIST_SIZE
        AlertQueue.MAX_ALERT_LIST_SIZE = 3
        try:
            queue = AlertQueue()
            # Fill: two acked (old, newer) and one unacked, in that order.
            acked_old = queue.add_alarm(self._make_alarm('acked_old'))
            queue.acknowledge_alert(acked_old.id)
            acked_newer = queue.add_alarm(self._make_alarm('acked_newer'))
            queue.acknowledge_alert(acked_newer.id)
            unacked = queue.add_alarm(self._make_alarm('unacked'))

            self.assertEqual(len(queue), 3)

            # Adding a fourth distinct alert should evict the OLDEST acked
            # (acked_old) and keep the unacked alert untouched.
            queue.add_alarm(self._make_alarm('new'))

            self.assertEqual(len(queue), 3)
            with self.assertRaises(KeyError):
                queue.get_alert(acked_old.id)
            # Other two survive.
            queue.get_alert(acked_newer.id)
            queue.get_alert(unacked.id)
        finally:
            AlertQueue.MAX_ALERT_LIST_SIZE = original_cap
        return

    def test_alert_queue_max_size_unacknowledged_not_evicted(self):
        """When the queue is full of only unacknowledged alerts, growth
        is allowed -- an active alert must never be silently lost."""
        original_cap = AlertQueue.MAX_ALERT_LIST_SIZE
        AlertQueue.MAX_ALERT_LIST_SIZE = 2
        try:
            queue = AlertQueue()
            queue.add_alarm(self._make_alarm('a'))
            queue.add_alarm(self._make_alarm('b'))
            self.assertEqual(len(queue), 2)
            # No acked alerts to evict; queue should grow past the cap.
            queue.add_alarm(self._make_alarm('c'))
            self.assertEqual(len(queue), 3)
        finally:
            AlertQueue.MAX_ALERT_LIST_SIZE = original_cap
        return

    def test_alert_queue_at_cap_with_no_acked_invokes_noop_eviction(self):
        """At the cap with zero acked alerts, ``_evict_oldest_acknowledged_alert``
        is still invoked (it's a no-op in this case) and the new alert
        is appended despite the cap. Pins the no-op eviction call path
        explicitly, separate from the queue-growth assertion."""
        from unittest.mock import patch
        original_cap = AlertQueue.MAX_ALERT_LIST_SIZE
        AlertQueue.MAX_ALERT_LIST_SIZE = 2
        try:
            queue = AlertQueue()
            queue.add_alarm(self._make_alarm('a'))
            queue.add_alarm(self._make_alarm('b'))
            with patch.object(
                queue, '_evict_oldest_acknowledged_alert',
                wraps=queue._evict_oldest_acknowledged_alert,
            ) as evict_spy:
                queue.add_alarm(self._make_alarm('c'))
                evict_spy.assert_called_once()
            # Eviction was a no-op; new alert appended.
            self.assertEqual(len(queue), 3)
        finally:
            AlertQueue.MAX_ALERT_LIST_SIZE = original_cap
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
            sensor_response_list=[],
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
            sensor_response_list=[],
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
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        critical_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='critical_test',
            alarm_level=AlarmLevel.CRITICAL,
            title='Critical Alarm',
            sensor_response_list=[],
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
            sensor_response_list=[],
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
            sensor_response_list=[],
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
        """Expired alerts are removed; not-yet-expired alerts survive."""
        from datetime import timedelta
        baseline = datetimeproxy.now()
        expired_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='expired_test',
            alarm_level=AlarmLevel.WARNING,
            title='Expired Alarm',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=1,
            timestamp=baseline,
        )

        # Add expired and active alarms
        expired_alert = self.queue.add_alarm(expired_alarm)
        active_alert = self.queue.add_alarm(self.test_alarm)

        initial_count = len(self.queue)
        self.assertEqual(initial_count, 2)

        # Advance the simulated clock past the expired alarm's end
        # but still before the active alarm's.
        datetimeproxy.set(baseline + timedelta(seconds=10))
        try:
            self.queue.remove_expired_alerts()

            self.assertEqual(len(self.queue), 1)
            with self.assertRaises(KeyError):
                self.queue.get_alert(expired_alert.id)
            found_alert = self.queue.get_alert(active_alert.id)
            self.assertEqual(found_alert, active_alert)
        finally:
            datetimeproxy.reset()
        return

    def test_alert_queue_acknowledged_alert_kept_as_dedup_anchor(self):
        """Acknowledged alerts stay in the queue until their natural
        ``end_datetime`` so they continue to suppress duplicate alarms
        with the same signature. This is the regression-prevention for
        the dismissed-alert-immediately-reappears bug."""
        alert = self.queue.add_alarm(self.test_alarm)
        self.queue.acknowledge_alert(alert.id)

        # Cleanup does not remove acked-but-not-expired alerts.
        self.queue.remove_expired_alerts()
        self.assertEqual(len(self.queue), 1)
        self.queue.get_alert(alert.id)

        # A second matching alarm is silently absorbed by the
        # acknowledged anchor -- not surfaced as a fresh alert.
        before_count = len(self.queue)
        duplicate_alarm = self._make_alarm('test_alarm')
        returned_alert = self.queue.add_alarm(duplicate_alarm)
        self.assertEqual(returned_alert.id, alert.id)
        self.assertEqual(len(self.queue), before_count)
        self.assertEqual(len(self.queue.unacknowledged_alert_list), 0)
        return

    def test_alert_queue_acknowledged_alert_distinct_incident_appends(self):
        """A new incident with the same signature but a distinct
        ``source_alarm_id`` should still append to the acked alert's
        occurrence deque, even though it doesn't re-surface. Captures
        the "new tornado warning during an acked one" path that the
        ``source_alarm_id=None`` dedup-anchor test doesn't exercise."""
        first_alarm = self._make_alarm('test_alarm', source_alarm_id='incident-1')
        alert = self.queue.add_alarm(first_alarm)
        self.queue.acknowledge_alert(alert.id)
        self.assertEqual(alert.alarm_count, 1)

        # Same signature, distinct upstream incident id.
        second_alarm = self._make_alarm('test_alarm', source_alarm_id='incident-2')
        returned_alert = self.queue.add_alarm(second_alarm)

        self.assertEqual(returned_alert.id, alert.id)
        self.assertEqual(alert.alarm_count, 2)
        # Alert stays hidden from the operator.
        self.assertEqual(len(self.queue.unacknowledged_alert_list), 0)
        return

    def test_alert_queue_acknowledged_alert_end_datetime_not_extended(self):
        """``upsert_alarm`` must not refresh ``end_datetime`` on an
        acknowledged alert; otherwise a chronic upstream condition
        could keep the suppression alive indefinitely."""
        from datetime import timedelta
        baseline = datetimeproxy.now()
        datetimeproxy.set(baseline)
        try:
            alert = self.queue.add_alarm(self.test_alarm)
            self.queue.acknowledge_alert(alert.id)
            ack_end_datetime = alert.end_datetime

            # Time passes and the same upstream condition is re-emitted.
            datetimeproxy.set(baseline + timedelta(seconds=120))
            self.queue.add_alarm(self._make_alarm('test_alarm'))

            # end_datetime unchanged: suppression still rides the
            # original window, not the latest poll.
            self.assertEqual(alert.end_datetime, ack_end_datetime)
        finally:
            datetimeproxy.reset()
        return

    def test_clear_signature_removes_unacked_matching_alert(self):
        """``clear_signature`` drops an unacknowledged alert with the
        matching signature -- this is the path producers will use
        when an external condition resolves before the operator has
        seen the alert."""
        alert = self.queue.add_alarm(self.test_alarm)
        signature = alert.signature
        self.assertEqual(len(self.queue), 1)

        removed = self.queue.clear_signature(signature)

        self.assertEqual(removed, 1)
        self.assertEqual(len(self.queue), 0)
        with self.assertRaises(KeyError):
            self.queue.get_alert(alert.id)
        return

    def test_clear_signature_removes_acked_dedup_anchor(self):
        """The primary use case: an acknowledged alert that was
        retained as a dedup anchor must be removable by
        ``clear_signature`` when the producer detects state
        recovery."""
        alert = self.queue.add_alarm(self.test_alarm)
        self.queue.acknowledge_alert(alert.id)
        signature = alert.signature
        self.assertEqual(len(self.queue), 1)

        removed = self.queue.clear_signature(signature)

        self.assertEqual(removed, 1)
        self.assertEqual(len(self.queue), 0)
        return

    def test_clear_signature_no_op_when_no_match(self):
        """No matching alert -> returns 0, queue unchanged. Callers
        must not treat zero as an error."""
        alert = self.queue.add_alarm(self.test_alarm)
        before_changed = self.queue._last_changed_datetime

        non_matching = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='not_in_queue',
            alarm_level=AlarmLevel.INFO,
        )
        removed = self.queue.clear_signature(non_matching)

        self.assertEqual(removed, 0)
        self.assertEqual(len(self.queue), 1)
        self.assertEqual(self.queue.get_alert(alert.id), alert)
        # ``_last_changed_datetime`` must NOT advance when nothing
        # was removed -- consumers polling on that timestamp would
        # otherwise see spurious "queue changed" signals.
        self.assertEqual(self.queue._last_changed_datetime, before_changed)
        return

    def test_clear_signature_no_op_on_empty_queue(self):
        """Empty queue: returns 0 without touching state."""
        self.assertEqual(len(self.queue), 0)
        before_changed = self.queue._last_changed_datetime

        removed = self.queue.clear_signature(
            AlarmSignature(
                alarm_source=AlarmSource.EVENT,
                alarm_type='anything',
                alarm_level=AlarmLevel.INFO,
            )
        )

        self.assertEqual(removed, 0)
        self.assertEqual(self.queue._last_changed_datetime, before_changed)
        return

    def test_clear_signature_leaves_non_matching_alerts_intact(self):
        """Only the targeted signature is removed; other alerts
        survive."""
        target = self.queue.add_alarm(self.test_alarm)
        other = self.queue.add_alarm(
            self._make_alarm('other_type', level=AlarmLevel.CRITICAL),
        )
        self.assertEqual(len(self.queue), 2)

        removed = self.queue.clear_signature(target.signature)

        self.assertEqual(removed, 1)
        self.assertEqual(len(self.queue), 1)
        self.assertEqual(self.queue.get_alert(other.id), other)
        return

    def test_clear_signature_updates_last_changed_only_on_removal(self):
        """The ``_last_changed_datetime`` advances when the call
        removes alerts but not when it's a no-op. Polling consumers
        rely on the timestamp to detect state changes."""
        from datetime import timedelta
        baseline = datetimeproxy.now()
        datetimeproxy.set(baseline)
        try:
            alert = self.queue.add_alarm(self.test_alarm)
            insertion_changed = self.queue._last_changed_datetime
            # Advance the clock and call clear_signature on a
            # non-matching signature: timestamp must not move.
            datetimeproxy.set(baseline + timedelta(seconds=10))
            self.queue.clear_signature(
                AlarmSignature(
                    alarm_source=AlarmSource.EVENT,
                    alarm_type='not_matching',
                    alarm_level=AlarmLevel.INFO,
                )
            )
            self.assertEqual(self.queue._last_changed_datetime, insertion_changed)
            # Advance further and clear the actual signature: timestamp
            # must now advance to reflect the change.
            datetimeproxy.set(baseline + timedelta(seconds=20))
            self.queue.clear_signature(alert.signature)
            self.assertGreater(
                self.queue._last_changed_datetime, insertion_changed
            )
        finally:
            datetimeproxy.reset()
        return

    def test_clear_signature_removes_all_matching_alerts(self):
        """``clear_signature`` walks the whole list and removes every
        match. The normal ``add_alarm`` path aggregates same-signature
        alarms into a single alert, so two distinct alerts with the
        same signature don't arise from typical use -- but the method
        contract is N-matches-N-removed, pinned here by seeding
        ``_alert_list`` directly."""
        a1 = self._make_alarm('multi_match')
        a2 = self._make_alarm('multi_match')
        alert1 = Alert(first_alarm=a1)
        alert2 = Alert(first_alarm=a2)
        with self.queue._active_alerts_lock:
            self.queue._alert_list = [alert1, alert2]
        self.assertEqual(alert1.signature, alert2.signature)

        removed = self.queue.clear_signature(alert1.signature)

        self.assertEqual(removed, 2)
        self.assertEqual(len(self.queue), 0)
        return

    def test_clear_signature_then_matching_alarm_creates_fresh_alert(self):
        """Regression check on the design goal: after ``clear_signature``,
        a subsequent matching alarm produces a NEW alert (not absorbed
        into a stale anchor), so notification re-fires."""
        first_alert = self.queue.add_alarm(self.test_alarm)
        self.queue.acknowledge_alert(first_alert.id)
        signature = first_alert.signature

        self.queue.clear_signature(signature)
        # Same signature alarm arrives after recovery -- must NOT
        # absorb (queue is empty); must create a new alert with a
        # distinct id.
        re_alarm = self._make_alarm('test_alarm')
        re_alert = self.queue.add_alarm(re_alarm)

        self.assertEqual(re_alert.signature, signature)
        self.assertNotEqual(re_alert.id, first_alert.id)
        self.assertEqual(len(self.queue.unacknowledged_alert_list), 1)
        return

    def test_alert_queue_remove_expired_counts_acknowledged_among_removed(self):
        """``acknowledged_removed`` reports the subset of expired alerts
        that had been acknowledged. No longer a removal trigger; just
        a stat."""
        from datetime import timedelta
        baseline = datetimeproxy.now()
        short_lived_acked = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='short_acked',
            alarm_level=AlarmLevel.WARNING,
            title='Short-lived acked',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=1,
            timestamp=baseline,
        )
        short_lived_unacked = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='short_unacked',
            alarm_level=AlarmLevel.WARNING,
            title='Short-lived unacked',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=1,
            timestamp=baseline,
        )
        a1 = self.queue.add_alarm(short_lived_acked)
        self.queue.add_alarm(short_lived_unacked)
        self.queue.acknowledge_alert(a1.id)

        datetimeproxy.set(baseline + timedelta(seconds=10))
        try:
            result = self.queue.remove_expired_alerts()
            self.assertEqual(result.expired_removed, 2)
            self.assertEqual(result.acknowledged_removed, 1)
            self.assertEqual(result.total_removed, 2)
        finally:
            datetimeproxy.reset()
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
                        sensor_response_list=[],
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
