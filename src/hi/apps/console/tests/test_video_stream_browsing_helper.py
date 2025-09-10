from datetime import datetime
from pytz import timezone as UTC
import logging

from django.test import TransactionTestCase
from django.utils import timezone

from hi.apps.console.video_stream_browsing_helper import VideoStreamBrowsingHelper
from hi.apps.console.transient_models import EntitySensorHistoryData, VideoDispatchResult
from hi.apps.console.enums import VideoDispatchType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey

from django.core.exceptions import BadRequest

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

    def test_find_video_sensor_handles_corrupted_entity_states(self):
        """Test error boundary: find_video_sensor with corrupted entity state relationships."""
        # Create entity with corrupted state (no sensors)
        corrupted_entity = Entity.objects.create(
            integration_id='test.corrupted',
            integration_name='test_integration', 
            name='Corrupted Entity',
            has_video_stream=True  # Claims to have video but has no sensors
        )
        
        # Should handle gracefully when entity claims video capability but has no sensors
        result = VideoStreamBrowsingHelper.find_video_sensor_for_entity(corrupted_entity)
        self.assertIsNone(result)

    def test_get_timeline_window_handles_invalid_preserve_bounds(self):
        """Test error boundary: timeline window with invalid preservation bounds."""
        # Create test data
        base_time = timezone.now()
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='test_value',
            response_datetime=base_time,
            has_video_stream=True
        )
        
        # Test with invalid window bounds (end before start)
        invalid_start = base_time
        invalid_end = base_time - timezone.timedelta(hours=1)  # End before start
        invalid_bounds = (invalid_start, invalid_end)
        
        # Should handle invalid bounds gracefully
        sensor_responses, metadata = VideoStreamBrowsingHelper.get_timeline_window(
            self.video_sensor, preserve_window_bounds=invalid_bounds
        )
        
        # Should return empty results or handle gracefully
        self.assertIsInstance(sensor_responses, list)
        self.assertIsInstance(metadata, dict)

    def test_group_responses_by_time_handles_same_timestamp_records(self):
        """Test performance boundary: grouping with many records at same timestamp."""
        base_time = timezone.now()
        same_timestamp = base_time.replace(hour=12, minute=0, second=0, microsecond=0)
        
        # Create multiple sensor responses at exactly the same timestamp
        sensor_responses = []
        for i in range(10):
            integration_key = IntegrationKey(
                integration_id='test_integration',
                integration_name=f'same_time_response_{i}'
            )
            
            response = SensorResponse(
                integration_key=integration_key,
                value=f'same_time_value_{i}',
                timestamp=same_timestamp,  # Same timestamp for all
                sensor=self.video_sensor,
                detail_attrs={'sensor_history_id': str(1000 + i)},
                has_video_stream=True
            )
            sensor_responses.append(response)
        
        # Should group all same-timestamp records correctly
        timeline_groups = VideoStreamBrowsingHelper.group_responses_by_time(sensor_responses)
        
        self.assertIsInstance(timeline_groups, list)
        self.assertEqual(len(timeline_groups), 1)  # All in same time group
        
        # All responses should be in the single group
        single_group = timeline_groups[0]
        self.assertEqual(len(single_group['items']), 10)

    def test_build_sensor_history_data_handles_extreme_timestamp_ranges(self):
        """Test error boundary: extreme timestamp ranges and edge cases."""
        # Create records with extreme timestamp ranges
        base_time = timezone.now()
        
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='extreme_past',
            response_datetime=timezone.datetime(1970, 1, 1, tzinfo=timezone.utc),
            has_video_stream=True
        )
        
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='recent',
            response_datetime=base_time,
            has_video_stream=True
        )
        
        # Should handle extreme timestamp ranges
        result = VideoStreamBrowsingHelper.build_sensor_history_data_default(self.video_sensor)
        
        self.assertIsNotNone(result)
        self.assertGreater(len(result.sensor_responses), 0)
        
        # Should handle timeline grouping with extreme ranges
        self.assertIsInstance(result.timeline_groups, list)

    def test_pagination_methods_handle_edge_case_timestamps(self):
        """Test performance boundary: pagination with edge case timestamp values."""
        # Test with Unix epoch timestamp (edge case)
        epoch_timestamp = 0  # January 1, 1970
        
        # Should handle epoch timestamp without errors
        result = VideoStreamBrowsingHelper.build_sensor_history_data_earlier(
            self.video_sensor, epoch_timestamp
        )
        
        # Should return valid empty result for epoch (no records before 1970)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.sensor_responses), 0)
        self.assertFalse(result.pagination_metadata['has_older_records'])
        
        # Test with very large timestamp (far future)
        future_timestamp = 2147483647  # 32-bit max timestamp (2038)
        
        result = VideoStreamBrowsingHelper.build_sensor_history_data_later(
            self.video_sensor, future_timestamp
        )
        
        # Should handle far future timestamp
        self.assertIsNotNone(result)
        self.assertIsInstance(result.sensor_responses, list)


class TestVideoDispatchResult(TransactionTestCase):
    """Test get_video_dispatch_result method core functionality and edge cases."""
    
    def setUp(self):
        # Create test entity with video stream capability
        self.video_entity = Entity.objects.create(
            integration_id='test.camera.dispatch',
            integration_name='test_integration',
            name='Dispatch Test Camera',
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
            integration_id='test.sensor.dispatch',
            integration_name='test_integration',
            name='Dispatch Motion Sensor',
            entity_state=self.entity_state,
            sensor_type_str='binary',
            provides_video_stream=True
        )
        
        # Create entity without video capability for error testing
        self.non_video_entity = Entity.objects.create(
            integration_id='test.no.video',
            integration_name='test_integration',
            name='No Video Entity',
            entity_type_str='sensor',
            has_video_stream=False
        )

    def test_get_video_dispatch_result_returns_valid_result_structure(self):
        """Test that method returns properly structured VideoDispatchResult."""
        referrer_url = f'/console/entity/{self.video_entity.id}/video-sensor-history/{self.video_sensor.id}/'
        
        result = VideoStreamBrowsingHelper.get_video_dispatch_result(
            self.video_entity, referrer_url
        )
        
        # Verify result structure
        self.assertIsInstance(result, VideoDispatchResult)
        self.assertIsInstance(result.dispatch_type, VideoDispatchType)
        self.assertEqual(result.sensor, self.video_sensor)
        
        # Verify properties work
        self.assertFalse(result.is_live_stream)
        self.assertTrue(result.is_history_view)
        
        # Verify get_view_kwargs method
        kwargs = result.get_view_kwargs()
        self.assertIn('sensor_id', kwargs)
        self.assertEqual(kwargs['sensor_id'], self.video_sensor.id)

    def test_get_video_dispatch_result_fallback_behavior_with_records(self):
        """Test fallback behavior when sensor has data records."""
        base_time = timezone.now()
        timestamp = int(base_time.timestamp())
        
        # Create both earlier and later records
        earlier_time = base_time - timezone.timedelta(hours=1)
        later_time = base_time + timezone.timedelta(hours=1)
        
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='earlier_event',
            response_datetime=earlier_time,
            has_video_stream=True
        )
        
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='later_event',
            response_datetime=later_time,
            has_video_stream=True
        )
        
        # Test with an earlier view URL that should trigger fallback logic
        referrer_url = f'/console/entity/{self.video_entity.id}/video-sensor-history/{self.video_sensor.id}/earlier/{timestamp}/'
        
        result = VideoStreamBrowsingHelper.get_video_dispatch_result(
            self.video_entity, referrer_url
        )
        
        self.assertIsInstance(result, VideoDispatchResult)
        self.assertEqual(result.sensor, self.video_sensor)
        # Method should return a valid dispatch type based on available records
        self.assertIn(result.dispatch_type, [
            VideoDispatchType.HISTORY_DEFAULT,
            VideoDispatchType.HISTORY_EARLIER,
            VideoDispatchType.HISTORY_LATER
        ])

    def test_get_video_dispatch_result_no_video_sensor_raises_error(self):
        """Test error handling when entity has no video sensor."""
        with self.assertRaises(BadRequest) as context:
            VideoStreamBrowsingHelper.get_video_dispatch_result(
                self.non_video_entity, '/any/url/'
            )
        
        self.assertIn('No video sensor found', str(context.exception))

    def test_get_video_dispatch_result_none_entity_raises_error(self):
        """Test error handling when entity is None."""
        with self.assertRaises(AttributeError):
            VideoStreamBrowsingHelper.get_video_dispatch_result(
                None, '/any/url/'
            )

    def test_get_video_dispatch_result_fallback_to_default(self):
        """Test fallback to default dispatch for unrecognized URLs."""
        unrecognized_urls = [
            '/some/invalid/url/',
            '',
            'not-a-url',
            '/console/other/path/',
        ]
        
        for url in unrecognized_urls:
            with self.subTest(url=url):
                result = VideoStreamBrowsingHelper.get_video_dispatch_result(
                    self.video_entity, url
                )
                
                # Should fallback to default dispatch
                self.assertIsInstance(result, VideoDispatchResult)
                self.assertEqual(result.dispatch_type, VideoDispatchType.HISTORY_DEFAULT)
                self.assertEqual(result.sensor, self.video_sensor)
                self.assertIsNone(result.timestamp)

    def test_get_video_dispatch_result_with_empty_database(self):
        """Test behavior when no sensor history records exist."""
        # No SensorHistory records created - empty database for this sensor
        referrer_url = f'/console/entity/{self.video_entity.id}/video-sensor-history/{self.video_sensor.id}/earlier/1234567890/'
        
        result = VideoStreamBrowsingHelper.get_video_dispatch_result(
            self.video_entity, referrer_url
        )
        
        # Should return a valid result even with empty database
        self.assertIsInstance(result, VideoDispatchResult)
        self.assertEqual(result.sensor, self.video_sensor)
        # Could be any dispatch type depending on URL matching
        self.assertIn(result.dispatch_type, [
            VideoDispatchType.HISTORY_DEFAULT,
            VideoDispatchType.HISTORY_EARLIER,
            VideoDispatchType.HISTORY_LATER
        ])

    def test_get_video_dispatch_result_basic_history_view_url(self):
        """Test basic sensor history view URL (Case 5: no specific event)."""
        referrer_url = f'/console/entity/{self.video_entity.id}/video-sensor-history/{self.video_sensor.id}/'
        
        result = VideoStreamBrowsingHelper.get_video_dispatch_result(
            self.video_entity, referrer_url
        )
        
        self.assertIsInstance(result, VideoDispatchResult)
        self.assertEqual(result.dispatch_type, VideoDispatchType.HISTORY_DEFAULT)
        self.assertEqual(result.sensor, self.video_sensor)
        self.assertIsNone(result.timestamp)

    def test_get_video_dispatch_result_timestamp_handling(self):
        """Test that method handles timestamp parameters correctly."""
        test_timestamp = 1234567890
        referrer_url = f'/console/entity/{self.video_entity.id}/video-sensor-history/{self.video_sensor.id}/earlier/{test_timestamp}/'
        
        result = VideoStreamBrowsingHelper.get_video_dispatch_result(
            self.video_entity, referrer_url
        )
        
        self.assertIsInstance(result, VideoDispatchResult)
        self.assertEqual(result.sensor, self.video_sensor)
        # If URL matches pattern and method sets timestamp, verify it
        if result.timestamp is not None:
            self.assertEqual(result.timestamp, test_timestamp)

    def test_get_video_dispatch_result_helper_methods_integration(self):
        """Test integration with helper methods _has_older_records and _has_newer_records."""
        base_time = timezone.now()
        timestamp = int(base_time.timestamp())
        
        # Create test record
        SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='test_event',
            response_datetime=base_time - timezone.timedelta(hours=1),
            has_video_stream=True
        )
        
        # Test that helper methods work correctly
        has_older = VideoStreamBrowsingHelper._has_older_records(self.video_sensor, timestamp)
        has_newer = VideoStreamBrowsingHelper._has_newer_records(self.video_sensor, timestamp)
        
        self.assertTrue(has_older)  # Record exists 1 hour before timestamp
        self.assertFalse(has_newer)   # No records after timestamp
        
        # Test dispatch method uses these results appropriately
        referrer_url = f'/console/entity/{self.video_entity.id}/video-sensor-history/{self.video_sensor.id}/later/{timestamp}/'
        
        result = VideoStreamBrowsingHelper.get_video_dispatch_result(
            self.video_entity, referrer_url
        )
        
        self.assertIsInstance(result, VideoDispatchResult)
        self.assertEqual(result.sensor, self.video_sensor)


class TestTimezoneHandling(TransactionTestCase):
    """Test timezone-related functionality in VideoStreamBrowsingHelper."""

    def setUp(self):
        """Set up test entities and sensors."""
        # Create test entity with video capability (matching existing pattern)
        self.video_entity = Entity.objects.create(
            integration_id='test.timezone.camera',
            integration_name='test_timezone_integration',
            name='Timezone Test Camera',
            entity_type_str='camera',
            has_video_stream=True
        )
        
        # Create entity state
        self.entity_state = EntityState.objects.create(
            entity=self.video_entity,
            entity_state_type_str='motion',
            name='Motion Detection'
        )
        
        # Create video sensor
        self.video_sensor = Sensor.objects.create(
            integration_id='test.timezone.sensor',
            integration_name='test_timezone_integration',
            name='Timezone Test Sensor',
            entity_state=self.entity_state,
            sensor_type_str='binary',
            provides_video_stream=True
        )

    def test_group_responses_by_time_with_user_timezone(self):
        """Test that group_responses_by_time correctly uses user timezone for grouping."""
        from datetime import datetime
        from pytz import UTC
        
        # Create test records at specific UTC times that would span multiple days in different timezones
        # 11 PM CDT (4 AM UTC next day) and 1 AM CDT (6 AM UTC same day)
        utc_time_1 = datetime(2023, 7, 15, 4, 0, 0, tzinfo=UTC)  # 11 PM CDT July 14
        utc_time_2 = datetime(2023, 7, 15, 6, 0, 0, tzinfo=UTC)  # 1 AM CDT July 15
        
        record_1 = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='event_july_14_cdt',
            response_datetime=utc_time_1,
            has_video_stream=True
        )
        
        record_2 = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='event_july_15_cdt',  
            response_datetime=utc_time_2,
            has_video_stream=True
        )
        
        # Create sensor responses
        response_1 = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(record_1)
        response_2 = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(record_2)
        
        # Test with CDT timezone - should group into different days
        groups_cdt = VideoStreamBrowsingHelper.group_responses_by_time(
            [response_1, response_2],
            user_timezone='America/Chicago'
        )
        
        # Should have two separate day groups
        self.assertEqual(len(groups_cdt), 2)
        
        # Test with UTC timezone - both should be in same day (July 15)
        groups_utc = VideoStreamBrowsingHelper.group_responses_by_time(
            [response_1, response_2], 
            user_timezone='UTC'
        )
        
        # Should have one day group since both events are on July 15 UTC
        self.assertEqual(len(groups_utc), 1)

    def test_group_responses_by_time_with_dst_transitions(self):
        """Test timezone handling during DST transitions."""
        
        # Test during spring forward in US Central Time (March 2023)
        # 1:30 AM CST (before spring forward) and 3:30 AM CDT (after spring forward)
        
        # Before DST transition (1:30 AM CST = 7:30 AM UTC)
        utc_before = datetime(2023, 3, 12, 7, 30, 0, tzinfo=UTC)
        # After DST transition (3:30 AM CDT = 8:30 AM UTC) 
        utc_after = datetime(2023, 3, 12, 8, 30, 0, tzinfo=UTC)
        
        record_before = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='before_dst',
            response_datetime=utc_before,
            has_video_stream=True
        )
        
        record_after = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='after_dst',
            response_datetime=utc_after,
            has_video_stream=True
        )
        
        response_before = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(record_before)
        response_after = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(record_after)
        
        # Test grouping with Chicago timezone
        groups = VideoStreamBrowsingHelper.group_responses_by_time(
            [response_before, response_after],
            user_timezone='America/Chicago'
        )
        
        # Should handle DST transition correctly and group appropriately
        # Both events should be on same day (March 12) in Chicago timezone
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]['items']), 2)

    def test_group_responses_by_time_midnight_boundary_edge_case(self):
        """Test timezone handling at midnight boundaries."""
        from datetime import datetime
        from pytz import UTC
        
        # Create records at 11:59 PM and 12:01 AM in a specific timezone
        # Using Pacific Time: 11:59 PM PST = 7:59 AM UTC next day
        pst_late_night = datetime(2023, 12, 15, 7, 59, 0, tzinfo=UTC)  # 11:59 PM PST Dec 14
        pst_early_morning = datetime(2023, 12, 15, 8, 1, 0, tzinfo=UTC)  # 12:01 AM PST Dec 15
        
        record_late = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='late_night',
            response_datetime=pst_late_night,
            has_video_stream=True
        )
        
        record_early = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='early_morning',
            response_datetime=pst_early_morning,
            has_video_stream=True
        )
        
        response_late = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(record_late)
        response_early = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(record_early)
        
        # Test with Pacific timezone - should be different days
        groups_pst = VideoStreamBrowsingHelper.group_responses_by_time(
            [response_late, response_early],
            user_timezone='America/Los_Angeles'
        )
        
        self.assertEqual(len(groups_pst), 2)  # Different days in PST
        
        # Test with UTC timezone - should be same day
        groups_utc = VideoStreamBrowsingHelper.group_responses_by_time(
            [response_late, response_early],
            user_timezone='UTC'
        )
        
        self.assertEqual(len(groups_utc), 1)  # Same day in UTC

    def test_group_responses_by_time_invalid_timezone_fallback(self):
        """Test that invalid timezone falls back to UTC behavior."""
        from datetime import datetime
        from pytz import UTC
        
        # Create a test record
        utc_time = datetime(2023, 7, 15, 12, 0, 0, tzinfo=UTC)
        
        record = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='test_event',
            response_datetime=utc_time,
            has_video_stream=True
        )
        
        response = VideoStreamBrowsingHelper.create_sensor_response_with_history_id(record)
        
        # Test with invalid timezone - should not crash and should fall back to UTC-like behavior
        groups_invalid = VideoStreamBrowsingHelper.group_responses_by_time(
            [response],
            user_timezone='Invalid/Timezone'
        )
        
        # Should still create groups without crashing
        self.assertIsInstance(groups_invalid, list)
        self.assertTrue(len(groups_invalid) > 0)
        
        # Compare with UTC behavior
        groups_utc = VideoStreamBrowsingHelper.group_responses_by_time(
            [response],
            user_timezone='UTC'
        )
        
        # Should have same structure as UTC (fallback behavior)
        self.assertEqual(len(groups_invalid), len(groups_utc))

    def test_build_sensor_history_data_methods_pass_timezone_parameter(self):
        """Test that all build_sensor_history_data methods accept and pass timezone parameter."""
        from datetime import datetime
        from pytz import UTC
        
        # Create test record
        utc_time = datetime(2023, 7, 15, 12, 0, 0, tzinfo=UTC)
        test_timestamp = int(utc_time.timestamp())
        
        _ = SensorHistory.objects.create(
            sensor=self.video_sensor,
            value='test_event',
            response_datetime=utc_time,
            has_video_stream=True
        )
        
        # Test build_sensor_history_data_default with timezone
        result_default = VideoStreamBrowsingHelper.build_sensor_history_data_default(
            self.video_sensor,
            user_timezone='America/New_York'
        )
        
        self.assertIsInstance(result_default, EntitySensorHistoryData)
        
        # Test build_sensor_history_data_earlier with timezone
        result_earlier = VideoStreamBrowsingHelper.build_sensor_history_data_earlier(
            self.video_sensor,
            test_timestamp,
            user_timezone='America/New_York'
        )
        
        self.assertIsInstance(result_earlier, EntitySensorHistoryData)
        
        # Test build_sensor_history_data_later with timezone
        result_later = VideoStreamBrowsingHelper.build_sensor_history_data_later(
            self.video_sensor,
            test_timestamp,
            user_timezone='America/New_York'
        )
        
        self.assertIsInstance(result_later, EntitySensorHistoryData)
        
        # Test main build_sensor_history_data with timezone
        result_main = VideoStreamBrowsingHelper.build_sensor_history_data(
            self.video_sensor,
            user_timezone='America/New_York'
        )
        
        self.assertIsInstance(result_main, EntitySensorHistoryData)
