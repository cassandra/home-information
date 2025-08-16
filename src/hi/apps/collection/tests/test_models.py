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

    def test_collection_type_change_affects_default_behavior(self):
        """Test Collection type changes impact system behavior - business logic validation."""
        collection = Collection.objects.create(
            name='Camera Collection',
            collection_type_str='CAMERAS',
            collection_view_type_str='GRID'
        )
        
        # Verify initial type
        self.assertEqual(collection.collection_type, CollectionType.CAMERAS)
        
        # Change to TOOLS type should update both enum property and string storage
        collection.collection_type = CollectionType.TOOLS
        collection.save()
        
        # Reload from database to verify persistence
        collection.refresh_from_db()
        self.assertEqual(collection.collection_type, CollectionType.TOOLS)
        self.assertEqual(collection.collection_type_str, 'tools')
        
        # Verify view type changes work similarly
        collection.collection_view_type = CollectionViewType.LIST
        collection.save()
        collection.refresh_from_db()
        self.assertEqual(collection.collection_view_type, CollectionViewType.LIST)
        self.assertEqual(collection.collection_view_type_str, 'list')

    def test_collection_integrates_with_item_type_system(self):
        """Test Collection item_type integration - enables polymorphic location item handling."""
        collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Verify collection implements location item interface
        self.assertEqual(collection.item_type, ItemType.COLLECTION)
        
        # Verify this enables polymorphic handling in location positioning
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        position = CollectionPosition.objects.create(
            location=location,
            collection=collection,
            svg_x=10.0, svg_y=20.0, svg_scale=1.0, svg_rotate=0.0
        )
        
        # location_item property should delegate to collection
        self.assertEqual(position.location_item, collection)
        self.assertEqual(position.location_item.item_type, ItemType.COLLECTION)

    def test_collection_ordering_supports_ui_drag_and_drop_resequencing(self):
        """Test Collection ordering behavior - enables dynamic UI reordering."""
        # Create collections simulating user drag-and-drop reordering
        tools = Collection.objects.create(
            name='Tools', collection_type_str='TOOLS',
            collection_view_type_str='GRID', order_id=3
        )
        cameras = Collection.objects.create(
            name='Cameras', collection_type_str='CAMERAS',
            collection_view_type_str='GRID', order_id=1
        )
        Collection.objects.create(
            name='Lights', collection_type_str='OTHER',
            collection_view_type_str='LIST', order_id=2
        )
        
        # Verify default ordering matches order_id sequence
        ordered_collections = list(Collection.objects.all())
        names = [c.name for c in ordered_collections]
        self.assertEqual(names, ['Cameras', 'Lights', 'Tools'])
        
        # Simulate reordering Tools to first position
        tools.order_id = 0
        tools.save()
        
        # Verify new ordering takes effect immediately
        reordered_collections = list(Collection.objects.all())
        new_names = [c.name for c in reordered_collections]
        self.assertEqual(new_names, ['Tools', 'Cameras', 'Lights'])
        
        # Verify ordering is stable across different collection types
        cameras.order_id = 5
        cameras.save()
        final_collections = list(Collection.objects.all())
        final_names = [c.name for c in final_collections]
        self.assertEqual(final_names, ['Tools', 'Lights', 'Cameras'])


class TestCollectionEntity(BaseTestCase):

    def test_collection_entity_ordering_preserves_user_arrangement(self):
        """Test CollectionEntity ordering persistence - maintains user-defined entity sequence."""
        collection = Collection.objects.create(
            name='Security System',
            collection_type_str='CAMERAS',
            collection_view_type_str='GRID'
        )
        
        # Create entities representing physical layout order
        front_door = Entity.objects.create(name='Front Door Camera', entity_type_str='CAMERA')
        garage = Entity.objects.create(name='Garage Camera', entity_type_str='CAMERA')
        backyard = Entity.objects.create(name='Backyard Camera', entity_type_str='CAMERA')
        
        # User arranges cameras in specific order: garage, backyard, front_door
        CollectionEntity.objects.create(collection=collection, entity=garage, order_id=1)
        CollectionEntity.objects.create(collection=collection, entity=backyard, order_id=2)
        CollectionEntity.objects.create(collection=collection, entity=front_door, order_id=3)
        
        # Verify entities maintain user-specified order through collection relationship
        ordered_entities = collection.entities.order_by('order_id')
        entity_names = [ce.entity.name for ce in ordered_entities]
        self.assertEqual(entity_names, [
            'Garage Camera', 'Backyard Camera', 'Front Door Camera'
        ])
        
        # Test order persistence across app restarts (database reload)
        collection.refresh_from_db()
        reloaded_entities = collection.entities.order_by('order_id')
        reloaded_names = [ce.entity.name for ce in reloaded_entities]
        self.assertEqual(reloaded_names, entity_names)

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

    def test_collection_entity_efficient_membership_queries(self):
        """Test CollectionEntity query optimization - supports fast membership checks."""
        cameras = Collection.objects.create(
            name='Cameras', collection_type_str='CAMERAS',
            collection_view_type_str='GRID'
        )
        lights = Collection.objects.create(
            name='Lights', collection_type_str='LIGHTS',
            collection_view_type_str='LIST'
        )
        
        # Create entities in both collections
        outdoor_cam = Entity.objects.create(name='Outdoor Camera', entity_type_str='CAMERA')
        indoor_cam = Entity.objects.create(name='Indoor Camera', entity_type_str='CAMERA')
        porch_light = Entity.objects.create(name='Porch Light', entity_type_str='LIGHT')
        
        CollectionEntity.objects.create(collection=cameras, entity=outdoor_cam)
        CollectionEntity.objects.create(collection=cameras, entity=indoor_cam)
        CollectionEntity.objects.create(collection=lights, entity=porch_light)
        
        # Test efficient membership queries that UI depends on
        camera_entities = CollectionEntity.objects.filter(collection=cameras)
        self.assertEqual(camera_entities.count(), 2)
        
        camera_entity_names = set(ce.entity.name for ce in camera_entities)
        self.assertEqual(camera_entity_names, {'Outdoor Camera', 'Indoor Camera'})
        
        # Test cross-collection entity queries
        outdoor_cam_collections = CollectionEntity.objects.filter(entity=outdoor_cam)
        self.assertEqual(outdoor_cam_collections.count(), 1)
        self.assertEqual(outdoor_cam_collections.first().collection, cameras)
        
        # Test that entity can be efficiently checked against multiple collections
        all_collections = Collection.objects.all()
        for collection in all_collections:
            entity_exists = CollectionEntity.objects.filter(
                collection=collection, entity=porch_light
            ).exists()
            if collection == lights:
                self.assertTrue(entity_exists)
            else:
                self.assertFalse(entity_exists)


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

    def test_collection_position_enables_polymorphic_svg_rendering(self):
        """Test CollectionPosition location_item delegation - supports unified SVG positioning."""
        location = Location.objects.create(
            name='Floor Plan',
            svg_fragment_filename='floor.svg',
            svg_view_box_str='0 0 800 600'
        )
        
        # Create collections with different visual characteristics
        cameras = Collection.objects.create(
            name='Security Cameras', collection_type_str='CAMERAS',
            collection_view_type_str='GRID'
        )
        lights = Collection.objects.create(
            name='Smart Lights', collection_type_str='OTHER',
            collection_view_type_str='LIST'
        )
        
        # Position collections at different locations
        camera_pos = CollectionPosition.objects.create(
            location=location, collection=cameras,
            svg_x=100.0, svg_y=150.0, svg_scale=1.2, svg_rotate=0.0
        )
        light_pos = CollectionPosition.objects.create(
            location=location, collection=lights,
            svg_x=300.0, svg_y=400.0, svg_scale=0.8, svg_rotate=45.0
        )
        
        # Verify polymorphic access to positioned items
        self.assertEqual(camera_pos.location_item, cameras)
        self.assertEqual(light_pos.location_item, lights)
        
        # Verify each position references correct collection type
        self.assertEqual(camera_pos.location_item.collection_type, CollectionType.CAMERAS)
        self.assertEqual(light_pos.location_item.collection_type, CollectionType.OTHER)
        
        # Test that positioning data is preserved for SVG rendering
        self.assertEqual(float(camera_pos.svg_scale), 1.2)
        self.assertEqual(float(light_pos.svg_rotate), 45.0)


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

    def test_collection_path_supports_complex_svg_shapes(self):
        """Test CollectionPath SVG path handling - enables custom collection visualizations."""
        location = Location.objects.create(
            name='Property Layout',
            svg_fragment_filename='property.svg',
            svg_view_box_str='0 0 1000 800'
        )
        
        # Create collections requiring path-based visualization
        patrol_route = Collection.objects.create(
            name='Security Patrol Route', collection_type_str='OTHER',
            collection_view_type_str='LIST'
        )
        irrigation_zone = Collection.objects.create(
            name='Garden Irrigation Zone', collection_type_str='OTHER',
            collection_view_type_str='GRID'
        )
        
        # Define complex SVG paths for different collection visualizations
        route_path = CollectionPath.objects.create(
            location=location, collection=patrol_route,
            svg_path='M 50,100 L 200,100 L 200,300 L 400,300 L 400,100 L 600,100'
        )
        zone_path = CollectionPath.objects.create(
            location=location, collection=irrigation_zone,
            svg_path='M 100,400 Q 300,350 500,400 Q 300,450 100,400 Z'
        )
        
        # Verify path delegation enables polymorphic handling
        self.assertEqual(route_path.location_item, patrol_route)
        self.assertEqual(zone_path.location_item, irrigation_zone)
        
        # Verify different path types can coexist for same location
        location_paths = CollectionPath.objects.filter(location=location)
        self.assertEqual(location_paths.count(), 2)
        
        # Verify SVG path data is preserved for rendering
        self.assertIn('M 50,100', route_path.svg_path)
        self.assertIn('Q 300,350', zone_path.svg_path)  # Quadratic curve
        self.assertTrue(zone_path.svg_path.endswith('Z'))  # Closed path


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
