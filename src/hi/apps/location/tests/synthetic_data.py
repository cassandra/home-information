"""
Synthetic data generators for Location and LocationView testing.

Provides centralized, reusable test data creation following the project's
synthetic data pattern documented in test-data-management.md.
"""
import uuid
from typing import Optional

from hi.apps.location.models import Location, LocationView
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.entity.enums import EntityType
from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.location.enums import LocationViewType


class LocationSyntheticData:
    """Centralized synthetic data generators for location testing."""
    
    @staticmethod
    def create_test_location(**kwargs) -> Location:
        """Create a test location with reasonable defaults."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': f'Test Location {unique_id}',
            'svg_fragment_filename': f'test-location-{unique_id}.svg',
            'svg_view_box_str': '0 0 800 600',
        }
        defaults.update(kwargs)
        return Location.objects.create(**defaults)
    
    @staticmethod
    def create_test_location_view(location: Optional[Location] = None, **kwargs) -> LocationView:
        """Create a test location view with reasonable defaults."""
        if location is None:
            location = LocationSyntheticData.create_test_location()
        
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'location': location,
            'name': f'Test View {unique_id}',
            'location_view_type_str': str(LocationViewType.DEFAULT),
            'svg_view_box_str': '0 0 800 600',
            'order_id': 0,
            'svg_rotate': 0.0,
        }
        defaults.update(kwargs)
        return LocationView.objects.create(**defaults)
    
    @staticmethod
    def create_test_entity_with_position(location: Optional[Location] = None, **kwargs) -> Entity:
        """Create a test entity with position on a location."""
        if location is None:
            location = LocationSyntheticData.create_test_location()
            
        unique_id = str(uuid.uuid4())[:8]
        entity_defaults = {
            'name': f'Test Entity {unique_id}',
            'integration_id': f'test.entity.{unique_id}',
            'integration_name': 'test_integration',
            'entity_type_str': str(EntityType.LIGHT),
        }
        # Extract position-specific kwargs
        position_kwargs = {
            'svg_x': kwargs.pop('svg_x', 100.0),
            'svg_y': kwargs.pop('svg_y', 100.0),
            'svg_rotate': kwargs.pop('svg_rotate', 0.0),
            'svg_scale': kwargs.pop('svg_scale', 1.0),
        }
        entity_defaults.update(kwargs)
        entity = Entity.objects.create(**entity_defaults)
        
        # Create position
        EntityPosition.objects.create(
            entity=entity,
            location=location,
            **position_kwargs
        )
        return entity
    
    @staticmethod
    def create_test_collection_with_position(location: Optional[Location] = None, **kwargs) -> Collection:
        """Create a test collection with position on a location."""
        if location is None:
            location = LocationSyntheticData.create_test_location()
            
        unique_id = str(uuid.uuid4())[:8]
        collection_defaults = {
            'name': f'Test Collection {unique_id}',
            'collection_type_str': str(CollectionType.OTHER),
            'collection_view_type_str': str(CollectionViewType.LIST),
        }
        # Extract position-specific kwargs
        position_kwargs = {
            'svg_x': kwargs.pop('svg_x', 200.0),
            'svg_y': kwargs.pop('svg_y', 200.0), 
            'svg_rotate': kwargs.pop('svg_rotate', 0.0),
            'svg_scale': kwargs.pop('svg_scale', 1.0),
        }
        collection_defaults.update(kwargs)
        collection = Collection.objects.create(**collection_defaults)
        
        # Create position
        CollectionPosition.objects.create(
            collection=collection,
            location=location,
            **position_kwargs
        )
        return collection
