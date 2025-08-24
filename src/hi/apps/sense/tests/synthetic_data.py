"""
Synthetic data generators for testing sensor-related functionality.
These generators create mock/synthetic data that can be reused across
tests and development scenarios.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from hi.apps.sense.models import Sensor
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
            detail_attrs = {
                'mock_id': str(1000 + i),  # Mock ID for compatibility
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
