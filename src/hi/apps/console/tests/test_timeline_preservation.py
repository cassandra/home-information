import logging
from django.test import TransactionTestCase
from django.utils import timezone

from hi.apps.console.video_stream_browsing_helper import VideoStreamBrowsingHelper
from hi.apps.console.transient_models import EntitySensorHistoryData
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.tests.synthetic_data import SensorHistorySyntheticData

logging.disable(logging.CRITICAL)


class TestTimelinePreservationLogic(TransactionTestCase):
    """Test timeline preservation functionality with real database operations."""

    def setUp(self):
        # Create test entity and sensor
        self.video_entity = Entity.objects.create(
            integration_id='test.camera.timeline',
            integration_name='test_integration',
            name='Timeline Test Camera',
            entity_type_str='camera',
            has_video_stream=True
        )
        
        self.entity_state = EntityState.objects.create(
            entity=self.video_entity,
            entity_state_type_str='motion',
            name='Motion Detection'
        )
        
        self.video_sensor = Sensor.objects.create(
            integration_id='test.sensor.timeline',
            integration_name='test_integration',
            name='Timeline Test Sensor',
            entity_state=self.entity_state,
            sensor_type_str='binary',
            provides_video_stream=True
        )

    def test_timeline_preserved_when_target_record_within_window(self):
        """Test that timeline is preserved when target record falls within preserve window."""
        # Create comprehensive test data
        records, window_start, window_end = SensorHistorySyntheticData.create_timeline_preservation_test_data(
            self.video_sensor
        )
        
        # Select target record that falls within the window (4 hours ago)
        target_record = records[4]  # Should be within window (2-6 hours ago)
        
        # Build sensor history data with preservation
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            sensor=self.video_sensor,
            sensor_history_id=target_record.id,
            preserve_window_start=window_start,
            preserve_window_end=window_end
        )
        
        # Verify timeline preservation behavior
        self.assertIsInstance(result, EntitySensorHistoryData)
        
        # Should preserve the window timestamps
        self.assertEqual(result.window_start_timestamp, window_start)
        self.assertEqual(result.window_end_timestamp, window_end)
        
        # Current response should be the target record
        self.assertEqual(
            result.current_sensor_response.sensor_history_id,
            target_record.id
        )
        
        # Should include only records within the preserve window (records 2-6)
        sensor_response_ids = [
            r.sensor_history_id for r in result.sensor_responses
        ]
        
        # Records 2, 3, 4, 5, 6 should be included (within 2-6 hours ago)
        expected_records = [records[i] for i in range(2, 7)]
        for expected_record in expected_records:
            self.assertIn(expected_record.id, sensor_response_ids)
        
        # Records 0, 1 (too recent) and 7, 8, 9 (too old) should not be included
        excluded_records = [records[i] for i in [0, 1, 7, 8, 9]]
        for excluded_record in excluded_records:
            self.assertNotIn(excluded_record.id, sensor_response_ids)

    def test_timeline_recenters_when_target_record_outside_window(self):
        """Test that timeline re-centers when target record falls outside preserve window."""
        # Create boundary test scenario
        all_records, record_inside, record_outside, window_start, window_end = \
            SensorHistorySyntheticData.create_window_boundary_test_scenario(self.video_sensor)
        
        # Use record outside window as target
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            sensor=self.video_sensor,
            sensor_history_id=record_outside.id,
            preserve_window_start=window_start,
            preserve_window_end=window_end
        )
        
        # Should re-center around the target record instead of preserving window
        self.assertIsInstance(result, EntitySensorHistoryData)
        
        # Current response should be the outside record
        self.assertEqual(
            result.current_sensor_response.sensor_history_id,
            record_outside.id
        )
        
        # Window boundaries should be recalculated based on actual returned records
        self.assertIsNotNone(result.window_start_timestamp)
        self.assertIsNotNone(result.window_end_timestamp)
        
        # Should not use the preserve window boundaries
        self.assertNotEqual(result.window_start_timestamp, window_start)
        self.assertNotEqual(result.window_end_timestamp, window_end)
        
        # Should include the target record in results
        sensor_response_ids = [
            r.sensor_history_id for r in result.sensor_responses
        ]
        self.assertIn(record_outside.id, sensor_response_ids)

    def test_pagination_metadata_reflects_preserve_window_boundaries(self):
        """Test that pagination metadata correctly reflects preserve window boundaries."""
        # Create test data with many records
        records, middle_index = SensorHistorySyntheticData.create_pagination_test_data(
            self.video_sensor, total_records=15, window_size=5
        )
        
        # Define preserve window that includes middle records (indices 5-10)
        base_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        window_start = base_time - timezone.timedelta(hours=10)
        window_end = base_time - timezone.timedelta(hours=5)
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            sensor=self.video_sensor,
            sensor_history_id=records[7].id,  # Target within window
            preserve_window_start=window_start,
            preserve_window_end=window_end
        )
        
        # Verify pagination metadata indicates records exist outside window
        self.assertTrue(result.pagination_metadata['has_newer_records'])  # Records 0-4 exist
        self.assertTrue(result.pagination_metadata['has_older_records'])   # Records 11-14 exist
        
        # Verify window boundaries match preserve window
        self.assertEqual(
            result.pagination_metadata['window_start_timestamp'], 
            window_start
        )
        self.assertEqual(
            result.pagination_metadata['window_end_timestamp'], 
            window_end
        )

    def test_timeline_groups_use_preserved_records_only(self):
        """Test that timeline groups are created only from preserved records."""
        # Create test data spanning multiple days but preserve only recent records
        base_time = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        
        # Create records: today (0), yesterday (-1 day), and older (-3 days)
        today_records = []
        for hour in [8, 10, 14, 16]:
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value='active',
                response_datetime=base_time.replace(hour=hour),
                has_video_stream=True,
                details='{"day": "today"}'
            )
            today_records.append(record)
        
        # Yesterday records
        yesterday = base_time - timezone.timedelta(days=1)
        yesterday_record = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='active',
            response_datetime=yesterday,
            has_video_stream=True,
            details='{"day": "yesterday"}'
        )
        
        # Older records
        old_time = base_time - timezone.timedelta(days=3)
        old_record = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='active',
            response_datetime=old_time,
            has_video_stream=True,
            details='{"day": "old"}'
        )
        
        # Preserve window that includes only today's records
        window_start = base_time.replace(hour=6)   # Start of today
        window_end = base_time.replace(hour=18)    # End of today
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            sensor=self.video_sensor,
            sensor_history_id=today_records[0].id,
            preserve_window_start=window_start,
            preserve_window_end=window_end
        )
        
        # Timeline groups should only include today's records
        all_response_values = []
        for group in result.timeline_groups:
            for item in group['items']:
                all_response_values.append(item.value)
        
        # Should have 4 responses from today, none from yesterday or older
        self.assertEqual(len(all_response_values), 4)
        
        # Verify that only today's records are represented
        response_ids = [
            r.sensor_history_id for r in result.sensor_responses
        ]
        for today_record in today_records:
            self.assertIn(today_record.id, response_ids)
        
        # Yesterday and old records should not be included
        self.assertNotIn(yesterday_record.id, response_ids)
        self.assertNotIn(old_record.id, response_ids)

    def test_adjacent_records_navigation_respects_database_ordering(self):
        """Test that prev/next navigation uses actual database timestamp ordering."""
        # Create records with specific timestamps for navigation testing
        base_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        
        # Create 5 records at 1-hour intervals
        records = []
        for i in range(5):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'nav_test_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True,
                details=f'{{"nav_order": "{i}"}}'
            )
            records.append(record)
        
        # Test navigation from middle record (index 2)
        middle_record = records[2]  # 2 hours ago
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            sensor=self.video_sensor,
            sensor_history_id=middle_record.id
        )
        
        # Previous should be older record (records[3] - 3 hours ago)
        self.assertIsNotNone(result.prev_sensor_response)
        self.assertEqual(result.prev_sensor_response.value, 'nav_test_3')
        
        # Next should be newer record (records[1] - 1 hour ago)  
        self.assertIsNotNone(result.next_sensor_response)
        self.assertEqual(result.next_sensor_response.value, 'nav_test_1')

    def test_timezone_awareness_in_window_comparisons(self):
        """Test that all datetime comparisons are timezone-aware."""
        # Create timezone-aware sensor responses
        base_time = timezone.now()
        responses = SensorHistorySyntheticData.create_timezone_aware_sensor_responses(
            self.video_sensor,
            num_responses=3,
            start_time=base_time
        )
        
        # Create corresponding SensorHistory records
        records = []
        for i, response in enumerate(responses):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=response.value,
                response_datetime=response.timestamp,
                has_video_stream=True,
                details='{"timezone": "aware"}'
            )
            records.append(record)
        
        # Create timezone-aware preserve window
        window_start = base_time - timezone.timedelta(hours=2)
        window_end = base_time - timezone.timedelta(hours=1)
        
        # Ensure all timestamps are timezone-aware
        self.assertIsNotNone(window_start.tzinfo)
        self.assertIsNotNone(window_end.tzinfo)
        for record in records:
            self.assertIsNotNone(record.response_datetime.tzinfo)
        
        # This should not raise any timezone comparison errors
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            sensor=self.video_sensor,
            sensor_history_id=records[1].id,  # Middle record
            preserve_window_start=window_start,
            preserve_window_end=window_end
        )
        
        # Verify result is successful and timestamps are timezone-aware
        self.assertIsInstance(result, EntitySensorHistoryData)
        self.assertIsNotNone(result.window_start_timestamp.tzinfo)
        self.assertIsNotNone(result.window_end_timestamp.tzinfo)

    def test_empty_sensor_history_handled_gracefully(self):
        """Test that empty sensor history is handled gracefully."""
        # Don't create any SensorHistory records
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            sensor=self.video_sensor
        )
        
        # Should return valid dataclass with empty/None values
        self.assertIsInstance(result, EntitySensorHistoryData)
        self.assertEqual(len(result.sensor_responses), 0)
        self.assertIsNone(result.current_sensor_response)
        self.assertEqual(len(result.timeline_groups), 0)
        self.assertIsNone(result.prev_sensor_response)
        self.assertIsNone(result.next_sensor_response)
