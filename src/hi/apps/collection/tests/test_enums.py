import logging

from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.collection.models import Collection
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestCollectionType(BaseTestCase):

    def test_collection_type_default_ensures_system_stability(self):
        """Test CollectionType default fallback - prevents initialization failures."""
        # System should always have a valid default when no type specified
        default_type = CollectionType.default()
        self.assertEqual(default_type, CollectionType.OTHER)
        
        # Default should be usable for creating collections
        collection = Collection.objects.create(
            name='Default Type Collection',
            collection_type_str=default_type.name.lower(),
            collection_view_type_str='GRID'
        )
        self.assertEqual(collection.collection_type, CollectionType.OTHER)
        
        # Verify default type provides meaningful system behavior
        self.assertIsNotNone(default_type.name)
        self.assertIsInstance(default_type.name, str)


class TestCollectionViewType(BaseTestCase):

    def test_collection_view_type_drives_ui_rendering_behavior(self):
        """Test CollectionViewType classification impacts UI layout - critical for display logic."""
        # Create collections with different view types
        grid_collection = Collection.objects.create(
            name='Camera Grid', collection_type_str='CAMERAS',
            collection_view_type_str='GRID'
        )
        list_collection = Collection.objects.create(
            name='Sensor List', collection_type_str='SENSORS',
            collection_view_type_str='LIST'
        )
        
        # GRID type should enable grid-specific UI features
        self.assertTrue(grid_collection.collection_view_type.is_grid())
        self.assertFalse(grid_collection.collection_view_type.is_list())
        
        # LIST type should enable list-specific UI features
        self.assertFalse(list_collection.collection_view_type.is_grid())
        self.assertTrue(list_collection.collection_view_type.is_list())
        
        # Verify view types persist correctly in database
        grid_collection.refresh_from_db()
        list_collection.refresh_from_db()
        self.assertTrue(grid_collection.collection_view_type.is_grid())
        self.assertTrue(list_collection.collection_view_type.is_list())

    def test_all_collection_view_types_support_required_ui_modes(self):
        """Test CollectionViewType completeness - ensures UI can handle all types."""
        # Every view type must be classifiable as either grid or list for UI rendering
        unclassified_types = []
        ambiguous_types = []
        
        for view_type in CollectionViewType:
            is_grid = view_type.is_grid()
            is_list = view_type.is_list()
            
            # Each type must be exactly one classification
            if not (is_grid or is_list):
                unclassified_types.append(view_type)
            elif is_grid and is_list:
                ambiguous_types.append(view_type)
        
        # No view types should be unclassified or ambiguous
        self.assertEqual(unclassified_types, [],
                         f"View types missing classification: {unclassified_types}")
        self.assertEqual(ambiguous_types, [],
                         f"View types with ambiguous classification: {ambiguous_types}")
        
        # Verify we have both grid and list types available
        grid_types = [vt for vt in CollectionViewType if vt.is_grid()]
        list_types = [vt for vt in CollectionViewType if vt.is_list()]
        
        self.assertGreater(len(grid_types), 0, "No grid view types available")
        self.assertGreater(len(list_types), 0, "No list view types available")
