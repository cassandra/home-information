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
        
        # Reset singletons for next test
        AlertManager._instance = None
        TransientViewManager._instance = None
        
        super().tearDown()

    def test_alert_manager_delegates_new_alerts_to_transient_view_manager(self):
        """Test AlertManager delegates new alerts to TransientViewManager - core integration."""
        from hi.apps.entity.models import Entity, EntityState
        from hi.apps.entity.enums import EntityStateType
        from hi.apps.sense.models import Sensor
        
        # Create test data - entity with both motion and video stream sensors
        entity = Entity.objects.create(
            integration_id='test.camera.front_door',
            integration_name='test_integration',
            name='Front Door Camera',
            entity_type_str='camera'
        )
        
        # Create motion sensor state
        motion_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str=str(EntityStateType.MOVEMENT),
            name='motion'
        )
        motion_sensor = Sensor.objects.create(
            entity_state=motion_state,
            integration_id='test.motion.front_door',
            integration_name='test_integration',
            name='Motion Sensor'
        )
        
        # Create video stream sensor state on same entity
        video_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str=str(EntityStateType.VIDEO_STREAM),
            name='video_stream'
        )
        video_sensor = Sensor.objects.create(
            entity_state=video_state,
            integration_id='test.video.front_door',
            integration_name='test_integration',
            name='Video Stream'
        )
        
        # Create realistic motion detection alarm with sensor details
        source_details = AlarmSourceDetails(
            detail_attrs={'location': 'Front Door'},
            image_url=None,
            sensor_id=motion_sensor.id  # Motion sensor that triggered the alarm
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
            
            # Add alarm to create an alert
            self.run_async_test(self.alert_manager.add_alarm(motion_alarm))
            
            # Get alert status data (this should trigger delegation to TransientViewManager)
            self.alert_manager.get_alert_status_data(
                last_alert_status_datetime=timezone.now() - timedelta(seconds=5)
            )
            
            # Verify delegation created a suggestion (test actual behavior, not mock calls)
            self.assertTrue(self.transient_manager.has_suggestion())
            
            # Verify the video sensor ID is used in the URL
            suggestion = self.transient_manager.peek_current_suggestion()
            expected_url = f'/console/sensor/video-stream/{video_sensor.id}'
            self.assertEqual(suggestion.url, expected_url)

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
        from hi.apps.entity.models import Entity, EntityState
        from hi.apps.entity.enums import EntityStateType
        from hi.apps.sense.models import Sensor
        
        # Create test data for two different cameras
        # First camera entity
        entity1 = Entity.objects.create(
            integration_id='test.camera.one',
            integration_name='test_integration',
            name='Camera One',
            entity_type_str='camera'
        )
        motion_state1 = EntityState.objects.create(
            entity=entity1,
            entity_state_type_str=str(EntityStateType.MOVEMENT),
            name='motion'
        )
        motion_sensor1 = Sensor.objects.create(
            entity_state=motion_state1,
            integration_id='test.motion.one',
            integration_name='test_integration',
            name='Motion Sensor 1'
        )
        # video_state1 and video_sensor1 not needed for this test since we only check video_sensor2
        
        # Second camera entity
        entity2 = Entity.objects.create(
            integration_id='test.camera.two',
            integration_name='test_integration',
            name='Camera Two',
            entity_type_str='camera'
        )
        motion_state2 = EntityState.objects.create(
            entity=entity2,
            entity_state_type_str=str(EntityStateType.MOVEMENT),
            name='motion'
        )
        motion_sensor2 = Sensor.objects.create(
            entity_state=motion_state2,
            integration_id='test.motion.two',
            integration_name='test_integration',
            name='Motion Sensor 2'
        )
        video_state2 = EntityState.objects.create(
            entity=entity2,
            entity_state_type_str=str(EntityStateType.VIDEO_STREAM),
            name='video_stream'
        )
        video_sensor2 = Sensor.objects.create(
            entity_state=video_state2,
            integration_id='test.video.two',
            integration_name='test_integration',
            name='Video Stream 2'
        )
        
        # Create two different alarms
        source_details_1 = AlarmSourceDetails(
            detail_attrs={},
            image_url=None,
            sensor_id=motion_sensor1.id  # First motion sensor
        )
        
        source_details_2 = AlarmSourceDetails(
            detail_attrs={},
            image_url=None,
            sensor_id=motion_sensor2.id  # Second motion sensor
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
            
            # Get alert status - should delegate only the new alert
            # Use timestamp that excludes old alarm but includes new one
            self.alert_manager.get_alert_status_data(
                last_alert_status_datetime=timezone.now() - timedelta(seconds=5)  # Between old (30s ago) and new (2s ago)
            )
            
            # Should have created a suggestion based on the new alert only
            self.assertTrue(self.transient_manager.has_suggestion())
            
            # The suggestion should be based on the new alert's video sensor_id
            suggestion = self.transient_manager.peek_current_suggestion()
            expected_url = f'/console/sensor/video-stream/{video_sensor2.id}'
            self.assertEqual(suggestion.url, expected_url)

    def run_async_test(self, coro):
        """Helper to run async methods in tests."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
