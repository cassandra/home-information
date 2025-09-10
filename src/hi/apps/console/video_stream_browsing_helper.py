"""
Helper class for video stream browsing functionality.
Encapsulates business logic for sensor history browsing, timeline grouping,
and sensor selection for video streams.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse

from django.core.exceptions import BadRequest
from django.utils import timezone
from django.urls import resolve, Resolver404

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.transient_models import SensorResponse

from .console_manager import ConsoleManager
from .enums import VideoDispatchType
from .transient_models import EntitySensorHistoryData, VideoDispatchResult


class VideoStreamBrowsingHelper:
    """Helper class for video stream browsing operations."""
    
    # Use ConsoleManager's priority list as the single source of truth
    # This ensures consistency across the application
    SENSOR_STATE_TYPE_PRIORITY = ConsoleManager.STATUS_ENTITY_STATE_PRIORITY
    
    @classmethod
    def find_video_sensor_for_entity( cls, entity: Entity ) -> Optional[Sensor]:
        """
        Find the first sensor with video capability for an entity.
        Uses priority order to select the best sensor and optimizes queries.
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
    def create_sensor_response_with_history_id(
            cls,
            sensor_history  : SensorHistory) -> SensorResponse:
        sensor_response = SensorResponse.from_sensor_history(sensor_history)
        
        # Set the core Django primary key as a proper property
        sensor_response.sensor_history_id = sensor_history.id
        
        return sensor_response
    
    @classmethod
    def get_timeline_window(
            cls,
            sensor                  : Sensor,
            center_record           : SensorHistory = None,
            window_size             : int = 50,
            preserve_window_bounds  : tuple = None ):
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
            has_older_records = cls._has_older_records(
                sensor = sensor,
                timestamp = start_time
            )
            has_newer_records = cls._has_newer_records(
                sensor = sensor,
                timestamp = end_time
            )
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
                window_start_timestamp = min( record.response_datetime
                                              for record in history_records )
                window_end_timestamp = max( record.response_datetime
                                            for record in history_records )
        
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
    def group_responses_by_time( cls,
                                 sensor_responses  : List[SensorResponse],
                                 user_timezone     : str           = None ) -> List[Dict]:
        """
        Group sensor responses by time period for timeline display.
        Uses adaptive grouping - hourly if many events in a day, otherwise daily.
        
        Args:
            sensor_responses: List of SensorResponse objects
            user_timezone: User's timezone string (e.g., 'America/Chicago').
            If None, uses UTC.
            
        Returns:
            List of grouped timeline items
        """
        if not sensor_responses:
            return []
        
        groups = []
        current_date = None
        current_hour = None
        current_group = None
        
        # Set up timezone conversion if user timezone provided
        if user_timezone:
            import pytz
            try:
                tz = pytz.timezone(user_timezone)
                # Get current date in user's timezone
                now_in_user_tz = timezone.now().astimezone(tz)
                today = now_in_user_tz.date()
                yesterday = today - timedelta(days=1)
            except pytz.UnknownTimeZoneError:
                # Fall back to UTC if invalid timezone
                user_timezone = None
                today = timezone.now().date()
                yesterday = today - timedelta(days=1)
        else:
            # Use UTC (original behavior)
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)
        
        # Count events for today to determine if we should use hourly grouping
        if user_timezone:
            today_count = sum( 1 for response in sensor_responses 
                               if response.timestamp.astimezone(tz).date() == today)
        else:
            today_count = sum( 1 for response in sensor_responses 
                               if response.timestamp.date() == today)
        use_hourly = today_count > 10
        
        for response in sensor_responses:
            # Convert response timestamp to user timezone if provided
            if user_timezone:
                response_in_tz = response.timestamp.astimezone(tz)
                response_date = response_in_tz.date()
                response_hour = response_in_tz.hour
            else:
                response_in_tz = response.timestamp
                response_date = response.timestamp.date()
                response_hour = response.timestamp.hour
            
            # Create new group if needed
            if use_hourly and response_date == today:
                # Group by hour for today if many events
                if current_date != response_date or current_hour != response_hour:
                    current_date = response_date
                    current_hour = response_hour
                    current_group = {
                        'label': f"{response_in_tz.strftime('%I:00 %p')}",
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
                        label = f"Today {response_in_tz.strftime('%a')}"
                    elif response_date == yesterday:
                        label = f"Yesterday {response_in_tz.strftime('%a')}"
                    else:
                        label = f"{response_in_tz.strftime('%B %d %a')}"
                    
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
    def find_navigation_items( cls,
                               sensor_responses           : List[SensorResponse], 
                               current_sensor_history_id  : int ) -> tuple:
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
             if r.sensor_history_id == current_sensor_history_id), 
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
    def find_adjacent_records( cls,
                               sensor              : Sensor,
                               current_history_id  : int ) -> tuple:
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
    def build_sensor_history_data_default(
            cls,
            sensor             : Sensor,
            sensor_history_id  : int      = None,
            user_timezone      : str      = None) -> EntitySensorHistoryData:
        """Build data for default view (most recent events or centered on specific record)."""
        return cls._build_sensor_history_data_internal(
            sensor, sensor_history_id, None, None, user_timezone
        )
    
    @classmethod 
    def build_sensor_history_data_with_window(
            cls,
            sensor                 : Sensor,
            sensor_history_id      : int       = None,
            preserve_window_start  : datetime  = None, 
            preserve_window_end    : datetime  = None,
            user_timezone          : str       = None ) -> EntitySensorHistoryData:
        """Build data for specific window preservation."""
        return cls._build_sensor_history_data_internal(
            sensor, sensor_history_id, preserve_window_start, preserve_window_end, user_timezone
        )
    
    @classmethod
    def build_sensor_history_data_earlier(
            cls,
            sensor           : Sensor,
            pivot_timestamp  : int,
            user_timezone    : str = None) -> EntitySensorHistoryData:
        """Build data for pagination to earlier events."""
        pivot_time = timezone.make_aware(datetime.fromtimestamp(pivot_timestamp))
        
        # Get events before the pivot time
        history_records = list(SensorHistory.objects.filter(
            sensor = sensor,
            has_video_stream = True,
            response_datetime__lt = pivot_time
        ).order_by('-response_datetime')[:50])
        
        if not history_records:
            # No earlier records found - check for newer records to set pagination accurately
            has_newer_records = cls._has_newer_records(
                sensor = sensor,
                timestamp = pivot_timestamp
            )
            
            return EntitySensorHistoryData(
                sensor_responses = [],
                current_sensor_response = None,
                timeline_groups = [],
                pagination_metadata = {'has_older_records': False, 'has_newer_records': has_newer_records},
                prev_sensor_response = None,
                next_sensor_response = None,
                window_start_timestamp = None,
                window_end_timestamp = pivot_timestamp if has_newer_records else None,
            )
        
        # Convert to SensorResponse objects
        sensor_responses = []
        for record in history_records:
            sensor_response = cls.create_sensor_response_with_history_id(record)
            sensor_responses.append(sensor_response)
        
        # Use the most recent record as current (first in the list due to DESC ordering)
        current_sensor_response = sensor_responses[0] if sensor_responses else None
        
        # Group sensor responses by time period
        timeline_groups = cls.group_responses_by_time(sensor_responses, user_timezone)
        
        # Calculate pagination metadata
        timestamps = [record.response_datetime for record in history_records]
        window_start = min(timestamps)
        window_end = max(timestamps)
        
        # Check for more records beyond this window
        has_older_records = cls._has_older_records(
            sensor = sensor,
            timestamp = window_start
        )
        
        has_newer_records = cls._has_newer_records(
            sensor = sensor,
            timestamp = window_end
        )
        
        pagination_metadata = {
            'has_older_records': has_older_records,
            'has_newer_records': has_newer_records,
            'window_start_timestamp': window_start,
            'window_end_timestamp': window_end,
        }
        
        # Find navigation items
        current_history_id = current_sensor_response.sensor_history_id if current_sensor_response else None
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
            window_start_timestamp=window_start,
            window_end_timestamp=window_end,
        )
    
    @classmethod
    def build_sensor_history_data_later( cls,
                                         sensor           : Sensor,
                                         pivot_timestamp  : int,
                                         user_timezone    : str = None ) -> EntitySensorHistoryData:
        """Build data for pagination to later events.""" 
        pivot_time = timezone.make_aware(datetime.fromtimestamp(pivot_timestamp))
        
        # Get 50 events after the pivot time (ordered chronologically, oldest first)
        history_records = list( SensorHistory.objects.filter(
            sensor=sensor,
            has_video_stream=True,
            response_datetime__gt=pivot_time
        ).order_by('response_datetime')[:50])
        
        if not history_records:
            # No later records found - check for older records to set pagination accurately
            has_older_records = cls._has_older_records(
                sensor = sensor,
                timestamp = pivot_timestamp
            )
            
            return EntitySensorHistoryData(
                sensor_responses=[],
                current_sensor_response=None,
                timeline_groups=[],
                pagination_metadata={'has_older_records': has_older_records, 'has_newer_records': False},
                prev_sensor_response=None,
                next_sensor_response=None,
                window_start_timestamp = pivot_timestamp if has_older_records else None,
                window_end_timestamp = None,
            )
        
        # Reverse to newest first for display (matching our standard ordering)
        history_records.reverse()
        
        # Convert to SensorResponse objects
        sensor_responses = []
        for record in history_records:
            sensor_response = cls.create_sensor_response_with_history_id(record)
            sensor_responses.append(sensor_response)
        
        # Use the most recent record as current (first in the list after reversal)
        current_sensor_response = sensor_responses[0] if sensor_responses else None
        
        # Group sensor responses by time period
        timeline_groups = cls.group_responses_by_time(sensor_responses, user_timezone)
        
        # Calculate pagination metadata
        timestamps = [record.response_datetime for record in history_records]
        window_start = min(timestamps)
        window_end = max(timestamps)
        
        # Check for more records beyond this window
        has_older_records = cls._has_older_records(
            sensor = sensor,
            timestamp = window_start
        )
        
        has_newer_records = cls._has_newer_records(
            sensor = sensor,
            timestamp = window_end
        )
        
        pagination_metadata = {
            'has_older_records': has_older_records,
            'has_newer_records': has_newer_records,
            'window_start_timestamp': window_start,
            'window_end_timestamp': window_end,
        }
        
        # Find navigation items
        current_history_id = current_sensor_response.sensor_history_id if current_sensor_response else None
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
            window_start_timestamp=window_start,
            window_end_timestamp=window_end,
        )
    
    @classmethod
    def build_sensor_history_data(
            cls,
            sensor                 : Sensor,
            sensor_history_id      : int       = None,
            preserve_window_start  : datetime  = None,
            preserve_window_end    : datetime  = None,
            user_timezone          : str       = None ) -> EntitySensorHistoryData:
        """Legacy method - delegates to window preservation method."""
        return cls.build_sensor_history_data_with_window(
            sensor, sensor_history_id, preserve_window_start, preserve_window_end, user_timezone
        )
    
    @classmethod
    def _build_sensor_history_data_internal(
            cls,
            sensor                 : Sensor,
            sensor_history_id      : int       = None,
            preserve_window_start  : datetime  = None,
            preserve_window_end    : datetime  = None,
            user_timezone          : str       = None ) -> EntitySensorHistoryData:
        """
        Build all data needed for the sensor history view.
        High-level method that encapsulates the business logic.
        
        Args:
            sensor: Sensor to get data for
            sensor_history_id: Optional specific record ID to display
            preserve_window_start: Start timestamp for timeline preservation
            preserve_window_end: End timestamp for timeline preservation
            user_timezone: User's timezone string for display grouping
            
        Returns:
            EntitySensorHistoryData containing all view data
        """
        # Determine window strategy: preserve existing timeline or create new one
        preserve_window_bounds = None
        if preserve_window_start and preserve_window_end:
            preserve_window_bounds = (preserve_window_start, preserve_window_end)
        
        # Convert sensor_history_id to int if it's a string (from URL kwargs)
        if sensor_history_id:
            if isinstance(sensor_history_id, str):
                sensor_history_id = int(sensor_history_id)
        
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
                     if r.sensor_history_id == sensor_history_id),
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
        timeline_groups = cls.group_responses_by_time(sensor_responses, user_timezone)
        
        # Find previous and next responses for navigation
        current_history_id = sensor_history_id if sensor_history_id else None
        
        # If no specific sensor_history_id, try to get it from current_sensor_response
        if not current_history_id and current_sensor_response:
            # Extract sensor_history_id from the current response
            current_history_id = current_sensor_response.sensor_history_id
        
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
    
    @classmethod
    def _has_older_records(cls, sensor: Sensor, timestamp: int) -> bool:
        """Check if sensor has records earlier than the given timestamp."""
        if isinstance( timestamp, datetime):
            pivot_datetime = timestamp
        else:
            pivot_datetime = timezone.make_aware(datetime.fromtimestamp(timestamp))
        return SensorHistory.objects.filter(
            sensor = sensor,
            has_video_stream = True,
            response_datetime__lt = pivot_datetime
        ).exists()

    @classmethod
    def _has_newer_records(cls, sensor: Sensor, timestamp: int) -> bool:
        """Check if sensor has records later than the given timestamp."""
        if isinstance( timestamp, datetime):
            pivot_datetime = timestamp
        else:
            pivot_datetime = timezone.make_aware(datetime.fromtimestamp(timestamp))
        return SensorHistory.objects.filter(
            sensor = sensor,
            has_video_stream = True,
            response_datetime__gt = pivot_datetime
        ).exists()

    @classmethod
    def get_video_dispatch_result( cls,
                                   entity        : Entity,
                                   referrer_url  : str    ) -> VideoDispatchResult:
        """
        Determine the appropriate video dispatch based on referrer URL context.
        
        Logic:
        - If referrer has sensor_history_id with window bounds, use earlier view with start time
        - If referrer has sensor_history_id without bounds, use default view  
        - If referrer is "earlier" view, preserve it with same timestamp
        - If referrer is "later" view, preserve it with same timestamp
        - Otherwise use default (latest events)
        
        Returns:
            VideoDispatchResult with dispatch type and necessary parameters
        """
        video_sensor = cls.find_video_sensor_for_entity(entity)
        if not video_sensor:
            raise BadRequest( f'No video sensor found for entity {entity.id}.' )
        
        # Extract timeline context from referrer URL if available
        try:
            parsed_url = urlparse(referrer_url)
            path = parsed_url.path
            
            resolved = resolve(path)
            url_name = resolved.url_name
            
            # Case 1: Referrer has sensor_history_id with window bounds
            # Use EntityVideoSensorHistoryEarlierView to preserve timeline
            if url_name == 'console_entity_video_sensor_history_detail_with_context':
                window_start_str = resolved.kwargs.get('window_start', '')
                window_end_str = resolved.kwargs.get('window_end', '')
                if ( window_start_str
                     and window_start_str.isdigit()
                     and window_end_str
                     and window_end_str.isdigit() ):
                    timestamp = int(window_start_str)
                    
                    # Try earlier records first (preserve original intent)
                    if cls._has_older_records(video_sensor, timestamp):
                        return VideoDispatchResult(
                            dispatch_type = VideoDispatchType.HISTORY_EARLIER,
                            sensor = video_sensor,
                            timestamp = timestamp,
                        )
                    # Fallback: show later records (closest in time)
                    else:
                        return VideoDispatchResult(
                            dispatch_type = VideoDispatchType.HISTORY_LATER,
                            sensor = video_sensor,
                            timestamp = timestamp,
                        )
            
            # Case 2: Referrer has sensor_history_id without window bounds  
            # Use default view (it will center around most recent)
            elif url_name == 'console_entity_video_sensor_history_detail':
                return VideoDispatchResult(
                    dispatch_type = VideoDispatchType.HISTORY_DEFAULT,
                    sensor = video_sensor
                )
                
            # Case 3: Referrer is "earlier" pagination view
            # Preserve the same earlier view with same timestamp
            elif url_name == 'console_entity_video_sensor_history_earlier':
                timestamp_str = resolved.kwargs.get('timestamp', '')
                if timestamp_str and timestamp_str.isdigit():
                    timestamp = int(timestamp_str)
                    
                    # Try to preserve earlier view
                    if cls._has_older_records(video_sensor, timestamp):
                        return VideoDispatchResult(
                            dispatch_type = VideoDispatchType.HISTORY_EARLIER,
                            sensor = video_sensor,
                            timestamp = timestamp
                        )
                    # Fallback: show later records (closest in time)
                    else:
                        return VideoDispatchResult(
                            dispatch_type = VideoDispatchType.HISTORY_LATER,
                            sensor = video_sensor,
                            timestamp = timestamp
                        )
                    
            # Case 4: Referrer is "later" pagination view  
            # Preserve the same later view with same timestamp
            elif url_name == 'console_entity_video_sensor_history_later':
                timestamp_str = resolved.kwargs.get('timestamp', '')
                if timestamp_str and timestamp_str.isdigit():
                    timestamp = int(timestamp_str)
                    
                    # Try to preserve later view
                    if cls._has_newer_records(video_sensor, timestamp):
                        return VideoDispatchResult(
                            dispatch_type = VideoDispatchType.HISTORY_LATER,
                            sensor = video_sensor,
                            timestamp = timestamp
                        )
                    # Fallback: show earlier records (closest in time)
                    else:
                        return VideoDispatchResult(
                            dispatch_type = VideoDispatchType.HISTORY_EARLIER,
                            sensor = video_sensor,
                            timestamp = timestamp
                        )
                    
            # Case 5: Basic sensor history view (no specific event)
            # Use default view
            elif url_name == 'console_entity_video_sensor_history':
                return VideoDispatchResult(
                    dispatch_type = VideoDispatchType.HISTORY_DEFAULT,
                    sensor = video_sensor
                )
                    
        except (Resolver404, ValueError, KeyError):
            # No timeline context available - use default behavior
            pass
        
        # Default fallback - use most recent history
        return VideoDispatchResult(
            dispatch_type = VideoDispatchType.HISTORY_DEFAULT,
            sensor = video_sensor
        )
