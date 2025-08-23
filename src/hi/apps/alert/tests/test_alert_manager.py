import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.alert.alert_manager import AlertManager
from hi.apps.alert.alarm import Alarm
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.security.enums import SecurityLevel
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
