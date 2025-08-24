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
                    'sensor_history_id': str(1000 + i),
                    'duration_seconds': str(60 + i * 30)
                },
                has_video_stream=True
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

    def test_dataclass_creation_with_all_fields(self):
        """Test that EntitySensorHistoryData can be created with all fields."""
        window_start = timezone.now() - timezone.timedelta(hours=2)
        window_end = timezone.now()
        
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=self.timeline_groups,
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=self.sensor_responses[1],
            next_sensor_response=None,
            window_start_timestamp=window_start,
            window_end_timestamp=window_end
        )
        
        # Verify all fields are set correctly
        self.assertEqual(data.sensor_responses, self.sensor_responses)
        self.assertEqual(data.current_sensor_response, self.sensor_responses[0])
        self.assertEqual(data.timeline_groups, self.timeline_groups)
        self.assertEqual(data.pagination_metadata, self.pagination_metadata)
        self.assertEqual(data.prev_sensor_response, self.sensor_responses[1])
        self.assertIsNone(data.next_sensor_response)
        self.assertEqual(data.window_start_timestamp, window_start)
        self.assertEqual(data.window_end_timestamp, window_end)

    def test_dataclass_creation_with_minimal_fields(self):
        """Test that EntitySensorHistoryData can be created with only required fields."""
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=self.timeline_groups,
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=None,
            next_sensor_response=None
        )
        
        # Verify required fields are set
        self.assertEqual(data.sensor_responses, self.sensor_responses)
        self.assertEqual(data.current_sensor_response, self.sensor_responses[0])
        self.assertEqual(data.timeline_groups, self.timeline_groups)
        self.assertEqual(data.pagination_metadata, self.pagination_metadata)
        
        # Verify optional fields have default values
        self.assertIsNone(data.prev_sensor_response)
        self.assertIsNone(data.next_sensor_response)
        self.assertIsNone(data.window_start_timestamp)
        self.assertIsNone(data.window_end_timestamp)

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

    def test_dataclass_equality_comparison(self):
        """Test that dataclass instances can be compared for equality."""
        window_start = timezone.now() - timezone.timedelta(hours=1)
        window_end = timezone.now()
        
        data1 = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=self.timeline_groups,
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=None,
            next_sensor_response=None,
            window_start_timestamp=window_start,
            window_end_timestamp=window_end
        )
        
        data2 = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses,
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=self.timeline_groups,
            pagination_metadata=self.pagination_metadata,
            prev_sensor_response=None,
            next_sensor_response=None,
            window_start_timestamp=window_start,
            window_end_timestamp=window_end
        )
        
        # Dataclass instances with same data should be equal
        self.assertEqual(data1, data2)
        
        # Different data should not be equal
        data3 = EntitySensorHistoryData(
            sensor_responses=[],  # Different data
            current_sensor_response=None,
            timeline_groups=[],
            pagination_metadata={},
            prev_sensor_response=None,
            next_sensor_response=None
        )
        
        self.assertNotEqual(data1, data3)

    def test_dataclass_repr_string_representation(self):
        """Test that dataclass has useful string representation."""
        data = EntitySensorHistoryData(
            sensor_responses=self.sensor_responses[:1],  # Just one for simpler output
            current_sensor_response=self.sensor_responses[0],
            timeline_groups=[],
            pagination_metadata={'test': 'metadata'},
            prev_sensor_response=None,
            next_sensor_response=None
        )
        
        repr_str = repr(data)
        
        # Should contain class name and key information
        self.assertIn('EntitySensorHistoryData', repr_str)
        self.assertIn('sensor_responses', repr_str)
        self.assertIn('current_sensor_response', repr_str)

