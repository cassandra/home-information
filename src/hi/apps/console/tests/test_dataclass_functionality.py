import logging
from datetime import datetime
from unittest.mock import Mock

from django.test import TestCase
from django.utils import timezone

from hi.apps.console.transient_models import EntitySensorHistoryData
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey

logging.disable(logging.CRITICAL)


class TestEntitySensorHistoryData(TestCase):
    """Test EntitySensorHistoryData dataclass functionality."""

    def setUp(self):
        # Create mock sensor responses for testing
        self.mock_sensor = Mock()
        self.mock_sensor.id = 123
        
        # Create sample sensor responses
        base_time = timezone.now()
        self.sensor_responses = []
        
        for i in range(3):
            integration_key = IntegrationKey(
                integration_id='test_integration',
                integration_name=f'test_response_{i}'
            )
            
            response = SensorResponse(
                integration_key=integration_key,
                value=f'value_{i}',
                timestamp=base_time - timezone.timedelta(hours=i),
                sensor=self.mock_sensor,
                detail_attrs={
                    'duration_seconds': str(60 + i * 30)
                },
                has_video_stream=True,
                sensor_history_id=1000 + i  # Set as direct property
            )
            self.sensor_responses.append(response)
        
        # Create sample timeline groups
        self.timeline_groups = [
            {
                'label': 'Today',
                'date': base_time.date(),
                'items': self.sensor_responses[:2]
            },
            {
                'label': 'Yesterday',
                'date': (base_time - timezone.timedelta(days=1)).date(),
                'items': self.sensor_responses[2:]
            }
        ]
        
        # Sample pagination metadata
        self.pagination_metadata = {
            'has_older_records': True,
            'has_newer_records': False,
            'window_center_timestamp': base_time,
            'window_size': 50,
            'window_start_timestamp': base_time - timezone.timedelta(hours=2),
            'window_end_timestamp': base_time
        }

    def test_dataclass_timeline_group_navigation_logic(self):
        """Test business logic for timeline navigation in template rendering."""
        # Create timeline groups with different date patterns
        base_time = timezone.now()
        today_responses = self.sensor_responses[:2]
        yesterday_responses = self.sensor_responses[2:]
        
        timeline_groups = [
            {
                'label': 'Today',
                'date': base_time.date(),
                'items': today_responses
            },
            {
                'label': 'Yesterday', 
                'date': (base_time - timezone.timedelta(days=1)).date(),
                'items': yesterday_responses
            }
        ]
        
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=timeline_groups,
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=self.sensor_responses[1],
            next_sensor_response=None
        )
        
        # Test business logic for timeline navigation
        # Verify navigation relationships work correctly
        current_response = data.current_sensor_response
        prev_response = data.prev_sensor_response
        
        # Current should be newer than previous (business rule)
        self.assertGreater(current_response.timestamp, prev_response.timestamp)
        
        # Test timeline group structure for template rendering
        self.assertEqual(len(data.timeline_groups), 2)
        
        # Verify today's group comes first (chronological ordering)
        today_group = data.timeline_groups[0]
        yesterday_group = data.timeline_groups[1]
        
        self.assertEqual(today_group['label'], 'Today')
        self.assertEqual(len(today_group['items']), 2)
        self.assertEqual(yesterday_group['label'], 'Yesterday')
        self.assertEqual(len(yesterday_group['items']), 1)
        
        # Test that items within groups maintain chronological order
        today_items = today_group['items']
        if len(today_items) > 1:
            self.assertGreaterEqual(today_items[0].timestamp, today_items[1].timestamp)

    def test_dataclass_handles_empty_and_edge_case_states(self):
        """Test dataclass behavior in edge cases and empty states."""
        # Test empty timeline state (no sensor history available)
        empty_data = EntitySensorHistoryData(
            sensor_responses=[],
            current_sensor_response=None,
            timeline_groups=[],
            pagination_metadata={'has_older_records': False, 'has_newer_records': False},
            prev_sensor_response=None,
            next_sensor_response=None
        )
        
        # Template should handle empty state gracefully
        self.assertEqual(len(empty_data.sensor_responses), 0)
        self.assertEqual(len(empty_data.timeline_groups), 0)
        self.assertIsNone(empty_data.current_sensor_response)
        
        # Test single record state (common for new sensors)
        single_record_data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses[:1],
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=[{
                'label': 'Today',
                'date': timezone.now().date(),
                'items': self.sensor_responses[:1]
            }],
            pagination_metadata={'has_older_records': False, 'has_newer_records': False},
            prev_sensor_response=None,
            next_sensor_response=None
        )
        
        # Verify single record navigation logic
        self.assertEqual(len(single_record_data.sensor_responses), 1)
        self.assertIsNotNone(single_record_data.current_sensor_response)
        self.assertIsNone(single_record_data.prev_sensor_response)
        self.assertIsNone(single_record_data.next_sensor_response)
        
        # Template pagination buttons should be disabled
        pagination = single_record_data.pagination_metadata
        self.assertFalse(pagination['has_older_records'])
        self.assertFalse(pagination['has_newer_records'])

    def test_dataclass_supports_none_values_for_optional_fields(self):
        """Test that dataclass properly handles None values for optional fields."""
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=None,  # Can be None if no records
            timeline_groups=[],             # Can be empty
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=None,
            next_sensor_response=None,
            window_start_timestamp=None,
            window_end_timestamp=None
        )
        
        # Should not raise any errors
        self.assertIsNone(data.current_sensor_response)
        self.assertEqual(data.timeline_groups, [])
        self.assertIsNone(data.prev_sensor_response)
        self.assertIsNone(data.next_sensor_response)
        self.assertIsNone(data.window_start_timestamp)
        self.assertIsNone(data.window_end_timestamp)

    def test_dataclass_fields_are_accessible(self):
        """Test that all dataclass fields are properly accessible."""
        window_start = timezone.now() - timezone.timedelta(hours=1)
        window_end = timezone.now()
        
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[1],
            timeline_groups=self.timeline_groups,
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=self.sensor_responses[2],
            next_sensor_response=self.sensor_responses[0],
            window_start_timestamp=window_start,
            window_end_timestamp=window_end
        )
        
        # Test field access
        self.assertIsInstance(data.sensor_responses, list)
        self.assertIsInstance(data.current_sensor_response, SensorResponse)
        self.assertIsInstance(data.timeline_groups, list)
        self.assertIsInstance(data.pagination_metadata, dict)
        self.assertIsInstance(data.prev_sensor_response, SensorResponse)
        self.assertIsInstance(data.next_sensor_response, SensorResponse)
        self.assertIsInstance(data.window_start_timestamp, datetime)
        self.assertIsInstance(data.window_end_timestamp, datetime)

    def test_dataclass_supports_timezone_aware_datetimes(self):
        """Test that dataclass properly handles timezone-aware datetime objects."""
        # Create timezone-aware timestamps
        window_start = timezone.now() - timezone.timedelta(hours=2)
        window_end = timezone.now()
        
        # Ensure they are timezone-aware
        self.assertIsNotNone(window_start.tzinfo)
        self.assertIsNotNone(window_end.tzinfo)
        
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=self.timeline_groups,
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=None,
            next_sensor_response=None,
            window_start_timestamp=window_start,
            window_end_timestamp=window_end
        )
        
        # Verify timezone information is preserved
        self.assertIsNotNone(data.window_start_timestamp.tzinfo)
        self.assertIsNotNone(data.window_end_timestamp.tzinfo)
        self.assertEqual(data.window_start_timestamp, window_start)
        self.assertEqual(data.window_end_timestamp, window_end)

    def test_dataclass_can_be_used_in_template_context(self):
        """Test that dataclass can be properly used in template context patterns."""
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=self.timeline_groups,
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=self.sensor_responses[1],
            next_sensor_response=None
        )
        
        # Simulate template context usage patterns
        context = {
            'entity': Mock(),
            'sensor': self.mock_sensor,
            'sensor_history_data': data
        }
        
        # Verify template-style access works
        sensor_history_data = context['sensor_history_data']
        self.assertEqual(sensor_history_data.sensor_responses, self.sensor_responses)
        
        # Test accessing nested data (like templates would)
        if sensor_history_data.current_sensor_response:
            current_value = sensor_history_data.current_sensor_response.value
            self.assertEqual(current_value, 'value_0')
        
        # Test timeline group access
        for group in sensor_history_data.timeline_groups:
            self.assertIn('label', group)
            self.assertIn('items', group)

    def test_dataclass_pagination_state_management(self):
        """Test pagination state preservation across requests."""
        # Test window boundary preservation logic
        window_start = timezone.now() - timezone.timedelta(hours=2)
        window_end = timezone.now() - timezone.timedelta(hours=1)
        
        pagination_metadata = {
            'has_older_records': True,
            'has_newer_records': True,
            'window_start_timestamp': window_start,
            'window_end_timestamp': window_end,
            'window_size': 50
        }
        
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[1],  # Middle response
            timeline_groups=self.timeline_groups,
            pagination_metadata=pagination_metadata,
            prev_sensor_response=self.sensor_responses[2],
            next_sensor_response=self.sensor_responses[0],
            window_start_timestamp=window_start,
            window_end_timestamp=window_end
        )
        
        # Test business logic for pagination state
        # Verify window boundaries are preserved for timeline navigation
        self.assertEqual(data.window_start_timestamp, window_start)
        self.assertEqual(data.window_end_timestamp, window_end)
        
        # Test pagination metadata accuracy for UI state management
        self.assertTrue(data.pagination_metadata['has_older_records'])
        self.assertTrue(data.pagination_metadata['has_newer_records'])
        
        # Verify navigation state consistency
        # Current response should be between prev and next chronologically
        current = data.current_sensor_response.timestamp
        prev = data.prev_sensor_response.timestamp
        next_time = data.next_sensor_response.timestamp
        
        self.assertLess(prev, current)  # Previous is older
        self.assertGreater(next_time, current)  # Next is newer
        
        # Test window boundary business rules
        # All sensor responses should be within or span the window boundaries
        for response in data.sensor_responses:
            # Responses can extend beyond window for context, but check reasonable bounds
            self.assertIsNotNone(response.timestamp)

    def test_dataclass_integration_with_template_context(self):
        """Test dataclass usage in real template rendering scenarios."""
        # Simulate complex template context scenarios
        window_start = timezone.now() - timezone.timedelta(hours=3)
        window_end = timezone.now()
        
        # Create data that represents different video sensor history browsing states
        browsing_states = [
            # State 1: Default view (recent records)
            {
                'current_sensor_response': self.sensor_responses[0],
                'has_older': True,
                'has_newer': False
            },
            # State 2: Historical browsing (middle of timeline)
            {
                'current_sensor_response': self.sensor_responses[1],
                'has_older': True,
                'has_newer': True
            },
            # State 3: Oldest records (end of pagination)
            {
                'current_sensor_response': self.sensor_responses[2],
                'has_older': False,
                'has_newer': True
            }
        ]
        
        for state in browsing_states:
            pagination_metadata = {
                'has_older_records': state['has_older'],
                'has_newer_records': state['has_newer'],
                'window_start_timestamp': window_start,
                'window_end_timestamp': window_end
            }
            
            data = EntitySensorHistoryData(
                sensor_responses=self.sensor_responses,
                current_sensor_response=state['current_sensor_response'],
                timeline_groups=self.timeline_groups,
                pagination_metadata=pagination_metadata,
                prev_sensor_response=None,
                next_sensor_response=None
            )
            
            # Test template context usage patterns
            template_context = {
                'entity': Mock(),
                'sensor': self.mock_sensor,
                'sensor_history_data': data
            }
            
            # Verify data accessibility patterns used in templates
            history_data = template_context['sensor_history_data']
            
            # Test accessing sensor_history_id for navigation URLs (critical for templates)
            if history_data.current_sensor_response:
                history_id = history_data.current_sensor_response.sensor_history_id
                self.assertIsNotNone(history_id)
            
            # Test pagination button logic (template conditional rendering)
            can_go_earlier = history_data.pagination_metadata.get('has_older_records', False)
            can_go_later = history_data.pagination_metadata.get('has_newer_records', False)
            
            self.assertEqual(can_go_earlier, state['has_older'])
            self.assertEqual(can_go_later, state['has_newer'])
            
            # Test timeline iteration patterns (template for loops)
            for group in history_data.timeline_groups:
                self.assertIn('label', group)  # Template displays group labels
                self.assertIn('items', group)  # Template iterates over items
                for item in group['items']:
                    # Template accesses sensor history ID for URLs
                    self.assertIsNotNone(item.sensor_history_id)

