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
    def create_timeline_test_data(sensor: Sensor, dense_events: bool = True) -> List[Dict]:
        """
        Create test data specifically for timeline grouping scenarios.
        Supports both dense (many events) and sparse (few events) patterns.
        
        Args:
            sensor: The sensor to create test data for
            dense_events: If True, creates many events today; if False, creates sparse events
            
        Returns:
            List of mock sensor history items for timeline testing
        """
        now = datetime.now()
        mock_items = []
        item_counter = 1000
        
        if dense_events:
            # Create dense events today (3 events per hour for 12 hours = 36 events)
            # Simplified from nested loops to single loop with calculation
            for event_num in range(36):
                hour = event_num // 3  # 0-11 hours
                minute_offset = (event_num % 3) * 20  # 0, 20, 40 minutes
                
                timestamp = now.replace(hour=hour, minute=minute_offset, second=0, microsecond=0)
                mock_items.append({
                    'id': item_counter + event_num,
                    'sensor': sensor,
                    'value': 'active' if minute_offset == 0 else 'idle',
                    'timestamp': timestamp,
                    'duration_seconds': 120,
                    'has_video_stream': True,
                    'details': f'Event at {timestamp.strftime("%H:%M")}',
                })
            item_counter += 36
        
        # Add yesterday's events (always sparse for contrast)
        yesterday = now - timedelta(days=1)
        yesterday_hours = [8, 14, 20]
        for i, hour in enumerate(yesterday_hours):
            timestamp = yesterday.replace(hour=hour, minute=0, second=0, microsecond=0)
            mock_items.append({
                'id': item_counter + i,
                'sensor': sensor,
                'value': 'active',
                'timestamp': timestamp,
                'duration_seconds': 180,
                'has_video_stream': True,
                'details': f'Yesterday event at {hour}:00',
            })
        item_counter += len(yesterday_hours)
        
        # Add older events
        older_days = [3, 5, 7]
        for i, days_ago in enumerate(older_days):
            timestamp = now - timedelta(days=days_ago, hours=12)
            mock_items.append({
                'id': item_counter + i,
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
    def create_timeline_test_scenario(
        sensor: Sensor,
        scenario_type: str = 'preservation',
        total_records: int = None,
        window_size: int = None,
        **kwargs
    ):
        """
        Unified method for creating timeline test scenarios.
        
        Args:
            sensor: The sensor to create test data for
            scenario_type: Type of scenario - 'preservation', 'boundary', or 'pagination'
            total_records: Override default record count for scenario
            window_size: Override default window size for scenario
            **kwargs: Additional scenario-specific parameters
            
        Returns:
            Scenario-specific tuple of test data and metadata
            
        Scenario Types:
        - 'preservation': Returns (records, window_start, window_end)
        - 'boundary': Returns (all_records, inside_record, outside_record, window_start, window_end)
        - 'pagination': Returns (records, middle_record_index)
        """
        base_time = timezone.now().replace(minute=0, second=0, microsecond=0)
        
        if scenario_type == 'preservation':
            # Timeline preservation scenario
            record_count = total_records or 10
            records = []
            
            for hours_ago in range(record_count):
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
            
        elif scenario_type == 'boundary':
            # Window boundary testing scenario
            record_count = total_records or 8
            all_records = []
            
            for hours_ago in range(record_count):
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
            
        elif scenario_type == 'pagination':
            # Pagination testing scenario
            record_count = total_records or 20
            window = window_size or 5  # Default window size
            records = []
            
            for i in range(record_count):
                timestamp = base_time - timezone.timedelta(hours=i)
                record = SensorHistory.objects.create(
                    sensor=sensor,
                    value=f'record_{i}',
                    response_datetime=timestamp,
                    has_video_stream=True,
                    details=f'{{"record_index": "{i}", "window_size": "{window}"}}'
                )
                records.append(record)
            
            middle_index = record_count // 2
            return records, middle_index
            
        else:
            raise ValueError(f"Unknown scenario_type: {scenario_type}. Must be 'preservation', 'boundary', or 'pagination'.")
    
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
    
    # Legacy methods for backward compatibility - use create_timeline_test_scenario instead
    @staticmethod
    def create_timeline_preservation_test_data(sensor: Sensor) -> Tuple[List[SensorHistory], datetime, datetime]:
        """Legacy method - use create_timeline_test_scenario(scenario_type='preservation') instead."""
        return SensorHistorySyntheticData.create_timeline_test_scenario(sensor, 'preservation')
    
    @staticmethod
    def create_window_boundary_test_scenario(
        sensor: Sensor
    ) -> Tuple[List[SensorHistory], SensorHistory, SensorHistory, datetime, datetime]:
        """Legacy method - use create_timeline_test_scenario(scenario_type='boundary') instead."""
        return SensorHistorySyntheticData.create_timeline_test_scenario(sensor, 'boundary')
    
    @staticmethod
    def create_pagination_test_data(
        sensor: Sensor,
        total_records: int = 20,
        window_size: int = 5
    ) -> Tuple[List[SensorHistory], int]:
        """Legacy method - use create_timeline_test_scenario(scenario_type='pagination') instead."""
        return SensorHistorySyntheticData.create_timeline_test_scenario(
            sensor, 'pagination', total_records=total_records, window_size=window_size
        )
