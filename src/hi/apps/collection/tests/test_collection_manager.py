import logging
from decimal import Decimal
from unittest.mock import Mock

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection, CollectionEntity, CollectionPosition, CollectionView, CollectionPath
from hi.apps.entity.models import Entity
from hi.apps.entity.enums import EntityGroupType
from hi.apps.location.models import Location, LocationView
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestCollectionManagerIntegration(BaseTestCase):
    """Integration tests for CollectionManager complex business workflows."""

    def test_collection_data_generation_includes_entity_status_and_svg_icons(self):
        """Test get_collection_data integration - combines entities, status, and display data."""
        collection = Collection.objects.create(
            name='Test Collection', collection_type_str='CAMERAS',
            collection_view_type_str='GRID'
        )
        
        # Create entities with different types
        camera = Entity.objects.create(name='Security Camera', entity_type_str='CAMERA')
        light = Entity.objects.create(name='Porch Light', entity_type_str='LIGHT')
        
        # Add entities to collection with specific order
        CollectionEntity.objects.create(collection=collection, entity=camera, order_id=1)
        CollectionEntity.objects.create(collection=collection, entity=light, order_id=2)
        
        manager = CollectionManager()
        collection_data = manager.get_collection_data(collection, is_editing=False)
        
        # Verify collection data structure
        self.assertEqual(collection_data.collection, collection)
        self.assertEqual(len(collection_data.entity_status_data_list), 2)
        
        # Verify entities are ordered correctly
        entity_names = [esd.entity.name for esd in collection_data.entity_status_data_list]
        self.assertEqual(entity_names, ['Security Camera', 'Porch Light'])
        
        # Verify each entity has status data and SVG icon
        for entity_status_data in collection_data.entity_status_data_list:
            self.assertIsNotNone(entity_status_data.entity)
            self.assertIsNotNone(entity_status_data.display_only_svg_icon_item)
            # SVG icon should be configured for display
            self.assertIsNotNone(entity_status_data.display_only_svg_icon_item.template_name)

    def test_entity_collection_group_organization_by_type(self):
        """Test create_entity_collection_group_list organization - groups entities by type."""
        collection = Collection.objects.create(
            name='Mixed Collection', collection_type_str='OTHER',
            collection_view_type_str='LIST'
        )
        
        # Create entities of different types
        camera1 = Entity.objects.create(name='Front Camera', entity_type_str='CAMERA')
        Entity.objects.create(name='Back Camera', entity_type_str='CAMERA')
        light1 = Entity.objects.create(name='Living Room Light', entity_type_str='LIGHT')
        Entity.objects.create(name='Motion Sensor', entity_type_str='SENSOR')
        
        # Add some entities to collection, leave others available
        CollectionEntity.objects.create(collection=collection, entity=camera1)
        CollectionEntity.objects.create(collection=collection, entity=light1)
        
        manager = CollectionManager()
        groups = manager.create_entity_collection_group_list(collection)
        
        # Should have groups for each entity type present in system
        group_types = {group.entity_group_type for group in groups}
        self.assertIn(EntityGroupType.SECURITY, group_types)  # Contains cameras
        self.assertIn(EntityGroupType.LIGHTS_SWITCHES, group_types)  # Contains lights
        
        # Find security group (contains cameras) and verify contents
        camera_group = next(g for g in groups if g.entity_group_type == EntityGroupType.SECURITY)
        camera_items = {item.entity.name: item.exists_in_collection for item in camera_group.item_list}
        
        self.assertEqual(len(camera_items), 2)
        self.assertTrue(camera_items['Front Camera'])  # In collection
        self.assertFalse(camera_items['Back Camera'])  # Not in collection
        
        # Find light group and verify contents
        light_group = next(g for g in groups if g.entity_group_type == EntityGroupType.LIGHTS_SWITCHES)
        self.assertEqual(len(light_group.item_list), 1)
        self.assertTrue(light_group.item_list[0].exists_in_collection)
        
        # Verify groups are sorted by label for consistent UI
        group_labels = [group.entity_group_type.label for group in groups]
        self.assertEqual(group_labels, sorted(group_labels))


class TestCollectionManager(BaseTestCase):

    def test_collection_manager_singleton_behavior(self):
        """Test CollectionManager singleton pattern - critical for system consistency."""
        manager1 = CollectionManager()
        manager2 = CollectionManager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)
        return

    def test_get_collection_returns_cached_when_ids_match(self):
        """Test get_collection cache optimization - prevents unnecessary database queries."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        mock_request = Mock()
        mock_request.view_parameters.collection = collection
        
        manager = CollectionManager()
        
        # Should return cached instance without database lookup
        with self.assertNumQueries(0):
            result = manager.get_collection(mock_request, collection.id)
            
        self.assertIs(result, collection)  # Same instance, not just equal

    def test_get_collection_performs_database_lookup_when_no_cache(self):
        """Test get_collection database fallback - ensures data consistency."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        mock_request = Mock()
        mock_request.view_parameters.collection = None
        
        manager = CollectionManager()
        
        # Should perform database lookup when no cache
        with self.assertNumQueries(1):
            result = manager.get_collection(mock_request, collection.id)
            
        self.assertEqual(result.id, collection.id)
        self.assertEqual(result.name, 'Test Collection')

    def test_get_default_collection_returns_cached_instance(self):
        """Test get_default_collection cache behavior - performance optimization."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        mock_request = Mock()
        mock_request.view_parameters.collection = collection
        
        manager = CollectionManager()
        
        # Should return cached instance without database access
        with self.assertNumQueries(0):
            result = manager.get_default_collection(mock_request)
            
        self.assertIs(result, collection)

    def test_get_default_collection_returns_lowest_order_id(self):
        """Test get_default_collection ordering logic - critical for UI consistency."""
        # Create collections in different order
        Collection.objects.create(
            name='Third Collection', collection_type_str='OTHER',
            collection_view_type_str='GRID', order_id=3
        )
        collection1 = Collection.objects.create(
            name='First Collection', collection_type_str='OTHER',
            collection_view_type_str='GRID', order_id=1
        )
        Collection.objects.create(
            name='Second Collection', collection_type_str='OTHER',
            collection_view_type_str='GRID', order_id=2
        )
        
        mock_request = Mock()
        mock_request.view_parameters.collection = None
        
        manager = CollectionManager()
        result = manager.get_default_collection(mock_request)
        
        # Should return collection with lowest order_id regardless of creation order
        self.assertEqual(result.id, collection1.id)
        self.assertEqual(result.order_id, 1)

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

    def test_toggle_collection_in_view_adds_collection_and_creates_position(self):
        """Test toggle_collection_in_view creation behavior - creates view relationship and position."""
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
        result = manager.toggle_collection_in_view(collection, location_view)
        
        # Should return True (added) and create database relationships
        self.assertTrue(result)
        
        # Verify CollectionView was created
        collection_view = CollectionView.objects.filter(
            collection=collection, location_view=location_view
        ).first()
        self.assertIsNotNone(collection_view)
        
        # Verify collection has visual representation (position or path)
        has_position = CollectionPosition.objects.filter(
            collection=collection, location=location
        ).exists()
        has_path = CollectionPath.objects.filter(
            collection=collection, location=location
        ).exists()
        
        # Collection should have either position or path for visual display
        self.assertTrue(has_position or has_path,
                        "Collection should have either position or path for visual representation")

    def test_toggle_collection_in_view_removes_existing_collection_view(self):
        """Test toggle_collection_in_view removal behavior - removes view relationship."""
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
        existing_view = CollectionView.objects.create(
            collection=collection,
            location_view=location_view
        )
        
        manager = CollectionManager()
        result = manager.toggle_collection_in_view(collection, location_view)
        
        # Should return False (removed) and delete the collection view
        self.assertFalse(result)
        self.assertFalse(CollectionView.objects.filter(
            id=existing_view.id
        ).exists())

    def test_set_collection_entity_order_preserves_entity_display_sequence(self):
        """Test set_collection_entity_order reordering - critical for UI entity sequence."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Create entities with initial order
        entity1 = Entity.objects.create(name='Camera', entity_type_str='CAMERA')
        entity2 = Entity.objects.create(name='Light', entity_type_str='LIGHT')
        entity3 = Entity.objects.create(name='Sensor', entity_type_str='SENSOR')
        
        ce1 = CollectionEntity.objects.create(collection=collection, entity=entity1, order_id=1)
        ce2 = CollectionEntity.objects.create(collection=collection, entity=entity2, order_id=2)
        ce3 = CollectionEntity.objects.create(collection=collection, entity=entity3, order_id=3)
        
        # Reorder: Sensor, Camera, Light
        new_order = [entity3.id, entity1.id, entity2.id]
        
        manager = CollectionManager()
        manager.set_collection_entity_order(collection, new_order)
        
        # Verify entities are now returned in the specified order
        ordered_entities = list(collection.entities.order_by('order_id'))
        entity_names = [ce.entity.name for ce in ordered_entities]
        
        self.assertEqual(entity_names, ['Sensor', 'Camera', 'Light'])
        
        # Verify order_ids are sequential with gaps for future insertions
        ce1.refresh_from_db()
        ce2.refresh_from_db()
        ce3.refresh_from_db()
        
        self.assertEqual(ce3.order_id, 2)  # Sensor first
        self.assertEqual(ce1.order_id, 4)  # Camera second
        self.assertEqual(ce2.order_id, 6)  # Light third

    def test_add_collection_position_if_needed_calculates_view_center(self):
        """Test add_collection_position_if_needed geometry calculation - centers collection in view."""
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
        
        # Should create position at view center for optimal default placement
        self.assertIsNotNone(result)
        self.assertEqual(result.collection, collection)
        self.assertEqual(result.location, location)
        
        # Verify center calculation: x + width/2 = 10 + 100/2 = 60
        self.assertEqual(result.svg_x, Decimal('60'))
        # Verify center calculation: y + height/2 = 20 + 200/2 = 120
        self.assertEqual(result.svg_y, Decimal('120'))
        
        # Verify default transform values for new positions
        self.assertEqual(result.svg_scale, Decimal('1.0'))
        self.assertEqual(result.svg_rotate, Decimal('0.0'))

    def test_add_collection_position_if_needed_preserves_existing_position(self):
        """Test add_collection_position_if_needed idempotency - preserves custom positioning."""
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
        
        # Create existing position with custom coordinates
        existing_position = CollectionPosition.objects.create(
            location=location,
            collection=collection,
            svg_x=25.0,
            svg_y=75.0,  # Custom Y position
            svg_scale=1.5,  # Custom scale
            svg_rotate=45.0  # Custom rotation
        )
        
        manager = CollectionManager()
        result = manager.add_collection_position_if_needed(collection, location_view)
        
        # Should return None and not create duplicate position
        self.assertIsNone(result)
        
        # Verify existing position is completely unchanged
        existing_position.refresh_from_db()
        self.assertEqual(existing_position.svg_x, Decimal('25.0'))
        self.assertEqual(existing_position.svg_y, Decimal('75.0'))
        self.assertEqual(existing_position.svg_scale, Decimal('1.5'))
        self.assertEqual(existing_position.svg_rotate, Decimal('45.0'))
        
        # Verify only one position exists for this collection-location pair
        position_count = CollectionPosition.objects.filter(
            location=location, collection=collection
        ).count()
        self.assertEqual(position_count, 1)

    def test_create_collection_entity_maintains_global_order_sequence(self):
        """Test create_collection_entity order calculation across multiple collections."""
        collection1 = Collection.objects.create(
            name='Collection 1', collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        collection2 = Collection.objects.create(
            name='Collection 2', collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        entity1 = Entity.objects.create(name='Entity 1', entity_type_str='CAMERA')
        entity2 = Entity.objects.create(name='Entity 2', entity_type_str='LIGHT')
        entity3 = Entity.objects.create(name='Entity 3', entity_type_str='SENSOR')
        
        manager = CollectionManager()
        
        # Add entities to different collections to test global ordering
        ce1 = manager.create_collection_entity(entity1, collection1)
        ce2 = manager.create_collection_entity(entity2, collection2)
        ce3 = manager.create_collection_entity(entity3, collection1)
        
        # Should maintain global sequence across all collections
        self.assertEqual(ce1.order_id, 0)  # First entity overall
        self.assertEqual(ce2.order_id, 1)  # Second entity overall
        self.assertEqual(ce3.order_id, 2)  # Third entity overall
        
        # Verify entities are properly associated with their collections
        self.assertEqual(ce1.collection, collection1)
        self.assertEqual(ce2.collection, collection2)
        self.assertEqual(ce3.collection, collection1)

    def test_toggle_entity_in_collection_handles_bidirectional_state(self):
        """Test toggle_entity_in_collection complete add/remove cycle."""
        collection = Collection.objects.create(
            name='Test Collection', collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        entity = Entity.objects.create(name='Test Entity', entity_type_str='CAMERA')
        
        manager = CollectionManager()
        
        # Initial state: entity not in collection
        self.assertFalse(CollectionEntity.objects.filter(
            entity=entity, collection=collection
        ).exists())
        
        # First toggle: add entity
        result1 = manager.toggle_entity_in_collection(entity, collection)
        self.assertTrue(result1)  # Returns True for addition
        self.assertTrue(CollectionEntity.objects.filter(
            entity=entity, collection=collection
        ).exists())
        
        # Second toggle: remove entity
        result2 = manager.toggle_entity_in_collection(entity, collection)
        self.assertFalse(result2)  # Returns False for removal
        self.assertFalse(CollectionEntity.objects.filter(
            entity=entity, collection=collection
        ).exists())
        
        # Third toggle: add again to verify repeatable behavior
        result3 = manager.toggle_entity_in_collection(entity, collection)
        self.assertTrue(result3)
        self.assertTrue(CollectionEntity.objects.filter(
            entity=entity, collection=collection
        ).exists())
