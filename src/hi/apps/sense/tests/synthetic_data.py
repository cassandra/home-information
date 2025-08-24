"""
Synthetic data generators for testing sensor-related functionality.
These generators create mock/synthetic data that can be reused across
tests and development scenarios.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.utils import timezone

from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey


class SensorHistorySyntheticData:
    """Generate synthetic sensor response data for testing and development."""
    
    @staticmethod
    def create_mock_sensor_responses(
        sensor: Sensor,
        num_items: int = 15,
        days_span: int = 3,
        current_id: Optional[int] = None
    ) -> List[SensorResponse]:
        """
        Create mock sensor response data for demonstration and testing.
        
        Args:
            sensor: The sensor to create responses for
            num_items: Number of response items to create
            days_span: Number of days to span the responses over
            current_id: Optional ID to include in the generated items
            
        Returns:
            List of SensorResponse objects
        """
        now = datetime.now()
        mock_responses = []
        
        for i in range(num_items):
            # Create timestamps with varying intervals to simulate realistic data
            if i < 5:
                # Recent items within last few hours
                timestamp = now - timedelta(hours=i * 2, minutes=i * 15)
            elif i < 10:
                # Yesterday's items
                timestamp = now - timedelta(days=1, hours=i - 5, minutes=i * 10)
            else:
                # Older items distributed over remaining days
                days_offset = 2 + (i - 10) * (days_span - 2) / max(1, num_items - 10)
                timestamp = now - timedelta(days=days_offset, hours=(i - 10) * 3)
            
            # Simulate different activity patterns
            is_active = i % 3 == 0  # Every third item is "active"
            
            # Create mock integration key
            integration_key = IntegrationKey(
                integration_id='mock_integration',
                integration_name=f'sensor_{sensor.id}_response_{i}'
            )
            
            # Create additional attributes for detail_attrs
            mock_sensor_history_id = 1000 + i  # Mock SensorHistory ID for testing
            detail_attrs = {
                'sensor_history_id': str(mock_sensor_history_id),  # Mock SensorHistory ID
                'duration_seconds': str(60 + (i * 15)),  # Varying durations
                'details': f'Motion detected in {sensor.entity_state.entity.name}' if is_active else 'No activity',
            }
            
            sensor_response = SensorResponse(
                integration_key=integration_key,
                value='active' if is_active else 'idle',
                timestamp=timestamp,
                sensor=sensor,
                detail_attrs=detail_attrs,
                source_image_url=f'/static/mock/video_{i}.mp4' if is_active else None,
                has_video_stream=True,
            )
            
            mock_responses.append(sensor_response)
        
        return mock_responses
    
    @staticmethod
    def create_mock_sensor_response(
        sensor: Sensor,
        value: str = 'active',
        timestamp: Optional[datetime] = None,
        has_video: bool = True
    ) -> Dict:
        """
        Create a single mock sensor response.
        
        Args:
            sensor: The sensor that generated this response
            value: The sensor value (e.g., 'active', 'idle')
            timestamp: Response timestamp (defaults to now)
            has_video: Whether this response has associated video
            
        Returns:
            Dictionary representing a mock sensor response
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        return {
            'sensor': sensor,
            'value': value,
            'timestamp': timestamp,
            'has_video_stream': has_video,
            'details': f'{value.capitalize()} state detected',
            'source_image_url': f'/static/mock/snapshot_{timestamp.timestamp()}.jpg' if has_video else None,
        }
    
    @staticmethod
    def create_timeline_test_data(sensor: Sensor) -> List[Dict]:
        """
        Create test data specifically for timeline grouping scenarios.
        Includes edge cases like many events in one day, sparse events, etc.
        
        Args:
            sensor: The sensor to create test data for
            
        Returns:
            List of mock sensor history items for timeline testing
        """
        now = datetime.now()
        mock_items = []
        
        # Create a burst of events today (to test hourly grouping)
        for hour in range(12):
            for minute_offset in [0, 20, 40]:
                timestamp = now.replace(hour=hour, minute=minute_offset, second=0, microsecond=0)
                mock_items.append({
                    'id': len(mock_items) + 1000,
                    'sensor': sensor,
                    'value': 'active' if minute_offset == 0 else 'idle',
                    'timestamp': timestamp,
                    'duration_seconds': 120,
                    'has_video_stream': True,
                    'details': f'Event at {timestamp.strftime("%H:%M")}',
                })
        
        # Add some events yesterday (sparse, to test daily grouping)
        yesterday = now - timedelta(days=1)
        for hour in [8, 14, 20]:
            timestamp = yesterday.replace(hour=hour, minute=0, second=0, microsecond=0)
            mock_items.append({
                'id': len(mock_items) + 1000,
                'sensor': sensor,
                'value': 'active',
                'timestamp': timestamp,
                'duration_seconds': 180,
                'has_video_stream': True,
                'details': f'Yesterday event at {hour}:00',
            })
        
        # Add a few older events
        for days_ago in [3, 5, 7]:
            timestamp = now - timedelta(days=days_ago, hours=12)
            mock_items.append({
                'id': len(mock_items) + 1000,
                'sensor': sensor,
                'value': 'idle',
                'timestamp': timestamp,
                'duration_seconds': 90,
                'has_video_stream': True,
                'details': f'Event {days_ago} days ago',
            })
        
        # Sort by timestamp descending (most recent first)
        mock_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return mock_items
    
    @staticmethod
    def create_timeline_preservation_test_data(sensor: Sensor) -> Tuple[List[SensorHistory], datetime, datetime]:
        """
        Create comprehensive test data for timeline preservation testing.
        Returns actual SensorHistory records with defined window boundaries.
        
        Args:
            sensor: The sensor to create test data for
            
        Returns:
            Tuple of (sensor_history_records, window_start, window_end)
        """
        # Create timezone-aware base time
        base_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        records = []
        
        # Create 10 records spanning 10 hours (1 per hour)
        for hours_ago in range(10):
            timestamp = base_time - timezone.timedelta(hours=hours_ago)
            record = SensorHistory.objects.create(
                sensor=sensor,
                value='active' if hours_ago % 3 == 0 else 'idle',
                response_datetime=timestamp,
                has_video_stream=True,
                details=f'{{"event_id": "{hours_ago}", "duration_seconds": "{60 + hours_ago * 15}"}}'
            )
            records.append(record)
        
        # Define window boundaries (hours 2-6 ago)
        window_start = base_time - timezone.timedelta(hours=6)
        window_end = base_time - timezone.timedelta(hours=2)
        
        return records, window_start, window_end
    
    @staticmethod
    def create_timezone_aware_sensor_responses(
        sensor: Sensor,
        num_responses: int = 5,
        start_time: Optional[datetime] = None,
        time_interval_hours: int = 1
    ) -> List[SensorResponse]:
        """
        Create timezone-aware sensor responses for testing datetime operations.
        
        Args:
            sensor: The sensor to create responses for
            num_responses: Number of responses to create
            start_time: Starting timestamp (defaults to now)
            time_interval_hours: Hours between each response
            
        Returns:
            List of timezone-aware SensorResponse objects
        """
        if start_time is None:
            start_time = timezone.now()
        
        # Ensure start_time is timezone-aware
        if start_time.tzinfo is None:
            start_time = timezone.make_aware(start_time)
        
        responses = []
        for i in range(num_responses):
            timestamp = start_time - timezone.timedelta(hours=i * time_interval_hours)
            integration_key = IntegrationKey(
                integration_id='test_integration',
                integration_name=f'sensor_{sensor.id}_response_{i}'
            )
            
            response = SensorResponse(
                integration_key=integration_key,
                value='active' if i % 2 == 0 else 'idle',
                timestamp=timestamp,
                sensor=sensor,
                detail_attrs={
                    'sensor_history_id': str(1000 + i),
                    'duration_seconds': str(90 + i * 30),
                    'details': f'Test event {i} - {timestamp.strftime("%Y-%m-%d %H:%M:%S %Z")}'
                },
                has_video_stream=True
            )
            responses.append(response)
        
        return responses
    
    @staticmethod
    def create_window_boundary_test_scenario(
        sensor: Sensor
    ) -> Tuple[List[SensorHistory], SensorHistory, SensorHistory, datetime, datetime]:
        """
        Create a specific test scenario for window boundary testing.
        Returns records inside window, outside window, and window boundaries.
        
        Args:
            sensor: The sensor to create test data for
            
        Returns:
            Tuple of (all_records, record_inside_window, record_outside_window, window_start, window_end)
        """
        base_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        all_records = []
        
        # Create records spanning 8 hours
        for hours_ago in range(8):
            timestamp = base_time - timezone.timedelta(hours=hours_ago)
            record = SensorHistory.objects.create(
                sensor=sensor,
                value=f'event_{hours_ago}',
                response_datetime=timestamp,
                has_video_stream=True,
                details=f'{{"hours_ago": "{hours_ago}"}}'
            )
            all_records.append(record)
        
        # Define window boundaries (3-5 hours ago)
        window_start = base_time - timezone.timedelta(hours=5)
        window_end = base_time - timezone.timedelta(hours=3)
        
        # Identify specific records for testing
        record_inside_window = all_records[4]   # 4 hours ago - inside window
        record_outside_window = all_records[1]  # 1 hour ago - outside window
        
        return all_records, record_inside_window, record_outside_window, window_start, window_end
    
    @staticmethod
    def create_pagination_test_data(
        sensor: Sensor,
        total_records: int = 20,
        window_size: int = 5
    ) -> Tuple[List[SensorHistory], int]:
        """
        Create test data for pagination and window size testing.
        
        Args:
            sensor: The sensor to create test data for
            total_records: Total number of records to create
            window_size: Expected window size for pagination tests
            
        Returns:
            Tuple of (all_records, middle_record_index)
        """
        base_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        records = []
        
        for i in range(total_records):
            timestamp = base_time - timezone.timedelta(hours=i)
            record = SensorHistory.objects.create(
                sensor=sensor,
                value=f'record_{i}',
                response_datetime=timestamp,
                has_video_stream=True,
                details=f'{{"record_index": "{i}"}}'
            )
            records.append(record)
        
        middle_index = total_records // 2
        return records, middle_index
