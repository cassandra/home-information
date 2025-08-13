import logging

from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestCollectionType(BaseTestCase):

    def test_collection_type_default_fallback(self):
        """Test CollectionType default fallback - critical for initialization."""
        self.assertEqual(CollectionType.default(), CollectionType.OTHER)
        return


class TestCollectionViewType(BaseTestCase):

    def test_collection_view_type_classification_logic(self):
        """Test CollectionViewType classification methods - critical for UI logic."""
        # GRID type
        self.assertTrue(CollectionViewType.GRID.is_grid())
        self.assertFalse(CollectionViewType.GRID.is_list())
        
        # LIST type
        self.assertFalse(CollectionViewType.LIST.is_grid())
        self.assertTrue(CollectionViewType.LIST.is_list())
        return

    def test_collection_view_type_mutual_exclusivity(self):
        """Test view type mutual exclusivity - critical for business logic."""
        for view_type in CollectionViewType:
            # Each type should be either grid or list, but not both
            is_grid = view_type.is_grid()
            is_list = view_type.is_list()
            self.assertTrue(is_grid or is_list, f"{view_type} is neither grid nor list")
            self.assertFalse(is_grid and is_list, f"{view_type} is both grid and list")
        return
