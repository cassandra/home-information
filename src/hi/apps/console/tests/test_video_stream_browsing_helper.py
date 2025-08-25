import logging

from django.test import TransactionTestCase
from django.utils import timezone

from hi.apps.console.video_stream_browsing_helper import VideoStreamBrowsingHelper
from hi.apps.console.transient_models import EntitySensorHistoryData
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey

logging.disable(logging.CRITICAL)


class TestVideoStreamBrowsingHelper(TransactionTestCase):
    """Test VideoStreamBrowsingHelper for timeline preservation and business logic."""

    def setUp(self):
        # Create test entity with video stream capability
        self.video_entity = Entity.objects.create(
            integration_id='test.camera.security',
            integration_name='test_integration',
            name='Security Camera',
            entity_type_str='camera',
            has_video_stream=True
        )
        
        # Create entity state
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
        
        # Create another entity without video capability for find_video_sensor tests
        self.non_video_entity = Entity.objects.create(
            integration_id='test.sensor.temp',
            integration_name='test_integration',
            name='Temperature Sensor',
            entity_type_str='sensor',
            has_video_stream=False
        )

    def test_find_video_sensor_for_entity_returns_none_for_non_video_entity(self):
        """Test that find_video_sensor returns None for entity without video capability."""
        result = VideoStreamBrowsingHelper.find_video_sensor_for_entity(self.non_video_entity)
        self.assertIsNone(result)

    def test_find_video_sensor_for_entity_returns_none_for_none_entity(self):
        """Test that find_video_sensor returns None for None entity."""
        result = VideoStreamBrowsingHelper.find_video_sensor_for_entity(None)
        self.assertIsNone(result)

    def test_find_video_sensor_for_entity_returns_video_sensor(self):
        """Test that find_video_sensor returns correct video sensor for video entity."""
        result = VideoStreamBrowsingHelper.find_video_sensor_for_entity(self.video_entity)
        self.assertEqual(result, self.video_sensor)

    def test_create_sensor_response_with_history_id_adds_history_id_to_detail_attrs(self):
        """Test that sensor response has history ID added to detail_attrs."""
        sensor_history = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='active',
            response_datetime=timezone.now(),
            has_video_stream=True,
            details='{"original": "data"}'
        )
        
        sensor_response = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(sensor_history)
        
        self.assertIsInstance(sensor_response, SensorResponse)
        self.assertEqual(sensor_response.sensor, self.video_sensor)
        self.assertEqual(sensor_response.value, 'active')
        self.assertIsNotNone(sensor_response.sensor_history_id)
        self.assertEqual(sensor_response.sensor_history_id, sensor_history.id)

    def test_create_sensor_response_with_history_id_preserves_existing_detail_attrs(self):
        """Test that existing detail_attrs are preserved when adding history ID."""
        sensor_history = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='active',
            response_datetime=timezone.now(),
            has_video_stream=True,
            details='{"existing": "value", "duration": "120"}'
        )
        
        sensor_response = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(sensor_history)
        
        # Verify existing attributes are preserved
        self.assertEqual(sensor_response.detail_attrs['existing'], 'value')
        self.assertEqual(sensor_response.detail_attrs['duration'], '120')
        # Verify sensor_history_id is set as property, not in detail_attrs
        self.assertEqual(sensor_response.sensor_history_id, sensor_history.id)
        self.assertNotIn('sensor_history_id', sensor_response.detail_attrs)

    def test_get_timeline_window_returns_recent_records_when_no_center(self):
        """Test that get_timeline_window returns most recent records when no center provided."""
        # Create test records
        base_time = timezone.now()
        records = []
        for i in range(3):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
            records.append(record)
        
        sensor_responses, pagination_metadata = VideoStreamBrowsingHelper.get_timeline_window(
            self.video_sensor, None, window_size=5
        )
        
        # Should return all records, most recent first
        self.assertEqual(len(sensor_responses), 3)
        self.assertEqual(sensor_responses[0].value, 'value_0')  # Most recent
        self.assertEqual(sensor_responses[2].value, 'value_2')  # Oldest
        
        # Verify pagination metadata
        self.assertFalse(pagination_metadata['has_newer_records'])
        self.assertFalse(pagination_metadata['has_older_records'])  # Only 3 records, window is 5

    def test_get_timeline_window_with_preserve_bounds_queries_within_range(self):
        """Test that get_timeline_window respects preserve_window_bounds."""
        # Create records spanning 6 hours
        base_time = timezone.now()
        records = []
        for i in range(6):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
            records.append(record)
        
        # Set preserve bounds to include middle records
        # Records: 0 (0h), 1 (-1h), 2 (-2h), 3 (-3h), 4 (-4h), 5 (-5h)
        # Window: -3h to -1h inclusive should include records 1, 2, 3
        window_start = base_time - timezone.timedelta(hours=3)
        window_end = base_time - timezone.timedelta(hours=1)
        preserve_bounds = (window_start, window_end)
        
        sensor_responses, pagination_metadata = VideoStreamBrowsingHelper.get_timeline_window(
            self.video_sensor, None, window_size=50, preserve_window_bounds=preserve_bounds
        )
        
        # Should return records within the preserve window (records 1, 2, and 3)
        self.assertEqual(len(sensor_responses), 3)
        self.assertEqual(sensor_responses[0].value, 'value_1')  # Most recent within range
        self.assertEqual(sensor_responses[1].value, 'value_2')  # Middle within range
        self.assertEqual(sensor_responses[2].value, 'value_3')  # Oldest within range
        
        # Verify pagination metadata indicates more records exist
        self.assertTrue(pagination_metadata['has_newer_records'])
        self.assertTrue(pagination_metadata['has_older_records'])

    def test_get_timeline_window_centered_around_record(self):
        """Test that get_timeline_window centers correctly around specific record."""
        # Create 5 records
        base_time = timezone.now()
        records = []
        for i in range(5):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
            records.append(record)
        
        # Center around middle record (index 2)
        center_record = records[2]
        
        sensor_responses, pagination_metadata = VideoStreamBrowsingHelper.get_timeline_window(
            self.video_sensor, center_record, window_size=5
        )
        
        # Should return all 5 records with center record included
        self.assertEqual(len(sensor_responses), 5)
        
        # Find center record in results
        center_in_results = next(
            r for r in sensor_responses 
            if r.sensor_history_id == center_record.id
        )
        self.assertEqual(center_in_results.value, 'value_2')

    def test_group_responses_by_time_creates_daily_groups(self):
        """Test that group_responses_by_time creates appropriate daily groups."""
        # Create sensor responses spanning multiple days
        base_time = timezone.now()
        sensor_responses = []
        
        # Create a few responses for today, yesterday, and older
        for days_ago in [0, 1, 3]:
            for hour_offset in [8, 14]:
                if days_ago == 0:
                    # For today, use a fixed time to ensure it's always today
                    # regardless of when the test runs
                    timestamp = base_time.replace(hour=hour_offset, minute=0, second=0, microsecond=0)
                else:
                    # For other days, subtract full days then set specific hour
                    date_base = base_time - timezone.timedelta(days=days_ago)
                    timestamp = date_base.replace(hour=hour_offset, minute=0, second=0, microsecond=0)
                    
                integration_key = IntegrationKey(
                    integration_id='test',
                    integration_name=f'response_{days_ago}_{hour_offset}'
                )
                response = SensorResponse(
                    integration_key=integration_key,
                    value='active',
                    timestamp=timestamp,
                    sensor=self.video_sensor,
                    detail_attrs={'duration_seconds': '120', 'details': f'Motion event {days_ago}_{hour_offset}'},
                    has_video_stream=True,
                    sensor_history_id=int(f'{days_ago}{hour_offset}')  # Use unique ID for test
                )
                sensor_responses.append(response)
        
        timeline_groups = VideoStreamBrowsingHelper.group_responses_by_time(sensor_responses)
        
        # Should create groups for Today, Yesterday, and older date
        self.assertEqual(len(timeline_groups), 3)
        
        # Verify group labels (now include day abbreviations)
        group_labels = [group['label'] for group in timeline_groups]
        
        # Check that Today and Yesterday labels contain the expected base text
        today_label = next((label for label in group_labels if label.startswith('Today')), None)
        yesterday_label = next((label for label in group_labels if label.startswith('Yesterday')), None)
        
        self.assertIsNotNone(today_label, f"Expected a label starting with 'Today', got: {group_labels}")
        self.assertIsNotNone(yesterday_label, f"Expected a label starting with 'Yesterday', got: {group_labels}")
        
        # Verify the day abbreviation is included (3 characters for day)
        self.assertTrue(today_label.split()[-1], "Today label should include day abbreviation")
        self.assertTrue(yesterday_label.split()[-1], "Yesterday label should include day abbreviation")

    def test_group_responses_by_time_uses_hourly_grouping_for_busy_day(self):
        """Test that group_responses_by_time uses hourly grouping when many events today."""
        # Create 15 responses for today to trigger hourly grouping (> 10)
        base_time = timezone.now()
        sensor_responses = []
        
        for hour in range(15):
            timestamp = base_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            integration_key = IntegrationKey(
                integration_id='test',
                integration_name=f'response_{hour}'
            )
            response = SensorResponse(
                integration_key=integration_key,
                value='active',
                timestamp=timestamp,
                sensor=self.video_sensor,
                detail_attrs={'duration_seconds': '90', 'details': f'Motion event hour {hour}'},
                has_video_stream=True,
                sensor_history_id=hour
            )
            sensor_responses.append(response)
        
        timeline_groups = VideoStreamBrowsingHelper.group_responses_by_time(sensor_responses)
        
        # Should create hourly groups (15 different hours)
        self.assertEqual(len(timeline_groups), 15)
        
        # Verify some groups have hourly labels (AM/PM format)
        group_labels = [group['label'] for group in timeline_groups]
        self.assertTrue(any('AM' in label or 'PM' in label for label in group_labels))

    def test_find_adjacent_records_returns_correct_navigation(self):
        """Test that find_adjacent_records returns correct prev/next records."""
        # Create 3 sequential records
        base_time = timezone.now()
        records = []
        for i in range(3):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
            records.append(record)
        
        # Test navigation for middle record
        middle_record = records[1]
        prev_response, next_response = VideoStreamBrowsingHelper.find_adjacent_records(
            self.video_sensor, middle_record.id
        )
        
        # Previous should be the older record (records[2])
        self.assertIsNotNone(prev_response)
        self.assertEqual(prev_response.value, 'value_2')
        
        # Next should be the newer record (records[0])
        self.assertIsNotNone(next_response)
        self.assertEqual(next_response.value, 'value_0')

    def test_find_adjacent_records_handles_boundary_conditions(self):
        """Test that find_adjacent_records handles first/last records correctly."""
        # Create 2 records
        base_time = timezone.now()
        records = []
        for i in range(2):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
            records.append(record)
        
        # Test first (newest) record - should only have previous
        newest_record = records[0]
        prev_response, next_response = VideoStreamBrowsingHelper.find_adjacent_records(
            self.video_sensor, newest_record.id
        )
        
        self.assertIsNotNone(prev_response)
        self.assertEqual(prev_response.value, 'value_1')
        self.assertIsNone(next_response)  # No newer records
        
        # Test last (oldest) record - should only have next
        oldest_record = records[1]
        prev_response, next_response = VideoStreamBrowsingHelper.find_adjacent_records(
            self.video_sensor, oldest_record.id
        )
        
        self.assertIsNone(prev_response)  # No older records
        self.assertIsNotNone(next_response)
        self.assertEqual(next_response.value, 'value_0')

    def test_build_sensor_history_data_returns_correct_dataclass_structure(self):
        """Test that build_sensor_history_data returns properly structured dataclass."""
        # Create test records
        base_time = timezone.now()
        for i in range(3):
            SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data(self.video_sensor)
        
        # Verify result is correct dataclass type
        self.assertIsInstance(result, EntitySensorHistoryData)
        
        # Verify all required fields are present
        self.assertIsNotNone(result.sensor_responses)
        self.assertIsNotNone(result.current_sensor_response)
        self.assertIsNotNone(result.timeline_groups)
        self.assertIsNotNone(result.pagination_metadata)
        # prev/next may be None depending on data
        
        # Verify window timestamps are populated
        self.assertIsNotNone(result.window_start_timestamp)
        self.assertIsNotNone(result.window_end_timestamp)

    def test_build_sensor_history_data_timeline_preservation_logic(self):
        """Test timeline preservation logic in build_sensor_history_data."""
        # Create test records spanning 4 hours
        base_time = timezone.now()
        records = []
        for i in range(4):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
            records.append(record)
        
        # Test with preserve window that includes middle record
        target_record = records[2]  # 2 hours ago
        window_start = base_time - timezone.timedelta(hours=3)
        window_end = base_time - timezone.timedelta(hours=1)
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            self.video_sensor,
            sensor_history_id=target_record.id,
            preserve_window_start=window_start,
            preserve_window_end=window_end
        )
        
        # Should use preserved timeline since target record is within window
        self.assertIsInstance(result, EntitySensorHistoryData)
        
        # Current response should be the target record
        self.assertEqual(
            result.current_sensor_response.sensor_history_id,
            target_record.id
        )
        
        # Should include records within preserve window
        response_values = [r.value for r in result.sensor_responses]
        self.assertIn('value_1', response_values)  # Within window
        self.assertIn('value_2', response_values)  # Target record

    def test_build_sensor_history_data_recenters_when_record_outside_window(self):
        """Test that build_sensor_history_data re-centers when target record outside preserve window."""
        # Create test records spanning 6 hours
        base_time = timezone.now()
        records = []
        for i in range(6):
            record = SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
            records.append(record)
        
        # Test with preserve window that excludes target record
        target_record = records[5]  # 5 hours ago
        window_start = base_time - timezone.timedelta(hours=2)
        window_end = base_time - timezone.timedelta(hours=1)
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            self.video_sensor,
            sensor_history_id=target_record.id,
            preserve_window_start=window_start,
            preserve_window_end=window_end
        )
        
        # Should re-center around target record since it's outside preserve window
        self.assertIsInstance(result, EntitySensorHistoryData)
        
        # Current response should be the target record
        self.assertEqual(
            result.current_sensor_response.sensor_history_id,
            target_record.id
        )
        
        # Should include records around the target (centered timeline)
        response_values = [r.value for r in result.sensor_responses]
        self.assertIn('value_5', response_values)  # Target record should be included

    def test_build_sensor_history_data_handles_nonexistent_sensor_history_id(self):
        """Test that build_sensor_history_data handles nonexistent sensor_history_id gracefully."""
        # Create test records
        base_time = timezone.now()
        for i in range(2):
            SensorHistory.objects.create(
                sensor=self.video_sensor,
                value=f'value_{i}',
                response_datetime=base_time - timezone.timedelta(hours=i),
                has_video_stream=True
            )
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data(
            self.video_sensor,
            sensor_history_id=99999  # Nonexistent ID
        )
        
        # Should fall back to most recent window
        self.assertIsInstance(result, EntitySensorHistoryData)
        self.assertIsNotNone(result.sensor_responses)
        self.assertIsNotNone(result.current_sensor_response)
        
        # Should select most recent record as current
        self.assertEqual(result.current_sensor_response.value, 'value_0')
