"""
Synthetic data generators for Collection testing.

Provides centralized, reusable test data creation following the project's
synthetic data pattern documented in test-data-management.md.
"""
import uuid

from hi.apps.collection.models import Collection
from hi.apps.collection.enums import CollectionType, CollectionViewType


class CollectionSyntheticData:
    """Centralized synthetic data generators for collection testing."""
    
    @staticmethod
    def create_test_collection(**kwargs) -> Collection:
        """Create a test collection with reasonable defaults."""
        unique_id = str(uuid.uuid4())[:8]
        defaults = {
            'name': f'Test Collection {unique_id}',
            'collection_type_str': str(CollectionType.OTHER),
            'collection_view_type_str': str(CollectionViewType.GRID),
        }
        defaults.update(kwargs)
        return Collection.objects.create(**defaults)
    
