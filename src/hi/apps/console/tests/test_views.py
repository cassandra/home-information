import logging
from unittest.mock import Mock

from django.urls import reverse
from django.utils import timezone
from django.http import Http404
from django.core.exceptions import BadRequest

from hi.apps.console.views import (
    EntityVideoStreamView, EntityVideoSensorHistoryView,
    EntityVideoSensorHistoryEarlierView, EntityVideoSensorHistoryLaterView
)
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

    def test_view_requires_sensor_with_video_capability(self):
        """Test that view raises BadRequest for sensor without video stream capability."""
        # Create a sensor that doesn't provide video streams
        non_video_sensor = Sensor.objects.create(
            integration_id='test.sensor.temp',
            integration_name='test_integration',
            name='Temperature Sensor',
            entity_state=self.entity_state,
            sensor_type_str='sensor',
            provides_video_stream=False
        )
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        with self.assertRaises(BadRequest) as context:
            view.get_main_template_context(
                request,
                entity_id=self.video_entity.id,
                sensor_id=non_video_sensor.id
            )
        self.assertEqual(str(context.exception), 'Sensor does not provide video stream capability.')

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

    def test_view_returns_correct_context_structure_with_real_data(self):
        """Test that view returns expected context structure with real sensor history data."""
        # Clear any existing sensor history from setUp
        SensorHistory.objects.filter(sensor=self.video_sensor).delete()
        
        # Create real sensor history records for testing
        base_time = timezone.now()
        test_records = []
        for i in range(3):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'motion_detected_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True,
                details=f'{{"event": "test_{i}", "confidence": 0.9}}'
            )
            test_records.append(record)
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        context = view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id
        )
        
        # Verify context structure with real data
        self.assertEqual(context['entity'], self.video_entity)
        self.assertEqual(context['sensor'], self.video_sensor)
        
        # Test actual EntitySensorHistoryData content
        sensor_history_data = context['sensor_history_data']
        self.assertIsInstance(sensor_history_data, EntitySensorHistoryData)
        self.assertEqual(len(sensor_history_data.sensor_responses), 3)
        
        # Verify sensor responses contain real data
        first_response = sensor_history_data.sensor_responses[0]
        self.assertTrue(hasattr(first_response, 'sensor_history_id'))
        self.assertIn('motion_detected', first_response.value)
        
        # Verify timeline groups are created
        self.assertIsInstance(sensor_history_data.timeline_groups, list)
        
        # Verify pagination metadata is present
        self.assertIsInstance(sensor_history_data.pagination_metadata, dict)
        self.assertIn('has_older_records', sensor_history_data.pagination_metadata)
        self.assertIn('has_newer_records', sensor_history_data.pagination_metadata)
        
        # Verify view parameters were set
        request.view_parameters.to_session.assert_called_once_with(request)

    def test_view_handles_earlier_pagination_with_real_data(self):
        """Test that view handles 'earlier' pagination with actual sensor history data."""
        # Clear any existing sensor history
        SensorHistory.objects.filter(sensor=self.video_sensor).delete()
        
        # Create real sensor history records across a time range
        base_time = timezone.now()
        older_records = []
        newer_records = []
        
        # Create 10 older records (more than 2 hours ago)
        for i in range(10):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'older_motion_{i}',
                response_datetime=base_time - timezone.timedelta(hours=3 + i),
                has_video_stream=True,
                details=f'{{"event": "older_{i}", "confidence": 0.8}}'
            )
            older_records.append(record)
        
        # Create 5 newer records (within last 2 hours)
        for i in range(5):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'newer_motion_{i}',
                response_datetime=base_time - timezone.timedelta(minutes=30 * i),
                has_video_stream=True,
                details=f'{{"event": "newer_{i}", "confidence": 0.9}}'
            )
            newer_records.append(record)
        
        # Test pagination to earlier records using timestamp from 2 hours ago
        pivot_time = base_time - timezone.timedelta(hours=2)
        pivot_timestamp = str(int(pivot_time.timestamp()))
        
        view = EntityVideoSensorHistoryEarlierView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        context = view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id,
            timestamp=pivot_timestamp
        )
        
        # Test actual pagination behavior
        sensor_history_data = context['sensor_history_data']
        self.assertIsInstance(sensor_history_data, EntitySensorHistoryData)
        
        # Should return earlier records (from older_records)
        self.assertGreater(len(sensor_history_data.sensor_responses), 0)
        
        # All returned records should be older than pivot time
        for response in sensor_history_data.sensor_responses:
            self.assertLess(response.timestamp, pivot_time)
        
        # Verify pagination metadata indicates more records available
        pagination_meta = sensor_history_data.pagination_metadata
        self.assertIn('has_older_records', pagination_meta)
        self.assertIn('has_newer_records', pagination_meta)
        self.assertTrue(pagination_meta['has_newer_records'])  # Should have newer records available

    def test_view_handles_later_pagination_with_real_data(self):
        """Test that view handles 'later' pagination with actual sensor history data."""
        # Clear any existing sensor history
        SensorHistory.objects.filter(sensor=self.video_sensor).delete()
        
        # Create real sensor history records across a time range
        base_time = timezone.now()
        older_records = []
        newer_records = []
        
        # Create 8 older records (more than 4 hours ago)
        for i in range(8):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'older_motion_{i}',
                response_datetime=base_time - timezone.timedelta(hours=5 + i),
                has_video_stream=True,
                details=f'{{"event": "older_{i}", "confidence": 0.7}}'
            )
            older_records.append(record)
        
        # Create 6 newer records (within last 3 hours) with more spacing
        for i in range(6):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'newer_motion_{i}',
                response_datetime=base_time - timezone.timedelta(hours=2.5) + timezone.timedelta(minutes=15 * i),
                has_video_stream=True,
                details=f'{{"event": "newer_{i}", "confidence": 0.95}}'
            )
            newer_records.append(record)
        
        # Test pagination to later records using timestamp from 4 hours ago
        pivot_time = base_time - timezone.timedelta(hours=4)
        pivot_timestamp = str(int(pivot_time.timestamp()))
        
        view = EntityVideoSensorHistoryLaterView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        context = view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id,
            timestamp=pivot_timestamp
        )
        
        # Test actual pagination behavior
        sensor_history_data = context['sensor_history_data']
        self.assertIsInstance(sensor_history_data, EntitySensorHistoryData)
        
        # Should return later records (from newer_records)
        self.assertGreater(len(sensor_history_data.sensor_responses), 0)
        
        # All returned records should be newer than pivot time
        for response in sensor_history_data.sensor_responses:
            self.assertGreater(response.timestamp, pivot_time)
        
        # Verify pagination metadata indicates more records available
        pagination_meta = sensor_history_data.pagination_metadata
        self.assertIn('has_older_records', pagination_meta)
        self.assertIn('has_newer_records', pagination_meta)
        self.assertTrue(pagination_meta['has_older_records'])  # Should have older records available
        
        # Test that responses contain expected newer data
        response_values = [r.value for r in sensor_history_data.sensor_responses]
        self.assertTrue(any('newer_motion' in value for value in response_values))

    def test_view_handles_window_context_parameters_with_real_data(self):
        """Test that view handles window context parameters with actual sensor history data."""
        # Clear any existing sensor history
        SensorHistory.objects.filter(sensor=self.video_sensor).delete()
        
        # Create real sensor history records within specific time windows
        base_time = timezone.now()
        
        # Records outside the window (should not appear in results)
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='outside_before_window',
            response_datetime=base_time - timezone.timedelta(hours=4),
            has_video_stream=True
        )
        
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='outside_after_window',
            response_datetime=base_time,
            has_video_stream=True
        )
        
        # Records inside the window (should appear in results)
        window_records = []
        for i in range(3):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'inside_window_{i}',
                response_datetime=base_time - timezone.timedelta(hours=2) + timezone.timedelta(minutes=20 * i),
                has_video_stream=True,
                details=f'{{"window_test": "record_{i}"}}'
            )
            window_records.append(record)
        
        # Define window boundaries (2.5 hours ago to 1.5 hours ago)
        window_start_time = base_time - timezone.timedelta(hours=2.5)
        window_end_time = base_time - timezone.timedelta(hours=1.5)
        window_start_timestamp = str(int(window_start_time.timestamp()))
        window_end_timestamp = str(int(window_end_time.timestamp()))
        
        # Use the middle record as the target
        target_record = window_records[1]
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        context = view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id,
            sensor_history_id=target_record.id,
            window_start=window_start_timestamp,
            window_end=window_end_timestamp
        )
        
        # Test actual window preservation behavior
        sensor_history_data = context['sensor_history_data']
        self.assertIsInstance(sensor_history_data, EntitySensorHistoryData)
        
        # Should only return records within the window
        response_values = [r.value for r in sensor_history_data.sensor_responses]
        
        # Verify only window records are included
        self.assertTrue(any('inside_window' in value for value in response_values))
        self.assertNotIn('outside_before_window', response_values)
        self.assertNotIn('outside_after_window', response_values)
        
        # Verify window timestamps are preserved
        self.assertIsNotNone(sensor_history_data.window_start_timestamp)
        self.assertIsNotNone(sensor_history_data.window_end_timestamp)
        
        # Verify current sensor response corresponds to target record
        if sensor_history_data.current_sensor_response:
            self.assertEqual(sensor_history_data.current_sensor_response.sensor_history_id, target_record.id)

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

    def test_view_handles_malformed_sensor_data_gracefully(self):
        """Test error boundary: malformed sensor data with invalid details JSON."""
        # Create sensor history with malformed JSON details
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='active',
            response_datetime=timezone.now(),
            has_video_stream=True,
            details='invalid-json-format{not valid}'
        )
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        # Current behavior: malformed JSON causes JSONDecodeError
        # This test documents the current behavior and identifies improvement opportunity
        with self.assertRaises(Exception) as context_manager:
            view.get_main_template_context(
                request,
                entity_id=self.video_entity.id,
                sensor_id=self.video_sensor.id
            )
        
        # Verify it's a JSON decode error as expected
        exception = context_manager.exception
        self.assertTrue(
            'JSON' in str(type(exception)) or 'json' in str(exception).lower(),
            f"Expected JSON-related error, got: {type(exception)} - {exception}"
        )

    def test_view_handles_timezone_conversion_edge_cases(self):
        """Test error boundary: timezone conversion with various timestamp formats."""
        view = EntityVideoSensorHistoryEarlierView()
        request = Mock()
        request.view_parameters = Mock() 
        request.view_parameters.to_session = Mock()
        
        # Test edge case timestamps
        edge_case_timestamps = [
            '0',  # Unix epoch
            '2147483647',  # 32-bit max timestamp
            str(int(timezone.now().timestamp())),  # Current time
        ]
        
        for timestamp in edge_case_timestamps:
            with self.subTest(timestamp=timestamp):
                # Should handle various timestamp formats without errors
                context = view.get_main_template_context(
                    request,
                    entity_id=self.video_entity.id,
                    sensor_id=self.video_sensor.id,
                    timestamp=timestamp
                )
                
                # Should return valid context structure
                self.assertIsInstance(context['sensor_history_data'], EntitySensorHistoryData)
                self.assertIsInstance(context['sensor_history_data'].pagination_metadata, dict)

    def test_view_handles_empty_result_sets_gracefully(self):
        """Test error boundary: empty sensor history with no video records."""
        # Clear all sensor history
        SensorHistory.objects.filter(sensor=self.video_sensor).delete()
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        context = view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id
        )
        
        # Should handle empty results gracefully
        sensor_history_data = context['sensor_history_data']
        self.assertIsInstance(sensor_history_data, EntitySensorHistoryData)
        self.assertEqual(len(sensor_history_data.sensor_responses), 0)
        self.assertEqual(len(sensor_history_data.timeline_groups), 0)
        self.assertIsNone(sensor_history_data.current_sensor_response)
        
        # Pagination should reflect no data available
        pagination = sensor_history_data.pagination_metadata
        self.assertFalse(pagination.get('has_older_records', True))
        self.assertFalse(pagination.get('has_newer_records', True))

    def test_view_handles_large_dataset_pagination_boundaries(self):
        """Test performance boundary: pagination with large number of records."""
        # Clear existing data and create large dataset
        SensorHistory.objects.filter(sensor=self.video_sensor).delete()
        
        # Create 100+ sensor records to test pagination boundaries
        base_time = timezone.now()
        large_dataset = []
        for i in range(150):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'large_dataset_record_{i}',
                response_datetime=base_time - timezone.timedelta(minutes=i * 10),
                has_video_stream=True,
                details=f'{{"large_test": true, "index": {i}}}'
            )
            large_dataset.append(record)
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        # Test default pagination handles large dataset
        context = view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id
        )
        
        sensor_history_data = context['sensor_history_data']
        
        # Should limit results to reasonable window size (typically 50)
        self.assertLessEqual(len(sensor_history_data.sensor_responses), 50)
        self.assertGreater(len(sensor_history_data.sensor_responses), 0)
        
        # Should indicate more records available
        pagination = sensor_history_data.pagination_metadata
        self.assertTrue(pagination.get('has_older_records', False))
        
        # Timeline groups should be created efficiently
        self.assertIsInstance(sensor_history_data.timeline_groups, list)
        
    def test_view_handles_timeline_grouping_edge_cases(self):
        """Test performance boundary: timeline grouping with edge case date patterns."""
        # Clear existing data
        SensorHistory.objects.filter(sensor=self.video_sensor).delete()
        
        base_time = timezone.now()
        
        # Create edge case scenarios: 
        # 1. Many events at exact same timestamp
        same_timestamp = base_time - timezone.timedelta(hours=1)
        for i in range(5):
            SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'same_time_{i}',
                response_datetime=same_timestamp,
                has_video_stream=True,
                details=f'{{"same_timestamp_test": {i}}}'
            )
        
        # 2. Events spanning midnight boundary
        midnight_boundary = base_time.replace(hour=0, minute=1, second=0, microsecond=0)
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='after_midnight',
            response_datetime=midnight_boundary,
            has_video_stream=True
        )
        
        before_midnight = midnight_boundary - timezone.timedelta(minutes=2)
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='before_midnight',
            response_datetime=before_midnight,
            has_video_stream=True
        )
        
        view = EntityVideoSensorHistoryView()
        request = Mock()
        request.view_parameters = Mock()
        request.view_parameters.to_session = Mock()
        
        context = view.get_main_template_context(
            request,
            entity_id=self.video_entity.id,
            sensor_id=self.video_sensor.id
        )
        
        # Should handle edge cases without errors
        sensor_history_data = context['sensor_history_data']
        self.assertIsInstance(sensor_history_data.timeline_groups, list)
        self.assertGreater(len(sensor_history_data.sensor_responses), 0)
        
        # Timeline groups should handle midnight boundary correctly
        for group in sensor_history_data.timeline_groups:
            self.assertIn('label', group)
            self.assertIn('items', group)
            self.assertIsInstance(group['items'], list)
