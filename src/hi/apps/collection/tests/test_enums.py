import logging

from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.collection.models import Collection
from hi.testing.base_test_case import BaseTestCase

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
        self.assertTrue(grid_collection.collection_view_type.is_grid)
        self.assertFalse(grid_collection.collection_view_type.is_list)
        
        # LIST type should enable list-specific UI features
        self.assertFalse(list_collection.collection_view_type.is_grid)
        self.assertTrue(list_collection.collection_view_type.is_list)
        
        # Verify view types persist correctly in database
        grid_collection.refresh_from_db()
        list_collection.refresh_from_db()
        self.assertTrue(grid_collection.collection_view_type.is_grid)
        self.assertTrue(list_collection.collection_view_type.is_list)

    def test_each_view_type_has_exactly_one_classification(self):
        """Every CollectionViewType value must classify as exactly one
        of the is_* properties so consumers can dispatch on a single
        property without ambiguity."""
        for view_type in CollectionViewType:
            classifications = [
                view_type.is_default,
                view_type.is_grid,
                view_type.is_grid_large,
                view_type.is_grid_small,
                view_type.is_list,
                view_type.is_security,
            ]
            true_count = sum( 1 for c in classifications if c )
            self.assertEqual(
                true_count, 1,
                f'{view_type} has {true_count} true classifications; expected exactly 1',
            )

    def test_default_view_type_is_classified(self):
        collection = Collection.objects.create(
            name = 'Info Index', collection_type_str = 'OTHER',
            collection_view_type_str = 'DEFAULT',
        )
        self.assertTrue( collection.collection_view_type.is_default )
        self.assertFalse( collection.collection_view_type.is_grid )
        self.assertFalse( collection.collection_view_type.is_list )
        self.assertFalse( collection.collection_view_type.is_security )

    def test_security_view_type_is_classified(self):
        collection = Collection.objects.create(
            name = 'Camera Watch', collection_type_str = 'CAMERAS',
            collection_view_type_str = 'SECURITY',
        )
        self.assertTrue( collection.collection_view_type.is_security )
        self.assertFalse( collection.collection_view_type.is_default )
        self.assertFalse( collection.collection_view_type.is_grid )
        self.assertFalse( collection.collection_view_type.is_list )
