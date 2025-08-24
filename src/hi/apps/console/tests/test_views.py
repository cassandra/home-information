import logging
from datetime import datetime
from unittest.mock import Mock, patch

from django.urls import reverse
from django.utils import timezone
from django.http import Http404
from django.core.exceptions import BadRequest

from hi.apps.console.views import EntityVideoStreamView, EntityVideoSensorHistoryView
from hi.apps.console.transient_models import EntitySensorHistoryData
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityVideoStreamView(BaseTestCase):
    """Test EntityVideoStreamView for displaying video streams."""

    def setUp(self):
        super().setUp()
        
        # Create test entity with video stream capability
        self.video_entity = Entity.objects.create(
            integration_id='test.camera.front',
            integration_name='test_integration',
            name='Front Door Camera',
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

    def test_get_main_template_name_returns_correct_template(self):
        """Test that the view returns the correct template name."""
        view = EntityVideoStreamView()
        template_name = view.get_main_template_name()
        
        self.assertEqual(template_name, 'console/panes/entity_video_pane.html')
        
    def test_view_integration_with_url_routing(self):
        """Test that the view integrates correctly with URL routing."""
        # This tests the actual URL pattern and view integration
        url = reverse('console_entity_video_stream', kwargs={'entity_id': self.video_entity.id})
        
        self.assertIn('/console/entity/video-stream/', url)
        self.assertIn(str(self.video_entity.id), url)
        
    def test_view_inheritance_from_higrideview(self):
        """Test that EntityVideoStreamView correctly inherits from HiGridView."""
        view = EntityVideoStreamView()
        
        # Should have HiGridView methods
        self.assertTrue(hasattr(view, 'get_main_template_name'))
        self.assertTrue(hasattr(view, 'get_main_template_context'))
        self.assertTrue(callable(view.get_main_template_name))
        self.assertTrue(callable(view.get_main_template_context))

    def test_view_class_exists_and_is_importable(self):
        """Test that the EntityVideoStreamView class exists and can be imported."""
        # This is a basic smoke test to ensure the view is properly defined
        from hi.apps.console.views import EntityVideoStreamView
        
        self.assertTrue(EntityVideoStreamView)
        self.assertTrue(hasattr(EntityVideoStreamView, 'get_main_template_name'))
        self.assertTrue(hasattr(EntityVideoStreamView, 'get_main_template_context'))

    def test_video_entity_has_correct_attributes(self):
        """Test that test video entity has correct attributes for testing."""
        self.assertEqual(self.video_entity.name, 'Front Door Camera')
        self.assertTrue(self.video_entity.has_video_stream)
        self.assertEqual(self.video_entity.integration_id, 'test.camera.front')

    def test_non_video_entity_has_correct_attributes(self):
        """Test that test non-video entity has correct attributes for testing."""
        self.assertEqual(self.non_video_entity.name, 'Temperature Sensor')
        self.assertFalse(self.non_video_entity.has_video_stream)
        self.assertEqual(self.non_video_entity.integration_id, 'test.sensor.temp')


class TestEntityVideoSensorHistoryView(BaseTestCase):
    """Test EntityVideoSensorHistoryView for timeline preservation functionality."""

    def setUp(self):
        super().setUp()
        
        # Create test entity with video stream capability
        self.video_entity = Entity.objects.create(
            integration_id='test.camera.security',
            integration_name='test_integration',
            name='Security Camera',
            entity_type_str='camera',
            has_video_stream=True
        )
        
        # Create entity state for the video entity
        self.entity_state = EntityState.objects.create(
            entity=self.video_entity,
            entity_state_type_str='motion',
            name='Motion Detection'
        )
        
        # Create sensor with video capability
        self.video_sensor = Sensor.objects.create(
            integration_id='test.sensor.motion',
            integration_name='test_integration',
            name='Motion Sensor',
            entity_state=self.entity_state,
            sensor_type_str='binary',
            provides_video_stream=True
        )
        
        # Create sensor history records for testing
        base_time = timezone.now()
        self.sensor_history_records = []
        for i in range(5):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value='active' if i % 2 == 0 else 'idle',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True,
                details='{"test": "data"}'
            )
            self.sensor_history_records.append(record)

    def test_get_main_template_name_returns_correct_template(self):
        """Test that the view returns the correct template name."""
        view = EntityVideoSensorHistoryView()
        template_name = view.get_main_template_name()
        
        self.assertEqual(template_name, 'console/panes/entity_video_sensor_history.html')

    def test_view_requires_valid_entity_id(self):
        """Test that view raises Http404 for invalid entity ID."""
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        with self.assertRaises(Http404) as context:
            view.get_main_template_context(
                request, 
                entity_id=99999, 
                sensor_id=self.video_sensor.id
            )
        self.assertEqual(str(context.exception), 'Entity not found.')

    def test_view_requires_entity_with_video_capability(self):
        """Test that view raises BadRequest for entity without video streams."""
        non_video_entity = Entity.objects.create(
            integration_id='test.sensor.temp',
            integration_name='test_integration',
            name='Temperature Sensor',
            entity_type_str='sensor',
            has_video_stream=False
        )
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        with self.assertRaises(BadRequest) as context:
            view.get_main_template_context(
                request,
                entity_id=non_video_entity.id,
                sensor_id=self.video_sensor.id
            )
        self.assertEqual(str(context.exception), 'Entity does not have video stream capability.')

    def test_view_requires_valid_sensor_id(self):
        """Test that view raises Http404 for invalid sensor ID."""
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        with self.assertRaises(Http404) as context:
            view.get_main_template_context(
                request,
                entity_id=self.video_entity.id,
                sensor_id=99999
            )
        self.assertEqual(str(context.exception), 'Sensor not found for this entity.')

    @patch('hi.apps.console.views.VideoStreamBrowsingHelper.build_sensor_history_data')
    def test_view_calls_helper_with_correct_parameters_no_window_context(self, mock_build_data):
        """Test that view calls helper with correct parameters when no window context provided."""
        mock_build_data.return_value = Mock(spec=EntitySensorHistoryData)
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id,
            sensor_history_id=123
        )
        
        mock_build_data.assert_called_once_with(
            sensor=self.video_sensor,
            sensor_history_id=123,
            preserve_window_start=None,
            preserve_window_end=None
        )

    @patch('hi.apps.console.views.VideoStreamBrowsingHelper.build_sensor_history_data')
    def test_view_parses_window_context_parameters(self, mock_build_data):
        """Test that view correctly parses window context parameters."""
        mock_build_data.return_value = Mock(spec=EntitySensorHistoryData)
        
        # Create timezone-aware test timestamps
        window_start = timezone.now() - timezone.timedelta(hours=2)
        window_end = timezone.now()
        window_start_timestamp = int(window_start.timestamp())
        window_end_timestamp = int(window_end.timestamp())
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id,
            sensor_history_id=123,
            window_start=str(window_start_timestamp),
            window_end=str(window_end_timestamp)
        )
        
        # Verify helper was called with timezone-aware datetime objects
        call_args = mock_build_data.call_args
        self.assertEqual(call_args[1]['sensor'], self.video_sensor)
        self.assertEqual(call_args[1]['sensor_history_id'], 123)
        
        # Check that timestamps were converted to timezone-aware datetimes
        preserve_start = call_args[1]['preserve_window_start']
        preserve_end = call_args[1]['preserve_window_end']
        self.assertIsInstance(preserve_start, datetime)
        self.assertIsInstance(preserve_end, datetime)
        self.assertIsNotNone(preserve_start.tzinfo)
        self.assertIsNotNone(preserve_end.tzinfo)

    @patch('hi.apps.console.views.VideoStreamBrowsingHelper.build_sensor_history_data')
    def test_view_handles_invalid_timestamp_parameters(self, mock_build_data):
        """Test that view handles invalid timestamp parameters gracefully."""
        mock_build_data.return_value = Mock(spec=EntitySensorHistoryData)
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        # Test with invalid timestamp values
        view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id,
            sensor_history_id=123,
            window_start='invalid_timestamp',
            window_end='also_invalid'
        )
        
        # Should fall back to None values when timestamps are invalid
        mock_build_data.assert_called_once_with(
            sensor=self.video_sensor,
            sensor_history_id=123,
            preserve_window_start=None,
            preserve_window_end=None
        )

    @patch('hi.apps.console.views.VideoStreamBrowsingHelper.build_sensor_history_data')
    def test_view_returns_correct_context_structure(self, mock_build_data):
        """Test that view returns expected context structure."""
        mock_sensor_history_data = Mock(spec=EntitySensorHistoryData)
        mock_build_data.return_value = mock_sensor_history_data
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        context = view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id
        )
        
        # Verify context structure
        self.assertEqual(context['entity'], self.video_entity)
        self.assertEqual(context['sensor'], self.video_sensor)
        self.assertEqual(context['sensor_history_data'], mock_sensor_history_data)
        
        # Verify view parameters were set
        request.view_parameters.to_session.assert_called_once_with(request)

    def test_view_integration_with_url_routing_basic(self):
        """Test basic URL routing integration."""
        url = reverse('console_entity_video_sensor_history', kwargs={
            'entity_id': self.video_entity.id,
            'sensor_id': self.video_sensor.id
        })
        
        self.assertIn('/console/entity/video-sensor-history/', url)
        self.assertIn(str(self.video_entity.id), url)
        self.assertIn(str(self.video_sensor.id), url)

    def test_view_integration_with_url_routing_with_history_id(self):
        """Test URL routing integration with sensor history ID."""
        url = reverse('console_entity_video_sensor_history_detail', kwargs={
            'entity_id': self.video_entity.id,
            'sensor_id': self.video_sensor.id,
            'sensor_history_id': 123
        })
        
        self.assertIn('/console/entity/video-sensor-history/', url)
        self.assertIn(str(self.video_entity.id), url)
        self.assertIn(str(self.video_sensor.id), url)
        self.assertIn('123', url)

    def test_view_integration_with_url_routing_with_window_context(self):
        """Test URL routing integration with window context parameters."""
        url = reverse('console_entity_video_sensor_history_detail_with_context', kwargs={
            'entity_id': self.video_entity.id,
            'sensor_id': self.video_sensor.id,
            'sensor_history_id': 123,
            'window_start': '1640995200',  # Example timestamp
            'window_end': '1641081600'
        })
        
        self.assertIn('/console/entity/video-sensor-history/', url)
        self.assertIn(str(self.video_entity.id), url)
        self.assertIn(str(self.video_sensor.id), url)
        self.assertIn('123', url)
        self.assertIn('1640995200', url)
        self.assertIn('1641081600', url)
