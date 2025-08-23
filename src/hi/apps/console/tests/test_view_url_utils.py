import logging
from unittest.mock import Mock

from hi.apps.console.view_url_utils import ViewUrlUtils
from hi.apps.entity.models import Entity, EntityState  
from hi.apps.entity.enums import EntityStateType
from hi.apps.sense.models import Sensor
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestViewUrlUtils(BaseTestCase):
    """Test ViewUrlUtils for generating view URLs from alarms and sensors."""

    def setUp(self):
        super().setUp()
        
        # Create entity with video stream capability
        self.video_entity = Entity.objects.create(
            integration_id='test.camera.video',
            integration_name='test_integration', 
            name='Video Camera',
            entity_type_str='camera',
            has_video_stream=True
        )
        
        # Create entity without video stream capability
        self.non_video_entity = Entity.objects.create(
            integration_id='test.sensor.temp',
            integration_name='test_integration',
            name='Temperature Sensor', 
            entity_type_str='sensor',
            has_video_stream=False
        )
        
        # Create entity states and sensors
        self.video_motion_state = EntityState.objects.create(
            entity=self.video_entity,
            entity_state_type_str=str(EntityStateType.MOVEMENT),
            name='motion'
        )
        self.video_motion_sensor = Sensor.objects.create(
            entity_state=self.video_motion_state,
            integration_id='test.motion.video',
            integration_name='test_integration',
            name='Video Motion Sensor'
        )
        
        self.temp_state = EntityState.objects.create(
            entity=self.non_video_entity,
            entity_state_type_str=str(EntityStateType.TEMPERATURE),
            name='temperature'
        )
        self.temp_sensor = Sensor.objects.create(
            entity_state=self.temp_state,
            integration_id='test.temp.sensor',
            integration_name='test_integration', 
            name='Temperature Sensor'
        )

    def test_get_view_url_for_alarm_returns_video_url_for_video_entity(self):
        """Test that alarms from video-capable entities return video stream URLs."""
        from hi.apps.alert.alarm import Alarm
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        from hi.apps.security.enums import SecurityLevel
        from hi.apps.sense.transient_models import SensorResponse
        from hi.integrations.transient_models import IntegrationKey
        import hi.apps.common.datetimeproxy as datetimeproxy
        
        # Create alarm with sensor from video-capable entity
        sensor_response = SensorResponse(
            integration_key=IntegrationKey('test', 'motion.video'),
            value='active',
            timestamp=datetimeproxy.now(),
            sensor=self.video_motion_sensor,
            detail_attrs={},
            source_image_url=None,
            has_video_stream=False
        )
        
        alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='motion_detection',
            alarm_level=AlarmLevel.WARNING,
            title='Motion detected',
            sensor_response_list=[sensor_response],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now()
        )
        
        # Test URL generation
        view_url = ViewUrlUtils.get_view_url_for_alarm(alarm)
        
        self.assertIsNotNone(view_url)
        self.assertIn('/console/entity/video-stream/', view_url)
        self.assertIn(str(self.video_entity.id), view_url)
        
    def test_get_view_url_for_alarm_returns_none_for_non_video_entity(self):
        """Test that alarms from non-video entities return None."""
        from hi.apps.alert.alarm import Alarm
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        from hi.apps.security.enums import SecurityLevel
        from hi.apps.sense.transient_models import SensorResponse
        from hi.integrations.transient_models import IntegrationKey
        import hi.apps.common.datetimeproxy as datetimeproxy
        
        # Create alarm with sensor from non-video entity
        sensor_response = SensorResponse(
            integration_key=IntegrationKey('test', 'temp.sensor'),
            value='22.5',
            timestamp=datetimeproxy.now(),
            sensor=self.temp_sensor,
            detail_attrs={},
            source_image_url=None,
            has_video_stream=False
        )
        
        alarm = Alarm(
            alarm_source=AlarmSource.EVENT,
            alarm_type='temperature_change',
            alarm_level=AlarmLevel.INFO,
            title='Temperature reading',
            sensor_response_list=[sensor_response],
            security_level=SecurityLevel.LOW,
            alarm_lifetime_secs=300,
            timestamp=datetimeproxy.now()
        )
        
        # Test URL generation
        view_url = ViewUrlUtils.get_view_url_for_alarm(alarm)
        
        self.assertIsNone(view_url)
        
    def test_get_view_url_for_alarm_returns_none_for_alarm_without_sensors(self):
        """Test that alarms without sensors return None."""
        from hi.apps.alert.alarm import Alarm
        from hi.apps.alert.enums import AlarmLevel, AlarmSource
        from hi.apps.security.enums import SecurityLevel
        from hi.apps.sense.transient_models import SensorResponse
        from hi.integrations.transient_models import IntegrationKey
        import hi.apps.common.datetimeproxy as datetimeproxy
        
        # Create alarm with sensor response but no sensor object
        sensor_response = SensorResponse(
            integration_key=IntegrationKey('test', 'weather'),
            value='active',
            timestamp=datetimeproxy.now(),
            sensor=None,  # No sensor object
            detail_attrs={'event': 'Tornado Warning'},
            source_image_url=None,
            has_video_stream=False
        )
        
        alarm = Alarm(
            alarm_source=AlarmSource.WEATHER,
            alarm_type='tornado',
            alarm_level=AlarmLevel.CRITICAL,
            title='Tornado Warning',
            sensor_response_list=[sensor_response],
            security_level=SecurityLevel.HIGH,
            alarm_lifetime_secs=3600,
            timestamp=datetimeproxy.now()
        )
        
        # Test URL generation
        view_url = ViewUrlUtils.get_view_url_for_alarm(alarm)
        
        self.assertIsNone(view_url)
        
    def test_get_view_url_for_sensor_id_returns_video_url_for_video_entity(self):
        """Test direct sensor ID lookup for video-capable entity."""
        view_url = ViewUrlUtils._get_view_url_for_sensor_id(self.video_motion_sensor.id)
        
        self.assertIsNotNone(view_url)
        self.assertIn('/console/entity/video-stream/', view_url)
        self.assertIn(str(self.video_entity.id), view_url)
        
    def test_get_view_url_for_sensor_id_returns_none_for_non_video_entity(self):
        """Test direct sensor ID lookup for non-video entity."""
        view_url = ViewUrlUtils._get_view_url_for_sensor_id(self.temp_sensor.id)
        
        self.assertIsNone(view_url)
        
    def test_get_view_url_for_sensor_id_handles_nonexistent_sensor(self):
        """Test that nonexistent sensor IDs are handled gracefully."""
        view_url = ViewUrlUtils._get_view_url_for_sensor_id('nonexistent-sensor-id')
        
        self.assertIsNone(view_url)