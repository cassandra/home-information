import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from hi.apps.alert.alert_manager import AlertManager
from hi.apps.alert.alarm import Alarm, AlarmSourceDetails
from hi.apps.alert.enums import AlarmLevel, AlarmSource
from hi.apps.console.transient_view_manager import TransientViewManager
from hi.apps.security.enums import SecurityLevel
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAlertManagerAutoViewIntegration(BaseTestCase):
    """Test AlertManager integration with TransientViewManager for auto-view switching."""

    def setUp(self):
        super().setUp()
        # Reset singletons for test isolation
        AlertManager._instances = {}
        TransientViewManager._instances = {}
        
        self.alert_manager = AlertManager()
        self.transient_manager = TransientViewManager()
        
    def tearDown(self):
        # Clear any suggestions between tests
        self.transient_manager.clear_suggestion()
        super().tearDown()

    def test_motion_event_alarm_triggers_auto_view_suggestion(self):
        """Test that motion detection alarms trigger auto-view suggestions - critical integration."""
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
            timestamp=datetime.now()
        )
        
        # Mock console settings to enable auto-view
        with patch('hi.apps.alert.alert_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            # Simulate the alert status check that happens during polling
            alert_status_data = self.alert_manager.get_alert_status_data(
                last_alert_status_datetime=datetime.now() - timedelta(seconds=5)
            )
            
            # Initially no suggestion
            self.assertFalse(self.transient_manager.has_suggestion())
            
            # Add the motion alarm (simulating what happens when motion is detected)
            with patch.object(self.alert_manager._alert_queue, 'get_most_recent_alarm', return_value=motion_alarm):
                alert_status_data = self.alert_manager.get_alert_status_data(
                    last_alert_status_datetime=datetime.now() - timedelta(seconds=5)
                )
            
            # Should now have auto-view suggestion
            self.assertTrue(self.transient_manager.has_suggestion())
            
            suggestion = self.transient_manager.peek_current_suggestion()
            self.assertIsNotNone(suggestion)
            self.assertEqual(suggestion.url, '/console/sensor/video-stream/123')
            self.assertEqual(suggestion.duration_seconds, 30)
            self.assertEqual(suggestion.priority, AlarmLevel.WARNING.priority)
            self.assertIn('motion', suggestion.trigger_reason)
        return

    def test_non_motion_event_alarm_does_not_trigger_auto_view(self):
        """Test that non-motion EVENT alarms don't trigger auto-view - business logic validation."""
        # Create a different type of event alarm (not motion)
        source_details = AlarmSourceDetails(
            detail_attrs={'entity_id': '456'},
            image_url=None
        )
        
        door_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='door_open',  # Not a motion type
            alarm_level=AlarmLevel.INFO,
            title='Door opened',
            source_details_list=[source_details],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=60,
            timestamp=datetime.now()
        )
        
        with patch('hi.apps.alert.alert_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            with patch.object(self.alert_manager._alert_queue, 'get_most_recent_alarm', return_value=door_alarm):
                self.alert_manager.get_alert_status_data(
                    last_alert_status_datetime=datetime.now() - timedelta(seconds=5)
                )
            
            # Should not create auto-view suggestion for non-motion events
            self.assertFalse(self.transient_manager.has_suggestion())
        return

    def test_weather_alarm_does_not_trigger_auto_view_yet(self):
        """Test that WEATHER alarms don't trigger auto-view (not implemented yet) - extensibility validation."""
        weather_alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type='tornado_warning',
            alarm_level=AlarmLevel.CRITICAL,
            title='Tornado Warning',
            source_details_list=[],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=3600,
            timestamp=datetime.now()
        )
        
        with patch('hi.apps.alert.alert_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            with patch.object(self.alert_manager._alert_queue, 'get_most_recent_alarm', return_value=weather_alarm):
                self.alert_manager.get_alert_status_data(
                    last_alert_status_datetime=datetime.now() - timedelta(seconds=5)
                )
            
            # Weather alarms not implemented yet
            self.assertFalse(self.transient_manager.has_suggestion())
        return

    def test_auto_view_disabled_in_settings_prevents_suggestions(self):
        """Test that auto-view respects console settings - settings integration."""
        source_details = AlarmSourceDetails(
            detail_attrs={'sensor_id': '789'},
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
            timestamp=datetime.now()
        )
        
        # Mock console settings with auto-view DISABLED
        with patch('hi.apps.alert.alert_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = False  # Disabled
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            with patch.object(self.alert_manager._alert_queue, 'get_most_recent_alarm', return_value=motion_alarm):
                self.alert_manager.get_alert_status_data(
                    last_alert_status_datetime=datetime.now() - timedelta(seconds=5)
                )
            
            # Should not create suggestion when disabled
            self.assertFalse(self.transient_manager.has_suggestion())
        return

    def test_alarm_priority_affects_suggestion_priority(self):
        """Test that alarm level priority propagates to suggestion priority - priority handling."""
        # Test different alarm levels
        alarm_levels = [
            (AlarmLevel.INFO, 10),
            (AlarmLevel.WARNING, 100),
            (AlarmLevel.CRITICAL, 1000),
        ]
        
        for alarm_level, expected_priority in alarm_levels:
            # Reset transient manager for each test
            self.transient_manager.clear_suggestion()
            
            source_details = AlarmSourceDetails(
                detail_attrs={'sensor_id': f'sensor_{alarm_level.name}'},
                image_url=None
            )
            
            alarm = Alarm(
                alarm_source=AlarmSource.EVENT,
                alarm_type='motion_detection',
                alarm_level=alarm_level,
                title=f'{alarm_level.name} motion detected',
                source_details_list=[source_details],
                security_level=SecurityLevel.OFF,
                alarm_lifetime_secs=300,
                timestamp=datetime.now()
            )
            
            with patch('hi.apps.alert.alert_manager.ConsoleSettingsHelper') as mock_helper_class:
                mock_helper = Mock()
                mock_helper.get_auto_view_enabled.return_value = True
                mock_helper.get_auto_view_duration.return_value = 30
                mock_helper_class.return_value = mock_helper
                
                with patch.object(self.alert_manager._alert_queue, 'get_most_recent_alarm', return_value=alarm):
                    self.alert_manager.get_alert_status_data(
                        last_alert_status_datetime=datetime.now() - timedelta(seconds=5)
                    )
                
                suggestion = self.transient_manager.peek_current_suggestion()
                self.assertIsNotNone(suggestion)
                self.assertEqual(suggestion.priority, expected_priority)
        return

    def test_missing_sensor_id_prevents_camera_url_generation(self):
        """Test that alarms without sensor_id don't generate camera URLs - error handling."""
        # Alarm with entity_id but no sensor_id
        source_details = AlarmSourceDetails(
            detail_attrs={'entity_id': 'entity_123'},  # No sensor_id
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
            timestamp=datetime.now()
        )
        
        with patch('hi.apps.alert.alert_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            with patch.object(self.alert_manager._alert_queue, 'get_most_recent_alarm', return_value=motion_alarm):
                self.alert_manager.get_alert_status_data(
                    last_alert_status_datetime=datetime.now() - timedelta(seconds=5)
                )
            
            # Should not create suggestion without sensor_id for camera URL
            self.assertFalse(self.transient_manager.has_suggestion())
        return

    def test_multiple_alarms_use_recent_alarm_for_suggestion(self):
        """Test that only the most recent alarm triggers auto-view - recent alarm logic."""
        old_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.INFO,
            title='Old motion',
            source_details_list=[
                AlarmSourceDetails(detail_attrs={'sensor_id': 'old_sensor'}, image_url=None)
            ],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=datetime.now() - timedelta(minutes=5)
        )
        
        recent_alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Recent motion',
            source_details_list=[
                AlarmSourceDetails(detail_attrs={'sensor_id': 'recent_sensor'}, image_url=None)
            ],
            security_level=SecurityLevel.OFF,
            alarm_lifetime_secs=300,
            timestamp=datetime.now()
        )
        
        with patch('hi.apps.alert.alert_manager.ConsoleSettingsHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper.get_auto_view_enabled.return_value = True
            mock_helper.get_auto_view_duration.return_value = 30
            mock_helper_class.return_value = mock_helper
            
            # Simulate having both alarms but returning the recent one
            with patch.object(self.alert_manager._alert_queue, 'get_most_recent_alarm', return_value=recent_alarm):
                self.alert_manager.get_alert_status_data(
                    last_alert_status_datetime=datetime.now() - timedelta(seconds=5)
                )
            
            suggestion = self.transient_manager.peek_current_suggestion()
            self.assertIsNotNone(suggestion)
            self.assertEqual(suggestion.url, '/console/sensor/video-stream/recent_sensor')
            self.assertEqual(suggestion.priority, AlarmLevel.WARNING.priority)
        return