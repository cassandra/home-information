import logging
from unittest.mock import patch, AsyncMock, MagicMock

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alert_manager import AlertManager, AlertMaintenanceResult
from hi.apps.alert.alarm import Alarm, AlarmSignature
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.alert.tests.synthetic_data import AlertSyntheticData
from hi.apps.security.enums import SecurityLevel
from hi.testing.async_task_utils import AsyncTaskFastTestCase, AsyncTaskTestCase
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlertManager(BaseTestCase):

    def test_alert_manager_singleton_behavior(self):
        """Test AlertManager singleton pattern - critical for system consistency."""
        manager1 = AlertManager()
        manager2 = AlertManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_alert_manager_initialization(self):
        """Test AlertManager initialization and ensure_initialized - critical setup logic."""
        manager = AlertManager()
        
        # Should have alert queue
        self.assertIsNotNone(manager._alert_queue)
        
        # May already be initialized due to singleton pattern
        # Test ensure_initialized works without error
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        
        # Subsequent calls should not change state
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        return

    def test_alert_manager_unacknowledged_alert_list_delegation(self):
        """Test unacknowledged_alert_list property delegation - critical UI integration."""
        manager = AlertManager()
        
        # Should delegate to alert queue
        unack_list = manager.unacknowledged_alert_list
        expected_list = manager._alert_queue.unacknowledged_alert_list
        self.assertEqual(unack_list, expected_list)
        return

    def test_alert_manager_get_alert_integration(self):
        """Test get_alert method through proper interface - critical for alert lookup."""
        manager = AlertManager()
        
        # Create test alarm and add through proper interface
        test_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.WARNING,
            title='Test Alarm',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        
        # Add alarm through AlertQueue's public interface
        created_alert = manager._alert_queue.add_alarm(test_alarm)
        
        # Should be retrievable through manager
        found_alert = manager.get_alert(created_alert.id)
        self.assertEqual(found_alert, created_alert)
        
        # Should raise KeyError for non-existent ID
        with self.assertRaises(KeyError):
            manager.get_alert('non_existent_id')
        return

    def test_alert_manager_get_alert_status_data_structure(self):
        """Test get_alert_status_data method structure - complex business logic integration."""
        manager = AlertManager()
        manager.ensure_initialized()
        
        test_datetime = datetimeproxy.now()
        
        # Method should exist and return AlertStatusData
        status_data = manager.get_alert_status_data(test_datetime)
        
        # Should return some form of status data structure
        self.assertIsNotNone(status_data)
        
        # The exact structure depends on AlertStatusData implementation,
        # but we're testing that the method executes without error
        return

    def test_alert_manager_mixin_inheritance(self):
        """Test AlertManager mixin inheritance - critical for system integration."""
        manager = AlertManager()
        
        # Should inherit from NotificationMixin
        self.assertTrue(hasattr(manager, 'notification_manager'))
        
        # Should inherit from SecurityMixin  
        self.assertTrue(hasattr(manager, 'security_manager'))
        
        # Should be a Singleton
        from hi.apps.common.singleton import Singleton
        self.assertIsInstance(manager, Singleton)
        return

    def test_notification_suppressed_for_absorbed_alarm_into_acked_alert(self):
        """When an alarm is absorbed into an already-acknowledged alert
        with a distinct ``source_alarm_id``, the alert's occurrence
        deque grows -- ``has_single_alarm`` becomes False -- and
        ``add_notification_item`` is NOT invoked. Pins the
        AlertManager-level suppression of re-notification on absorb
        for the new dedup-anchor semantics."""
        manager = AlertManager()
        # Fresh queue per test so prior tests don't bleed in.
        manager._alert_queue._alert_list.clear()

        mock_notification_manager = patch.object(
            manager, 'notification_manager'
        ).start()
        self.addCleanup(patch.stopall)
        mock_security_manager = patch.object(
            manager, 'security_manager'
        ).start()
        mock_security_manager.return_value.security_state.uses_notifications = True

        first_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='absorb_test',
            alarm_level=AlarmLevel.WARNING,
            title='First incident',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
            source_alarm_id='incident-1',
        )
        manager.upsert_alarm(first_alarm)
        first_alert = manager.unacknowledged_alert_list[0]
        # First alarm produces one notification call (single-alarm).
        self.assertEqual(
            mock_notification_manager.return_value.add_notification_item.call_count, 1
        )

        manager.acknowledge_alert(first_alert.id)

        # Distinct new incident, same signature, arrives after ack.
        second_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='absorb_test',
            alarm_level=AlarmLevel.WARNING,
            title='Second incident',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
            source_alarm_id='incident-2',
        )
        manager.upsert_alarm(second_alarm)

        # No new notification: alert now has 2 alarms in its deque.
        self.assertEqual(
            mock_notification_manager.return_value.add_notification_item.call_count, 1
        )
        return

    def test_clear_alarms_removes_matching_alert(self):
        """``AlertManager.clear_alarms`` takes an ``AlarmSignature``
        the producer constructs from the same fields the original
        ``Alarm`` carried. The composition (joined-string form, used
        for diagnostics) stays inside ``AlarmSignature``; the queue
        compares structurally."""
        manager = AlertManager()
        manager._alert_queue._alert_list.clear()

        test_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='clear_alarms_test',
            alarm_level=AlarmLevel.WARNING,
            title='Clear-alarms target',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        manager._alert_queue.add_alarm(test_alarm)

        removed = manager.clear_alarms(
            signature=AlarmSignature(
                alarm_source=AlarmSource.EVENT,
                alarm_type='clear_alarms_test',
                alarm_level=AlarmLevel.WARNING,
            )
        )

        self.assertEqual(removed, 1)
        self.assertEqual(len(manager.unacknowledged_alert_list), 0)
        return

    def test_clear_alarms_returns_zero_when_no_match(self):
        """``clear_alarms`` returns 0 (not None / not error) when
        nothing in the queue matches. Producers may call it
        speculatively on every recovery transition; the no-op outcome
        must be cheap and silent."""
        manager = AlertManager()
        manager._alert_queue._alert_list.clear()

        removed = manager.clear_alarms(
            signature=AlarmSignature(
                alarm_source=AlarmSource.EVENT,
                alarm_type='nothing.like.this.is.queued',
                alarm_level=AlarmLevel.WARNING,
            )
        )

        self.assertEqual(removed, 0)
        return

    def test_clear_alarms_matches_alarm_signature(self):
        """The ``AlarmSignature`` a producer constructs MUST equal the
        ``Alarm.signature`` of an alarm with the same fields. Pins
        the contract that ``AlarmSignature`` is the structural
        identity, not a coincidental string match."""
        manager = AlertManager()
        manager._alert_queue._alert_list.clear()

        test_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='roundtrip_test',
            alarm_level=AlarmLevel.CRITICAL,
            title='Round-trip target',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        alert = manager._alert_queue.add_alarm(test_alarm)

        producer_signature = AlarmSignature(
            alarm_source=AlarmSource.EVENT,
            alarm_type='roundtrip_test',
            alarm_level=AlarmLevel.CRITICAL,
        )
        # Producer's signature equals the alert's signature -- otherwise
        # ``clear_alarms`` would silently miss its target.
        self.assertEqual(producer_signature, alert.signature)

        removed = manager.clear_alarms(signature=producer_signature)
        self.assertEqual(removed, 1)
        return

    def test_alert_manager_alert_queue_integration(self):
        """Test AlertManager integration with AlertQueue - critical system interaction."""
        manager = AlertManager()

        # Should have working alert queue
        self.assertIsNotNone(manager._alert_queue)
        
        # Queue operations should work through manager interface
        initial_count = len(manager.unacknowledged_alert_list)
        
        # Add alarm through queue's public interface
        test_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='test_alarm',
            alarm_level=AlarmLevel.CRITICAL,
            title='Test Alarm',
            sensor_response_list=[],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now(),
        )
        created_alert = manager._alert_queue.add_alarm(test_alarm)
        
        # Should be reflected in manager's unacknowledged list
        self.assertEqual(len(manager.unacknowledged_alert_list), initial_count + 1)
        self.assertIn(created_alert, manager.unacknowledged_alert_list)
        
        # Should be retrievable through manager
        retrieved_alert = manager.get_alert(created_alert.id)
        self.assertEqual(retrieved_alert, created_alert)
        return



class TestAlertMaintenanceResult(BaseTestCase):
    """Test the AlertMaintenanceResult data class and summary message generation."""

    def test_summary_message_no_alerts_in_queue(self):
        """Test summary message when no alerts in queue."""
        result = AlertMaintenanceResult(alerts_before_cleanup=0)
        self.assertEqual(result.get_summary_message(), "No alerts in queue")

    def test_summary_message_no_cleanup_needed(self):
        """Test summary message when no cleanup needed."""
        result = AlertMaintenanceResult(
            alerts_before_cleanup=3,
            alerts_after_cleanup=3,
            expired_alerts_removed=0,
            acknowledged_alerts_removed=0
        )
        self.assertEqual(result.get_summary_message(), "No cleanup needed (3 active alerts)")

    def test_summary_message_no_cleanup_needed_single_alert(self):
        """Test summary message when no cleanup needed with single alert."""
        result = AlertMaintenanceResult(
            alerts_before_cleanup=1,
            alerts_after_cleanup=1,
            expired_alerts_removed=0,
            acknowledged_alerts_removed=0
        )
        self.assertEqual(result.get_summary_message(), "No cleanup needed (1 active alert)")

    def test_summary_message_expired_alerts_removed(self):
        """Test summary message when expired alerts removed."""
        result = AlertMaintenanceResult(
            alerts_before_cleanup=5,
            alerts_after_cleanup=3,
            expired_alerts_removed=2,
            acknowledged_alerts_removed=0
        )
        self.assertEqual(result.get_summary_message(), "Removed 2 expired, 3 active")

    def test_summary_message_acknowledged_alerts_removed(self):
        """Test summary message when acknowledged alerts removed."""
        result = AlertMaintenanceResult(
            alerts_before_cleanup=4,
            alerts_after_cleanup=2,
            expired_alerts_removed=0,
            acknowledged_alerts_removed=2
        )
        self.assertEqual(result.get_summary_message(), "Removed 2 acknowledged, 2 active")

    def test_summary_message_mixed_removal(self):
        """Test summary message when both expired and acknowledged alerts removed."""
        result = AlertMaintenanceResult(
            alerts_before_cleanup=7,
            alerts_after_cleanup=3,
            expired_alerts_removed=2,
            acknowledged_alerts_removed=2
        )
        self.assertEqual(result.get_summary_message(), "Removed 2 expired, 2 acknowledged, 3 active")

    def test_summary_message_all_alerts_removed(self):
        """Test summary message when all alerts removed."""
        result = AlertMaintenanceResult(
            alerts_before_cleanup=3,
            alerts_after_cleanup=0,
            expired_alerts_removed=2,
            acknowledged_alerts_removed=1
        )
        self.assertEqual(result.get_summary_message(), "Removed 2 expired, 1 acknowledged, none active")

    def test_summary_message_with_error(self):
        """Test summary message when error occurred."""
        result = AlertMaintenanceResult(error_message="Database connection failed")
        self.assertEqual(result.get_summary_message(), "Alert maintenance failed: Database connection failed")

    def test_total_alerts_removed_property(self):
        """Test total_alerts_removed property calculation."""
        result = AlertMaintenanceResult(
            expired_alerts_removed=3,
            acknowledged_alerts_removed=2
        )
        self.assertEqual(result.total_alerts_removed, 5)


class TestAlertManagerMaintenance(AsyncTaskFastTestCase):
    """Test AlertManager periodic maintenance with new result tracking."""

    def setUp(self):
        super().setUp()
        # Reset singleton state for each test
        AlertManager._instance = None
        self.manager = AlertManager()

    def test_periodic_maintenance_returns_result(self):
        """Test periodic maintenance returns AlertMaintenanceResult."""
        async def async_test_logic():
            # Use the real AlertQueue - no mocking needed
            result = await self.manager.do_periodic_maintenance()

            # Verify result is correct type
            self.assertIsInstance(result, AlertMaintenanceResult)

            # For an empty queue, should have specific values
            self.assertEqual(result.alerts_before_cleanup, 0)
            self.assertEqual(result.alerts_after_cleanup, 0)
            self.assertEqual(result.expired_alerts_removed, 0)
            self.assertEqual(result.acknowledged_alerts_removed, 0)
            self.assertIsNone(result.error_message)

            # Should report "No alerts in queue"
            self.assertEqual(result.get_summary_message(), "No alerts in queue")

        self.run_async(async_test_logic())

    def test_periodic_maintenance_handles_exceptions(self):
        """Test periodic maintenance handles exceptions gracefully."""
        async def async_test_logic():
            # Mock the alert queue to raise an exception
            with patch.object(self.manager._alert_queue, 'remove_expired_alerts') as mock_cleanup:
                mock_cleanup.side_effect = Exception("Test exception")

                result = await self.manager.do_periodic_maintenance()

                # Verify result contains error information
                self.assertIsInstance(result, AlertMaintenanceResult)
                self.assertEqual(result.alerts_before_cleanup, 0)  # Empty queue before exception
                self.assertIn("Test exception", result.error_message)

        self.run_async(async_test_logic())


class TestAlertManagerAsyncSecurityInit(AsyncTaskTestCase):
    """Regression for issue #404: the async alarm path (reached e.g. from
    WeatherManager) must obtain SecurityManager via the async accessor. The
    synchronous accessor runs a sync ORM query on the loop, which
    SecurityManager.ensure_initialized() swallows while forcing security state
    DISABLED -- a silent fault. We assert the accessor contract directly."""

    def setUp(self):
        super().setUp()
        AlertManager._instance = None
        self.manager = AlertManager()

    def test_upsert_alarm_async_uses_async_security_accessor(self):
        async def async_test_logic():
            alarm = AlertSyntheticData.create_single_alarm_alert().first_alarm

            security_state = MagicMock()
            security_state.uses_notifications = False  # skip the notify branch
            security_manager = MagicMock()
            security_manager.security_state = security_state

            with patch.object( self.manager, 'notification_manager_async',
                               new = AsyncMock( return_value = MagicMock() )), \
                 patch.object( self.manager, 'security_manager_async',
                               new = AsyncMock( return_value = security_manager )) as mock_async, \
                 patch.object( self.manager, 'security_manager' ) as mock_sync:

                await self.manager.upsert_alarm_async( alarm )

            mock_async.assert_awaited_once()
            mock_sync.assert_not_called()

        self.run_async(async_test_logic())

