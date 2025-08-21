import logging
from datetime import timedelta
from unittest.mock import Mock, patch

from django.utils import timezone

from hi.apps.alert.alert_manager import AlertManager
from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.console.transient_view_manager import TransientViewManager
from hi.apps.security.enums import SecurityLevel
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlertManagerDelegation(BaseTestCase):
    """Test AlertManager delegation to TransientViewManager for auto-view switching."""

    def setUp(self):
        super().setUp()
        # Reset singletons for test isolation
        AlertManager._instance = None
        TransientViewManager._instance = None
        
        self.alert_manager = AlertManager()
        self.transient_manager = TransientViewManager()
        
        # Ensure clean state for TransientViewManager
        self.transient_manager.clear_suggestion()
    
    def tearDown(self):
        # Clean up after each test
        if hasattr(self, 'transient_manager'):
            self.transient_manager.clear_suggestion()
        TransientViewManager().clear_suggestion()
        
        # Clear AlertManager state (the AlertQueue)
        if hasattr(self, 'alert_manager'):
            self.alert_manager._alert_queue._alert_list.clear()
        
        super().tearDown()

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
        
        # Verify no suggestion exists initially
        self.assertFalse(self.transient_manager.has_suggestion())
        
        # Mock settings to enable auto-view for this test
        with patch('hi.apps.console.transient_view_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            with patch('django.urls.reverse') as mock_reverse:
                mock_reverse.return_value = '/console/sensor/video_stream/123/'
                
                # Add alarm to create an alert
                self.run_async_test(self.alert_manager.add_alarm(motion_alarm))
                
                # Get alert status data (this should trigger delegation to TransientViewManager)
                self.alert_manager.get_alert_status_data(
                    last_alert_status_datetime=timezone.now() - timedelta(seconds=5)
                )
                
                # Verify delegation created a suggestion (test actual behavior, not mock calls)
                self.assertTrue(self.transient_manager.has_suggestion())

    def test_alert_manager_no_delegation_when_no_new_alert(self):
        """Test AlertManager doesn't delegate when no new alerts - conditional delegation."""
        # Verify no suggestion exists initially
        self.assertFalse(self.transient_manager.has_suggestion())
        
        # Get alert status without any alarms being added
        self.alert_manager.get_alert_status_data(
            last_alert_status_datetime=timezone.now() - timedelta(seconds=5)
        )
        
        # Should still not have any suggestions (no new alerts to delegate)
        self.assertFalse(self.transient_manager.has_suggestion())

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
        
        # Create alarms with different types to ensure separate alerts
        old_time = timezone.now() - timedelta(seconds=30)
        new_time = timezone.now() - timedelta(seconds=2)  # More recent but not now
        
        old_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.INFO,  # Lower priority
            title='Old Motion',
            source_details_list=[source_details_1],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=old_time
        )
        
        new_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,  # Higher priority, different signature
            title='New Motion',
            source_details_list=[source_details_2],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=new_time
        )
        
        # Add old alarm first
        self.run_async_test(self.alert_manager.add_alarm(old_alarm))
        
        # Verify no suggestion exists yet
        self.assertFalse(self.transient_manager.has_suggestion())
        
        # Add new alarm
        self.run_async_test(self.alert_manager.add_alarm(new_alarm))
        
        # Mock settings to enable auto-view for this test
        with patch('hi.apps.console.transient_view_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            with patch('django.urls.reverse') as mock_reverse:
                mock_reverse.return_value = '/console/sensor/video_stream/456/'
                
                # Get alert status - should delegate only the new alert
                # Use timestamp that excludes old alarm but includes new one
                self.alert_manager.get_alert_status_data(
                    last_alert_status_datetime=timezone.now() - timedelta(seconds=5)  # Between old (30s ago) and new (2s ago)
                )
                
                # Should have created a suggestion based on the new alert only
                self.assertTrue(self.transient_manager.has_suggestion())
                
                # The suggestion should be based on the new alert's sensor_id ('456')
                suggestion = self.transient_manager.peek_current_suggestion()
                self.assertIn('456', suggestion.url)

    def run_async_test(self, coro):
        """Helper to run async methods in tests."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
