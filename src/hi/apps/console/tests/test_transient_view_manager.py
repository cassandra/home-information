import logging
from unittest.mock import Mock, patch

from hi.apps.console.transient_view_manager import TransientViewManager
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestTransientViewManager(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Reset singleton state for each test
        TransientViewManager._instances = {}
        self.manager = TransientViewManager()
        
    def tearDown(self):
        # Clear any suggestions between tests
        self.manager.clear_suggestion()
        super().tearDown()

    def test_transient_view_manager_singleton_behavior(self):
        """Test TransientViewManager singleton pattern - critical for system consistency."""
        manager1 = TransientViewManager()
        manager2 = TransientViewManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_priority_based_replacement_business_logic(self):
        """Test priority-based suggestion replacement - critical business logic for alert prioritization."""
        # Simulate realistic scenario: motion detection followed by critical alarm
        
        # Low priority motion detection from secondary camera
        self.manager.suggest_view_change(
            url='/console/sensor/backyard/video',
            duration_seconds=30,
            priority=10,  # Low priority
            trigger_reason='motion_detection_backyard'
        )
        
        initial_suggestion = self.manager.peek_current_suggestion()
        self.assertEqual(initial_suggestion.url, '/console/sensor/backyard/video')
        
        # High priority motion detection from front door (security concern)
        self.manager.suggest_view_change(
            url='/console/sensor/frontdoor/video',
            duration_seconds=45,
            priority=100,  # High priority security event
            trigger_reason='motion_detection_entrance'
        )
        
        # Should replace with higher priority
        current_suggestion = self.manager.peek_current_suggestion()
        self.assertEqual(current_suggestion.url, '/console/sensor/frontdoor/video')
        self.assertEqual(current_suggestion.priority, 100)
        
        # Lower priority subsequent event should be ignored
        self.manager.suggest_view_change(
            url='/console/sensor/garage/video',
            duration_seconds=30,
            priority=50,  # Medium priority, but lower than current
            trigger_reason='motion_detection_garage'
        )
        
        # Should still have high priority front door suggestion
        final_suggestion = self.manager.peek_current_suggestion()
        self.assertEqual(final_suggestion.url, '/console/sensor/frontdoor/video')
        self.assertEqual(final_suggestion.priority, 100)
        return

    def test_equal_priority_replacement_for_newer_events(self):
        """Test equal priority replacement - ensures newer events of same importance are shown."""
        # Realistic scenario: Multiple motion events of same priority
        # User should see the most recent one
        
        self.manager.suggest_view_change(
            url='/console/sensor/zone1/video',
            duration_seconds=30,
            priority=50,
            trigger_reason='motion_zone1'
        )
        
        # Same priority event from different zone
        self.manager.suggest_view_change(
            url='/console/sensor/zone2/video',
            duration_seconds=30,
            priority=50,  # Same priority
            trigger_reason='motion_zone2'
        )
        
        # Should have the newer suggestion
        suggestion = self.manager.peek_current_suggestion()
        self.assertEqual(suggestion.url, '/console/sensor/zone2/video')
        self.assertEqual(suggestion.trigger_reason, 'motion_zone2')
        return

    def test_get_and_clear_pattern_for_api_consumption(self):
        """Test get_current_suggestion consumption pattern - critical for API endpoint behavior."""
        # This simulates how the API status endpoint consumes suggestions
        
        self.manager.suggest_view_change(
            url='/console/sensor/123/video',
            duration_seconds=30,
            priority=75,
            trigger_reason='motion_alarm'
        )
        
        # First API call gets the suggestion
        suggestion = self.manager.get_current_suggestion()
        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion.url, '/console/sensor/123/video')
        
        # Subsequent API calls should get None (suggestion consumed)
        next_suggestion = self.manager.get_current_suggestion()
        self.assertIsNone(next_suggestion)
        
        # This prevents the same suggestion from being sent multiple times
        self.assertFalse(self.manager.has_suggestion())
        return

    def test_consider_alert_with_auto_view_enabled(self):
        """Test TransientViewManager considers alerts when auto-view enabled - core business logic."""
        from django.utils import timezone
        from hi.apps.alert.alert import Alert
        from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        from hi.apps.security.enums import SecurityLevel
        
        # Create motion detection alert with camera
        source_details = AlarmSourceDetails(
            detail_attrs={'sensor_id': 'cam_123', 'location': 'Front Door'},
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
        
        alert = Alert(motion_alarm)
        
        # Mock settings to enable auto-view
        with patch('hi.apps.console.transient_view_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            # Mock URL generation at system boundary
            with patch('django.urls.reverse') as mock_reverse:
                mock_reverse.return_value = '/console/sensor/video_stream/cam_123/'
                
                # Initially no suggestion
                self.assertFalse(self.manager.has_suggestion())
                
                # Consider alert for auto-view
                self.manager.consider_alert_for_auto_view(alert)
                
                # Should create suggestion
                self.assertTrue(self.manager.has_suggestion())
                suggestion = self.manager.peek_current_suggestion()
                self.assertEqual(suggestion.url, '/console/sensor/video_stream/cam_123/')
                self.assertEqual(suggestion.duration_seconds, 30)
                self.assertEqual(suggestion.priority, motion_alarm.alarm_level.priority)
                self.assertEqual(suggestion.trigger_reason, 'event_alert')

    def test_consider_alert_with_auto_view_disabled(self):
        """Test TransientViewManager ignores alerts when auto-view disabled - settings integration."""
        from django.utils import timezone
        from hi.apps.alert.alert import Alert
        from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        from hi.apps.security.enums import SecurityLevel
        
        # Create motion detection alert
        source_details = AlarmSourceDetails(
            detail_attrs={'sensor_id': 'cam_123'},
            image_url=None
        )
        
        motion_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Motion detected',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()
        )
        
        alert = Alert(motion_alarm)
        
        # Mock settings to disable auto-view
        with patch('hi.apps.console.transient_view_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = False
            mock_helper_class.return_value = mock_helper
            
            # Consider alert for auto-view
            self.manager.consider_alert_for_auto_view(alert)
            
            # Should not create suggestion when disabled
            self.assertFalse(self.manager.has_suggestion())

    def test_consider_non_motion_alert_ignored(self):
        """Test TransientViewManager handles alerts without camera view URLs - integration test."""
        from django.utils import timezone
        from hi.apps.alert.alert import Alert
        from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        from hi.apps.security.enums import SecurityLevel
        
        # Create non-motion EVENT alarm
        source_details = AlarmSourceDetails(
            detail_attrs={'sensor_id': 'cam_123'},
            image_url=None
        )
        
        status_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='device_status',  # Not motion-related
            alarm_level=AlarmLevel.INFO,
            title='Device status update',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()
        )
        
        alert = Alert(status_alarm)
        
        # Mock settings to enable auto-view
        with patch('hi.apps.console.transient_view_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper_class.return_value = mock_helper
            
            # Consider alert for auto-view
            self.manager.consider_alert_for_auto_view(alert)
            
            # Should not create suggestion for non-motion events
            self.assertFalse(self.manager.has_suggestion())

    def test_consider_alert_without_view_url_ignored(self):
        """Test TransientViewManager ignores alerts without view URLs - integration with Alert model."""
        from django.utils import timezone
        from hi.apps.alert.alert import Alert
        from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        from hi.apps.security.enums import SecurityLevel
        
        # Create motion alarm but without sensor_id (no view URL)
        source_details = AlarmSourceDetails(
            detail_attrs={'location': 'Front Door'},  # No sensor_id
            image_url=None
        )
        
        motion_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Motion detected',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=timezone.now()
        )
        
        alert = Alert(motion_alarm)
        
        # Mock settings to enable auto-view
        with patch('hi.apps.console.transient_view_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper_class.return_value = mock_helper
            
            # Consider alert for auto-view
            self.manager.consider_alert_for_auto_view(alert)
            
            # Should not create suggestion when no view URL available
            self.assertFalse(self.manager.has_suggestion())
