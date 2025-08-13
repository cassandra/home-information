import logging
from django.db import IntegrityError

from hi.apps.collection.models import Collection, CollectionEntity, CollectionPosition, CollectionPath, CollectionView
from hi.apps.collection.enums import CollectionType, CollectionViewType
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView
from hi.enums import ItemType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestCollection(BaseTestCase):

    def test_collection_enum_property_conversions(self):
        """Test Collection enum property conversions - custom business logic."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='CAMERAS',
            collection_view_type_str='GRID'
        )
        
        # Test getter converts string to enum
        self.assertEqual(collection.collection_type, CollectionType.CAMERAS)
        self.assertEqual(collection.collection_view_type, CollectionViewType.GRID)
        
        # Test setter converts enum to string
        collection.collection_type = CollectionType.TOOLS
        collection.collection_view_type = CollectionViewType.LIST
        self.assertEqual(collection.collection_type_str, 'tools')
        self.assertEqual(collection.collection_view_type_str, 'list')
        return

    def test_collection_item_type_property(self):
        """Test item_type property - critical for type system integration."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        self.assertEqual(collection.item_type, ItemType.COLLECTION)
        return

    def test_collection_ordering_by_order_id(self):
        """Test Collection ordering - critical for UI display order."""
        # Create collections with different order_ids
        collection1 = Collection.objects.create(
            name='First Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID',
            order_id=2
        )
        collection2 = Collection.objects.create(
            name='Second Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID',
            order_id=1
        )
        collection3 = Collection.objects.create(
            name='Third Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID',
            order_id=3
        )
        
        # Should be ordered by order_id
        collections = list(Collection.objects.all())
        self.assertEqual(collections[0], collection2)  # order_id=1
        self.assertEqual(collections[1], collection1)  # order_id=2
        self.assertEqual(collections[2], collection3)  # order_id=3
        return


class TestCollectionEntity(BaseTestCase):

    def test_collection_entity_ordering_by_order_id(self):
        """Test CollectionEntity ordering - critical for entity display order."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        entity1 = Entity.objects.create(
            name='Entity 1',
            entity_type_str='CAMERA'
        )
        entity2 = Entity.objects.create(
            name='Entity 2',
            entity_type_str='LIGHT'
        )
        
        # Create collection entities with specific order
        ce1 = CollectionEntity.objects.create(
            collection=collection,
            entity=entity1,
            order_id=2
        )
        ce2 = CollectionEntity.objects.create(
            collection=collection,
            entity=entity2,
            order_id=1
        )
        
        # Should be ordered by order_id
        collection_entities = list(CollectionEntity.objects.filter(collection=collection))
        self.assertEqual(collection_entities[0], ce2)  # order_id=1
        self.assertEqual(collection_entities[1], ce1)  # order_id=2
        return

    def test_collection_entity_cascade_deletion_from_collection(self):
        """Test cascade deletion from collection - critical for data integrity."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        collection_entity = CollectionEntity.objects.create(
            collection=collection,
            entity=entity
        )
        
        ce_id = collection_entity.id
        
        # Delete collection should cascade to collection entities
        collection.delete()
        
        self.assertFalse(CollectionEntity.objects.filter(id=ce_id).exists())
        return

    def test_collection_entity_cascade_deletion_from_entity(self):
        """Test cascade deletion from entity - critical for data integrity."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        collection_entity = CollectionEntity.objects.create(
            collection=collection,
            entity=entity
        )
        
        ce_id = collection_entity.id
        
        # Delete entity should cascade to collection entities
        entity.delete()
        
        self.assertFalse(CollectionEntity.objects.filter(id=ce_id).exists())
        return

    def test_collection_entity_database_indexing(self):
        """Test CollectionEntity database indexing - critical for query performance."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        collection_entity = CollectionEntity.objects.create(
            collection=collection,
            entity=entity
        )
        
        # Test that indexed query works efficiently
        # (The actual index performance isn't testable in unit tests,
        # but we can verify the fields are queryable)
        results = CollectionEntity.objects.filter(
            collection=collection,
            entity=entity
        )
        self.assertIn(collection_entity, results)
        return


class TestCollectionPosition(BaseTestCase):

    def test_collection_position_uniqueness_constraint(self):
        """Test location-collection uniqueness constraint - critical for data integrity."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Create first position
        CollectionPosition.objects.create(
            location=location,
            collection=collection,
            svg_x=10.0,
            svg_y=20.0,
            svg_scale=1.0,
            svg_rotate=0.0
        )
        
        # Duplicate location-collection should fail
        with self.assertRaises(IntegrityError):
            CollectionPosition.objects.create(
                location=location,
                collection=collection,
                svg_x=30.0,
                svg_y=40.0,
                svg_scale=1.0,
                svg_rotate=0.0
            )
        return

    def test_collection_position_location_item_property(self):
        """Test location_item property delegation - critical for interface compliance."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        position = CollectionPosition.objects.create(
            location=location,
            collection=collection,
            svg_x=10.0,
            svg_y=20.0,
            svg_scale=1.0,
            svg_rotate=0.0
        )
        
        # Should delegate to collection
        self.assertEqual(position.location_item, collection)
        return


class TestCollectionPath(BaseTestCase):

    def test_collection_path_uniqueness_constraint(self):
        """Test location-collection uniqueness constraint - critical for data integrity."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Create first path
        CollectionPath.objects.create(
            location=location,
            collection=collection,
            svg_path='M 10,10 L 50,50 Z'
        )
        
        # Duplicate location-collection should fail
        with self.assertRaises(IntegrityError):
            CollectionPath.objects.create(
                location=location,
                collection=collection,
                svg_path='M 20,20 L 60,60 Z'
            )
        return

    def test_collection_path_location_item_property(self):
        """Test location_item property delegation - critical for interface compliance."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        path = CollectionPath.objects.create(
            location=location,
            collection=collection,
            svg_path='M 10,10 L 50,50 Z'
        )
        
        # Should delegate to collection
        self.assertEqual(path.location_item, collection)
        return


class TestCollectionView(BaseTestCase):

    def test_collection_view_cascade_deletion_from_collection(self):
        """Test cascade deletion from collection - critical for data integrity."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        location_view = LocationView.objects.create(
            location=location,
            location_view_type_str='DEFAULT',
            name='Test View',
            svg_view_box_str='0 0 50 50',
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )
        
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        collection_view = CollectionView.objects.create(
            collection=collection,
            location_view=location_view
        )
        
        cv_id = collection_view.id
        
        # Delete collection should cascade to collection view
        collection.delete()
        
        self.assertFalse(CollectionView.objects.filter(id=cv_id).exists())
        return

    def test_collection_view_cascade_deletion_from_location_view(self):
        """Test cascade deletion from location view - critical for data integrity."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        location_view = LocationView.objects.create(
            location=location,
            location_view_type_str='DEFAULT',
            name='Test View',
            svg_view_box_str='0 0 50 50',
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )
        
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        collection_view = CollectionView.objects.create(
            collection=collection,
            location_view=location_view
        )
        
        cv_id = collection_view.id
        
        # Delete location view should cascade to collection view
        location_view.delete()
        
        self.assertFalse(CollectionView.objects.filter(id=cv_id).exists())
        return
