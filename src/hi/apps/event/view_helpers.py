from typing import List, Dict, Any
from django.utils import timezone

from .models import EventHistory


class EventHistoryViewHelper:
    """
    Helper class to encapsulate business logic for EventHistoryView.
    Handles complex data transformations for event history display and video integration.
    """
    
    @classmethod
    def enhance_event_history_list(cls, event_history_list: List[EventHistory]) -> List[EventHistory]:
        """
        Enhance a list of EventHistory objects with computed fields for display and video integration.
        
        Args:
            event_history_list: List of EventHistory objects with prefetched relationships
            
        Returns:
            The same list with additional computed attributes added to each EventHistory object:
            - entity_count: Number of entities involved in the event
            - entity_names: List of entity names
            - video_entities: List of entities with video capabilities
            - entity_display_list: Unified list for template rendering
            - video_url_timestamp: Adjusted timestamp for video browser integration
        """
        for event_history in event_history_list:
            cls._add_entity_information(event_history)
            cls._add_video_integration_data(event_history)
            cls._add_timestamp_adjustment(event_history)
            
        return event_history_list
    
    @classmethod
    def _add_entity_information(cls, event_history: EventHistory) -> None:
        """Add basic entity count and names to EventHistory object."""
        event_history.entity_count = event_history.event_definition.event_clauses.count()
        event_history.entity_names = [
            clause.entity_state.entity.name 
            for clause in event_history.event_definition.event_clauses.all()
        ]
    
    @classmethod
    def _add_video_integration_data(cls, event_history: EventHistory) -> None:
        """Add video-related data structures for browser integration."""
        # Group video-capable sensors by entity for video browser integration
        video_entities = cls._group_video_entities_by_entity(event_history)
        event_history.video_entities = list(video_entities.values())
        
        # Create unified entity display list that combines regular entities and video entities
        event_history.entity_display_list = cls._create_entity_display_list(
            event_history, video_entities
        )
    
    @classmethod
    def _group_video_entities_by_entity(cls, event_history: EventHistory) -> Dict[int, Dict[str, Any]]:
        """
        Group video-capable sensors by their parent entity.
        
        Returns:
            Dict mapping entity.id to {'entity': Entity, 'sensors': [Sensor, ...]}
        """
        video_entities = {}
        
        for clause in event_history.event_definition.event_clauses.all():
            entity = clause.entity_state.entity
            for sensor in clause.entity_state.sensors.all():
                if sensor.provides_video_stream:
                    if entity.id not in video_entities:
                        video_entities[entity.id] = {
                            'entity': entity,
                            'sensors': []
                        }
                    video_entities[entity.id]['sensors'].append(sensor)
        
        return video_entities
    
    @classmethod
    def _create_entity_display_list(cls, event_history: EventHistory,
                                    video_entities: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create unified entity display list for template rendering.
        
        Returns:
            List of dicts with keys: 'entity', 'has_video', 'video_sensor'
        """
        entity_display_list = []
        
        for clause in event_history.event_definition.event_clauses.all():
            entity = clause.entity_state.entity
            
            # Check if this entity has video capability
            video_info = video_entities.get(entity.id)
            if video_info:
                # Entity has video - create display object with video info
                entity_display_list.append({
                    'entity': entity,
                    'has_video': True,
                    'video_sensor': video_info['sensors'][0]  # Use first available video sensor
                })
            else:
                # Entity has no video - create display object for text display
                entity_display_list.append({
                    'entity': entity,
                    'has_video': False,
                    'video_sensor': None
                })
        
        return entity_display_list
    
    @classmethod
    def _add_timestamp_adjustment(cls, event_history: EventHistory) -> None:
        """Add adjusted timestamp for inclusive video browser results."""
        # Add 2 minutes to event timestamp for inclusive video browser results
        # This ensures we capture the triggering response + surrounding context
        adjusted_timestamp = event_history.event_datetime + timezone.timedelta(minutes=2)
        event_history.video_url_timestamp = int(adjusted_timestamp.timestamp())
