"""
Helper class for video stream browsing functionality.
Encapsulates business logic for sensor history browsing, timeline grouping,
and sensor selection for video streams.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor

from .console_manager import ConsoleManager


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
    def group_history_by_time(cls, history_items: List[Dict]) -> List[Dict]:
        """
        Group history items by time period for timeline display.
        Uses adaptive grouping - hourly if many events in a day, otherwise daily.
        
        Args:
            history_items: List of history item dictionaries with 'timestamp' field
            
        Returns:
            List of grouped timeline items
        """
        if not history_items:
            return []
        
        groups = []
        current_date = None
        current_hour = None
        current_group = None
        
        # Determine if we should group by hour (if many events in current day)
        today = datetime.now().date()
        today_count = sum(1 for h in history_items if h['timestamp'].date() == today)
        use_hourly = today_count > 10
        
        for item in history_items:
            item_date = item['timestamp'].date()
            item_hour = item['timestamp'].hour
            
            # Create new group if needed
            if use_hourly and item_date == today:
                # Group by hour for today if many events
                if current_date != item_date or current_hour != item_hour:
                    current_date = item_date
                    current_hour = item_hour
                    current_group = {
                        'label': f"{item['timestamp'].strftime('%I:00 %p')}",
                        'date': item_date,
                        'items': []
                    }
                    groups.append(current_group)
            else:
                # Group by day
                if current_date != item_date:
                    current_date = item_date
                    current_hour = None
                    if item_date == today:
                        label = "Today"
                    elif item_date == today - timedelta(days=1):
                        label = "Yesterday"
                    else:
                        label = item['timestamp'].strftime('%B %d')
                    
                    current_group = {
                        'label': label,
                        'date': item_date,
                        'items': []
                    }
                    groups.append(current_group)
            
            if current_group:
                current_group['items'].append(item)
        
        return groups
    
    @classmethod
    def find_navigation_items(cls, history_items: List[Dict], current_id: int) -> tuple:
        """
        Find previous and next history items for navigation.
        
        Args:
            history_items: List of history items
            current_id: ID of current item
            
        Returns:
            Tuple of (previous_item, next_item), either can be None
        """
        if not history_items or not current_id:
            return (None, None)
        
        current_item = next((h for h in history_items if h.get('id') == current_id), None)
        if not current_item:
            return (None, None)
        
        try:
            current_idx = history_items.index(current_item)
            prev_item = history_items[current_idx - 1] if current_idx > 0 else None
            next_item = history_items[current_idx + 1] if current_idx < len(history_items) - 1 else None
            return (prev_item, next_item)
        except (ValueError, IndexError):
            return (None, None)
