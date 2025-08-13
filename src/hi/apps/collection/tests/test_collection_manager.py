import logging
from decimal import Decimal
from unittest.mock import Mock, patch

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection, CollectionEntity, CollectionPosition, CollectionView
from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestCollectionManager(BaseTestCase):

    def test_collection_manager_singleton_behavior(self):
        """Test CollectionManager singleton pattern - critical for system consistency."""
        manager1 = CollectionManager()
        manager2 = CollectionManager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)
        return

    def test_get_collection_with_cached_collection(self):
        """Test get_collection with cached collection - critical for performance."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Mock request with cached collection
        mock_request = Mock()
        mock_request.view_parameters.collection = collection
        
        manager = CollectionManager()
        result = manager.get_collection(mock_request, collection.id)
        
        # Should return cached collection
        self.assertEqual(result, collection)
        return

    def test_get_collection_with_database_lookup(self):
        """Test get_collection with database lookup - critical for data retrieval."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Mock request without cached collection
        mock_request = Mock()
        mock_request.view_parameters.collection = None
        
        manager = CollectionManager()
        result = manager.get_collection(mock_request, collection.id)
        
        # Should return collection from database
        self.assertEqual(result, collection)
        return

    def test_get_default_collection_with_cached_collection(self):
        """Test get_default_collection with cached collection - performance optimization."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Mock request with cached collection
        mock_request = Mock()
        mock_request.view_parameters.collection = collection
        
        manager = CollectionManager()
        result = manager.get_default_collection(mock_request)
        
        # Should return cached collection
        self.assertEqual(result, collection)
        return

    def test_get_default_collection_with_database_fallback(self):
        """Test get_default_collection with database fallback - critical for system initialization."""
        collection = Collection.objects.create(
            name='Default Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID',
            order_id=1
        )
        
        # Mock request without cached collection
        mock_request = Mock()
        mock_request.view_parameters.collection = None
        
        manager = CollectionManager()
        result = manager.get_default_collection(mock_request)
        
        # Should return first collection by order_id
        self.assertEqual(result, collection)
        return

    def test_get_default_collection_no_collections_exist(self):
        """Test get_default_collection when no collections exist - error handling."""
        # Mock request without cached collection
        mock_request = Mock()
        mock_request.view_parameters.collection = None
        
        manager = CollectionManager()
        
        # Should raise DoesNotExist when no collections
        with self.assertRaises(Collection.DoesNotExist):
            manager.get_default_collection(mock_request)
        return

    def test_create_collection_entity_with_order_calculation(self):
        """Test create_collection_entity with order calculation - complex ordering logic."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        # Create existing entity with order_id=5
        existing_entity = Entity.objects.create(
            name='Existing Entity',
            entity_type_str='LIGHT'
        )
        CollectionEntity.objects.create(
            collection=collection,
            entity=existing_entity,
            order_id=5
        )
        
        manager = CollectionManager()
        result = manager.create_collection_entity(entity, collection)
        
        # Should create with next order_id
        self.assertEqual(result.entity, entity)
        self.assertEqual(result.collection, collection)
        self.assertEqual(result.order_id, 6)  # 5 + 1
        return

    def test_create_collection_entity_first_entity(self):
        """Test create_collection_entity for first entity - initialization logic."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        manager = CollectionManager()
        result = manager.create_collection_entity(entity, collection)
        
        # Should create with order_id=0 for first entity
        self.assertEqual(result.order_id, 0)
        return

    def test_remove_collection_entity_exists(self):
        """Test remove_collection_entity when entity exists - successful removal."""
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
        
        manager = CollectionManager()
        result = manager.remove_collection_entity(entity, collection)
        
        # Should return True and delete the entity
        self.assertTrue(result)
        self.assertFalse(CollectionEntity.objects.filter(id=collection_entity.id).exists())
        return

    def test_remove_collection_entity_not_exists(self):
        """Test remove_collection_entity when entity doesn't exist - error handling."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        
        manager = CollectionManager()
        result = manager.remove_collection_entity(entity, collection)
        
        # Should return False when entity doesn't exist in collection
        self.assertFalse(result)
        return

    def test_toggle_collection_in_view_add_to_view(self):
        """Test toggle_collection_in_view adding collection - complex toggle logic."""
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
        
        manager = CollectionManager()
        
        # Mock the create_collection_view method to avoid complex SVG item logic
        with patch.object(manager, 'create_collection_view') as mock_create:
            mock_collection_view = Mock()
            mock_create.return_value = mock_collection_view
            
            result = manager.toggle_collection_in_view(collection, location_view)
            
            # Should return True (added) and call create_collection_view
            self.assertTrue(result)
            mock_create.assert_called_once_with(
                collection=collection,
                location_view=location_view
            )
        return

    def test_toggle_collection_in_view_remove_from_view(self):
        """Test toggle_collection_in_view removing collection - complex toggle logic."""
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
        
        # Create existing collection view
        CollectionView.objects.create(
            collection=collection,
            location_view=location_view
        )
        
        manager = CollectionManager()
        result = manager.toggle_collection_in_view(collection, location_view)
        
        # Should return False (removed) and delete the collection view
        self.assertFalse(result)
        self.assertFalse(CollectionView.objects.filter(
            collection=collection,
            location_view=location_view
        ).exists())
        return

    def test_set_collection_entity_order_batch_update(self):
        """Test set_collection_entity_order batch update - complex ordering logic."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Create entities in different order
        entity1 = Entity.objects.create(name='Entity 1', entity_type_str='CAMERA')
        entity2 = Entity.objects.create(name='Entity 2', entity_type_str='LIGHT')
        entity3 = Entity.objects.create(name='Entity 3', entity_type_str='SENSOR')
        
        ce1 = CollectionEntity.objects.create(collection=collection, entity=entity1, order_id=1)
        ce2 = CollectionEntity.objects.create(collection=collection, entity=entity2, order_id=2)
        ce3 = CollectionEntity.objects.create(collection=collection, entity=entity3, order_id=3)
        
        # Reorder: entity3, entity1, entity2
        entity_id_list = [entity3.id, entity1.id, entity2.id]
        
        manager = CollectionManager()
        manager.set_collection_entity_order(collection, entity_id_list)
        
        # Check new order (with gaps: 2, 4, 6)
        ce1.refresh_from_db()
        ce2.refresh_from_db()
        ce3.refresh_from_db()
        
        self.assertEqual(ce3.order_id, 2)  # First in new order
        self.assertEqual(ce1.order_id, 4)  # Second in new order
        self.assertEqual(ce2.order_id, 6)  # Third in new order
        return

    def test_add_collection_position_if_needed_creates_position(self):
        """Test add_collection_position_if_needed creating position - complex geometry calculation."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='10 20 100 200'  # x=10, y=20, width=100, height=200
        )
        
        location_view = LocationView.objects.create(
            location=location,
            location_view_type_str='DEFAULT',
            name='Test View',
            svg_view_box_str='10 20 100 200',
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )
        
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        manager = CollectionManager()
        result = manager.add_collection_position_if_needed(collection, location_view)
        
        # Should create position at center of view box
        self.assertIsNotNone(result)
        self.assertEqual(result.collection, collection)
        self.assertEqual(result.location, location)
        
        # Center calculation: x + width/2 = 10 + 100/2 = 60
        # Center calculation: y + height/2 = 20 + 200/2 = 120
        self.assertEqual(result.svg_x, Decimal('60'))
        self.assertEqual(result.svg_y, Decimal('120'))
        self.assertEqual(result.svg_scale, Decimal('1.0'))
        self.assertEqual(result.svg_rotate, Decimal('0.0'))
        return

    def test_add_collection_position_if_needed_position_exists(self):
        """Test add_collection_position_if_needed when position exists - no-op behavior."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        location_view = LocationView.objects.create(
            location=location,
            location_view_type_str='DEFAULT',
            name='Test View',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )
        
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Create existing position
        existing_position = CollectionPosition.objects.create(
            location=location,
            collection=collection,
            svg_x=25.0,
            svg_y=25.0,
            svg_scale=1.0,
            svg_rotate=0.0
        )
        
        manager = CollectionManager()
        result = manager.add_collection_position_if_needed(collection, location_view)
        
        # Should return None (no-op) when position already exists
        self.assertIsNone(result)
        
        # Existing position should be unchanged
        existing_position.refresh_from_db()
        self.assertEqual(existing_position.svg_x, Decimal('25.0'))
        return
