import logging
from datetime import timedelta
from unittest.mock import Mock, patch

from django.utils import timezone

from hi.apps.alert.alert_manager import AlertManager
from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.console.transient_view_manager import TransientViewManager
from hi.apps.security.enums import SecurityLevel
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlertManagerDelegation(BaseTestCase):
    """Test AlertManager delegation to TransientViewManager for auto-view switching."""

    def setUp(self):
        super().setUp()
        # Reset singletons for test isolation
        AlertManager._instances = {}
        TransientViewManager._instances = {}
        
        self.alert_manager = AlertManager()
        self.transient_manager = TransientViewManager()

    def test_alert_manager_delegates_new_alerts_to_transient_view_manager(self):
        """Test AlertManager delegates new alerts to TransientViewManager - core integration."""
        # Create realistic motion detection alarm with sensor details
        source_details = AlarmSourceDetails(
            detail_attrs={'sensor_id': '123', 'location': 'Front Door'},
            image_url=None
        )
        
        motion_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Motion detected at Front Door',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()
        )
        
        # Mock TransientViewManager to track delegation calls
        with patch.object(self.transient_manager, 'consider_alert_for_auto_view') as mock_consider:
            # Add alarm to create an alert
            self.run_async_test(self.alert_manager.add_alarm(motion_alarm))
            
            # Get alert status data (this triggers delegation to TransientViewManager)
            alert_status_data = self.alert_manager.get_alert_status_data(
                last_alert_status_datetime=timezone.now() - timedelta(seconds=5)
            )
            
            # Verify delegation occurred
            mock_consider.assert_called_once()
            
            # Verify the correct alert was passed to TransientViewManager
            call_args = mock_consider.call_args[0]
            alert_passed = call_args[0]
            
            self.assertEqual(alert_passed.first_alarm.alarm_type, 'motion_detection')
            self.assertEqual(
                alert_passed.first_alarm.source_details_list[0].detail_attrs['sensor_id'], 
                '123'
            )

    def test_alert_manager_no_delegation_when_no_new_alert(self):
        """Test AlertManager doesn't delegate when no new alerts - conditional delegation."""
        # Mock TransientViewManager to track calls
        with patch.object(self.transient_manager, 'consider_alert_for_auto_view') as mock_consider:
            # Get alert status without any alarms being added
            alert_status_data = self.alert_manager.get_alert_status_data(
                last_alert_status_datetime=timezone.now() - timedelta(seconds=5)
            )
            
            # Should not have called TransientViewManager
            mock_consider.assert_not_called()

    def test_alert_manager_focuses_on_new_alerts_not_queue_state(self):
        """Test AlertManager delegates only new alerts, not existing queue state - precise delegation."""
        # Create two different alarms
        source_details_1 = AlarmSourceDetails(
            detail_attrs={'sensor_id': '123'},
            image_url=None
        )
        
        source_details_2 = AlarmSourceDetails(
            detail_attrs={'sensor_id': '456'},
            image_url=None
        )
        
        old_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.INFO,
            title='Old Motion',
            source_details_list=[source_details_1],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now() - timedelta(seconds=30)  # Older timestamp
        )
        
        new_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='New Motion',
            source_details_list=[source_details_2],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()  # Recent timestamp
        )
        
        # Add old alarm first
        self.run_async_test(self.alert_manager.add_alarm(old_alarm))
        
        # Clear any existing delegations
        with patch.object(self.transient_manager, 'consider_alert_for_auto_view') as mock_consider:
            # Add new alarm
            self.run_async_test(self.alert_manager.add_alarm(new_alarm))
            
            # Get alert status - should delegate only the new alert
            alert_status_data = self.alert_manager.get_alert_status_data(
                last_alert_status_datetime=timezone.now() - timedelta(seconds=5)
            )
            
            # Should have been called once for the new alert
            mock_consider.assert_called_once()
            
            # Verify it was called with the new alert (sensor_id '456')
            call_args = mock_consider.call_args[0]
            alert_passed = call_args[0]
            
            self.assertEqual(
                alert_passed.first_alarm.source_details_list[0].detail_attrs['sensor_id'],
                '456'
            )

    def run_async_test(self, coro):
        """Helper to run async methods in tests."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()