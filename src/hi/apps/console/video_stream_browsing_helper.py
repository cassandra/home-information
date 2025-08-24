"""
Helper class for video stream browsing functionality.
Encapsulates business logic for sensor history browsing, timeline grouping,
and sensor selection for video streams.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.transient_models import SensorResponse

from .console_manager import ConsoleManager
from .transient_models import EntitySensorHistoryData


class VideoStreamBrowsingHelper:
    """Helper class for video stream browsing operations."""
    
    # Use ConsoleManager's priority list as the single source of truth
    # This ensures consistency across the application
    SENSOR_STATE_TYPE_PRIORITY = ConsoleManager.STATUS_ENTITY_STATE_PRIORITY
    
    @classmethod
    def find_video_sensor_for_entity(cls, entity: Entity) -> Optional[Sensor]:
        """
        Find the first sensor with video capability for an entity.
        Uses priority order to select the best sensor and optimizes queries.
        
        Args:
            entity: Entity to find video sensor for
            
        Returns:
            First video-capable Sensor found, or None
        """
        if not entity or not entity.has_video_stream:
            return None
        
        # Fetch all entity states with their sensors in a single query
        # Using select_related and prefetch_related to minimize database hits
        entity_states = EntityState.objects.filter(
            entity=entity
        ).prefetch_related(
            'sensors'
        )
        
        # Build a map of state types to their sensors for efficient lookup
        state_type_to_sensors: Dict[str, List[Sensor]] = {}
        for state in entity_states:
            state_type_str = state.entity_state_type_str
            if state_type_str not in state_type_to_sensors:
                state_type_to_sensors[state_type_str] = []
            state_type_to_sensors[state_type_str].extend(
                sensor for sensor in state.sensors.all() 
                if sensor.provides_video_stream
            )
        
        # Check sensors in priority order
        for state_type in cls.SENSOR_STATE_TYPE_PRIORITY:
            state_type_str = str(state_type)
            if state_type_str in state_type_to_sensors:
                sensors = state_type_to_sensors[state_type_str]
                if sensors:
                    return sensors[0]
        
        # If no prioritized sensor found, return any video-capable sensor
        for sensors in state_type_to_sensors.values():
            if sensors:
                return sensors[0]
        
        return None
    
    @classmethod
    def create_sensor_response_with_history_id(cls, sensor_history: SensorHistory) -> SensorResponse:
        """
        Create SensorResponse from SensorHistory and add the history ID for template access.
        
        Args:
            sensor_history: SensorHistory record to convert
            
        Returns:
            SensorResponse object with sensor_history_id added to detail_attrs
        """
        sensor_response = SensorResponse.from_sensor_history(sensor_history)
        
        # Add the sensor_history_id to detail_attrs for template access
        if sensor_response.detail_attrs is None:
            sensor_response.detail_attrs = {}
        sensor_response.detail_attrs['sensor_history_id'] = str(sensor_history.id)
        
        return sensor_response
    
    @classmethod
    def get_timeline_window(
            cls, sensor: Sensor, center_record: SensorHistory = None, window_size: int = 50,
            preserve_window_bounds: tuple = None
    ):
        """
        Get a timeline window of SensorHistory records around a center record.
        Designed to support future pagination functionality.
        
        Args:
            sensor: Sensor to get records for
            center_record: Record to center the window around (None for most recent)
            window_size: Total number of records to include
            preserve_window_bounds: Tuple of (start_datetime, end_datetime) for timeline preservation
            
        Returns:
            Tuple of (sensor_responses_list, pagination_metadata)
        """
        if preserve_window_bounds:
            # Preserve existing timeline window - query records within bounds
            start_time, end_time = preserve_window_bounds
            history_records = list(SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True,
                response_datetime__gte=start_time,
                response_datetime__lte=end_time
            ).order_by('-response_datetime'))
            
            # Check for records outside the preserved window for pagination
            has_older_records = SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True,
                response_datetime__lt=start_time
            ).exists()
            has_newer_records = SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True,
                response_datetime__gt=end_time
            ).exists()
            window_center_timestamp = start_time if history_records else None
        elif center_record is None:
            # No center record - get most recent records (default behavior)
            history_records = SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True
            ).order_by('-response_datetime')[:window_size]
            
            has_older_records = len(history_records) == window_size
            has_newer_records = False
            window_center_timestamp = history_records[0].response_datetime if history_records else None
        else:
            # Center window around specific record
            half_window = window_size // 2
            
            # Get records before center (older timestamps)
            before_records = list(SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True,
                response_datetime__lt=center_record.response_datetime
            ).order_by('-response_datetime')[:half_window])
            
            # Get records after center (newer timestamps) 
            after_records = list(SensorHistory.objects.filter(
                sensor=sensor,
                has_video_stream=True,
                response_datetime__gt=center_record.response_datetime
            ).order_by('response_datetime')[:half_window])
            
            # Combine all records in chronological order (newest first)
            history_records = list(reversed(after_records)) + [center_record] + before_records
            
            # Pagination metadata for future use
            has_older_records = len(before_records) == half_window
            has_newer_records = len(after_records) == half_window
            window_center_timestamp = center_record.response_datetime
        
        # Convert to SensorResponse objects
        sensor_responses = []
        for record in history_records:
            sensor_response = cls.create_sensor_response_with_history_id(record)
            sensor_responses.append(sensor_response)
        
        # Calculate actual window bounds for timeline preservation
        window_start_timestamp = None
        window_end_timestamp = None
        if history_records:
            if preserve_window_bounds:
                window_start_timestamp, window_end_timestamp = preserve_window_bounds
            else:
                # Use actual bounds of returned records
                window_start_timestamp = min(record.response_datetime for record in history_records)
                window_end_timestamp = max(record.response_datetime for record in history_records)
        
        # Pagination metadata for future pagination feature
        pagination_metadata = {
            'has_older_records': has_older_records,
            'has_newer_records': has_newer_records,
            'window_center_timestamp': window_center_timestamp,
            'window_size': window_size,
            'window_start_timestamp': window_start_timestamp,
            'window_end_timestamp': window_end_timestamp,
        }
        
        return sensor_responses, pagination_metadata
    
    @classmethod
    def group_responses_by_time(cls, sensor_responses: List[SensorResponse]) -> List[Dict]:
        """
        Group sensor responses by time period for timeline display.
        Uses adaptive grouping - hourly if many events in a day, otherwise daily.
        
        Args:
            sensor_responses: List of SensorResponse objects
            
        Returns:
            List of grouped timeline items
        """
        if not sensor_responses:
            return []
        
        groups = []
        current_date = None
        current_hour = None
        current_group = None
        
        # Determine if we should group by hour (if many events in current day)
        today = timezone.now().date()
        today_count = sum(1 for response in sensor_responses if response.timestamp.date() == today)
        use_hourly = today_count > 10
        
        for response in sensor_responses:
            response_date = response.timestamp.date()
            response_hour = response.timestamp.hour
            
            # Create new group if needed
            if use_hourly and response_date == today:
                # Group by hour for today if many events
                if current_date != response_date or current_hour != response_hour:
                    current_date = response_date
                    current_hour = response_hour
                    current_group = {
                        'label': f"{response.timestamp.strftime('%I:00 %p')}",
                        'date': response_date,
                        'items': []
                    }
                    groups.append(current_group)
            else:
                # Group by day
                if current_date != response_date:
                    current_date = response_date
                    current_hour = None
                    if response_date == today:
                        label = "Today"
                    elif response_date == today - timedelta(days=1):
                        label = "Yesterday"
                    else:
                        label = response.timestamp.strftime('%B %d')
                    
                    current_group = {
                        'label': label,
                        'date': response_date,
                        'items': []
                    }
                    groups.append(current_group)
            
            if current_group:
                current_group['items'].append(response)
        
        return groups
    
    @classmethod
    def find_navigation_items(
            cls, sensor_responses: List[SensorResponse], 
            current_sensor_history_id: int
    ) -> tuple:
        """
        Find previous and next sensor responses for navigation.
        
        Args:
            sensor_responses: List of SensorResponse objects (with sensor_history_id in detail_attrs)
            current_sensor_history_id: SensorHistory ID of current response
            
        Returns:
            Tuple of (previous_response, next_response), either can be None
        """
        if not sensor_responses or not current_sensor_history_id:
            return (None, None)
        
        current_response = next(
            (r for r in sensor_responses 
             if (r.detail_attrs 
                 and r.detail_attrs.get('sensor_history_id') == str(current_sensor_history_id))), 
            None
        )
        if not current_response:
            return (None, None)
        
        try:
            current_idx = sensor_responses.index(current_response)
            prev_response = sensor_responses[current_idx - 1] if current_idx > 0 else None
            next_response = (
                sensor_responses[current_idx + 1] 
                if current_idx < len(sensor_responses) - 1 else None
            )
            return (prev_response, next_response)
        except (ValueError, IndexError):
            return (None, None)
    
    @classmethod
    def find_adjacent_records(cls, sensor: Sensor, current_history_id: int) -> tuple:
        """
        Find previous and next SensorHistory records for navigation.
        Uses database queries for efficient navigation.
        
        Args:
            sensor: Sensor to find records for
            current_history_id: ID of current SensorHistory record
            
        Returns:
            Tuple of (prev_sensor_response, next_sensor_response), either can be None
        """
        if not current_history_id:
            return (None, None)
        
        try:
            current_record = SensorHistory.objects.get(
                id=current_history_id,
                sensor=sensor,
                has_video_stream=True
            )
        except SensorHistory.DoesNotExist:
            return (None, None)
        
        # Find previous record (older timestamp)
        prev_record = SensorHistory.objects.filter(
            sensor=sensor,
            has_video_stream=True,
            response_datetime__lt=current_record.response_datetime
        ).order_by('-response_datetime').first()
        
        prev_sensor_response = None
        if prev_record:
            prev_sensor_response = cls.create_sensor_response_with_history_id(prev_record)
        
        # Find next record (newer timestamp)
        next_record = SensorHistory.objects.filter(
            sensor=sensor,
            has_video_stream=True,
            response_datetime__gt=current_record.response_datetime
        ).order_by('response_datetime').first()
        
        next_sensor_response = None
        if next_record:
            next_sensor_response = cls.create_sensor_response_with_history_id(next_record)
        
        return (prev_sensor_response, next_sensor_response)
    
    @classmethod
    def build_sensor_history_data(
            cls, sensor: Sensor, sensor_history_id: int = None,
            preserve_window_start: datetime = None, preserve_window_end: datetime = None
    ) -> EntitySensorHistoryData:
        """
        Build all data needed for the sensor history view.
        High-level method that encapsulates the business logic.
        
        Args:
            sensor: Sensor to get data for
            sensor_history_id: Optional specific record ID to display
            preserve_window_start: Start timestamp for timeline preservation
            preserve_window_end: End timestamp for timeline preservation
            
        Returns:
            EntitySensorHistoryData containing all view data
        """
        # Determine window strategy: preserve existing timeline or create new one
        preserve_window_bounds = None
        if preserve_window_start and preserve_window_end:
            preserve_window_bounds = (preserve_window_start, preserve_window_end)
        
        # Smart query strategy based on context and record availability
        if sensor_history_id:
            # Specific record requested
            try:
                current_history_record = SensorHistory.objects.get(
                    id=sensor_history_id,
                    sensor=sensor,
                    has_video_stream=True
                )
                
                # Check if we should preserve timeline (record is within preserve window)
                if preserve_window_bounds:
                    start_time, end_time = preserve_window_bounds
                    if start_time <= current_history_record.response_datetime <= end_time:
                        # Record is within preserve window - use preserved timeline
                        sensor_responses, pagination_metadata = cls.get_timeline_window(
                            sensor, preserve_window_bounds=preserve_window_bounds
                        )
                    else:
                        # Record is outside preserve window - center around it
                        sensor_responses, pagination_metadata = cls.get_timeline_window(
                            sensor, current_history_record
                        )
                else:
                    # No preserve context - center around the record
                    sensor_responses, pagination_metadata = cls.get_timeline_window(
                        sensor, current_history_record
                    )
                
                # Find current record in the timeline
                current_sensor_response = next(
                    (r for r in sensor_responses 
                     if r.detail_attrs and r.detail_attrs.get('sensor_history_id') == str(sensor_history_id)),
                    None
                )
            except SensorHistory.DoesNotExist:
                # Record not found - fall back to most recent window
                sensor_responses, pagination_metadata = cls.get_timeline_window(sensor, None)
                current_sensor_response = sensor_responses[0] if sensor_responses else None
        else:
            # No specific record - get most recent window
            sensor_responses, pagination_metadata = cls.get_timeline_window(sensor, None)
            current_sensor_response = sensor_responses[0] if sensor_responses else None
        
        # Group sensor responses by time period
        timeline_groups = cls.group_responses_by_time(sensor_responses)
        
        # Find previous and next responses for navigation
        current_history_id = sensor_history_id if sensor_history_id else None
        prev_sensor_response, next_sensor_response = cls.find_adjacent_records(
            sensor, current_history_id
        )
        
        return EntitySensorHistoryData(
            sensor_responses=sensor_responses,
            current_sensor_response=current_sensor_response,
            timeline_groups=timeline_groups,
            pagination_metadata=pagination_metadata,
            prev_sensor_response=prev_sensor_response,
            next_sensor_response=next_sensor_response,
            window_start_timestamp=pagination_metadata.get('window_start_timestamp'),
            window_end_timestamp=pagination_metadata.get('window_end_timestamp'),
        )
