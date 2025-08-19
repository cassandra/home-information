from decimal import Decimal
from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.location.models import Location, LocationView
from hi.apps.common.path_geometry import PathGeometry


class TestPathGeometry(TestCase):
    """Test the PathGeometry utility class for generating default SVG paths."""

    def setUp(self):
        """Set up test data."""
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 200 100',
            order_id=1
        )
        
        self.location_view = LocationView.objects.create(
            location=self.location,
            location_view_type_str='DEFAULT',
            name='Test View',
            svg_view_box_str='0 0 200 100',  # Width=200, Height=100, Center=(100,50)
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )

    def test_get_entity_radius_configured_types(self):
        """Test entity-specific radius configurations."""
        # Test configured entity types
        appliance_radius = PathGeometry.get_entity_radius(EntityType.APPLIANCE)
        self.assertEqual(appliance_radius.x, 32)
        self.assertEqual(appliance_radius.y, 32)
        
        door_radius = PathGeometry.get_entity_radius(EntityType.DOOR)
        self.assertIsNone(door_radius.x)
        self.assertEqual(door_radius.y, 16)
        
        wall_radius = PathGeometry.get_entity_radius(EntityType.WALL)
        self.assertEqual(wall_radius.x, 16)
        self.assertIsNone(wall_radius.y)
        
        window_radius = PathGeometry.get_entity_radius(EntityType.WINDOW)
        self.assertIsNone(window_radius.x)
        self.assertEqual(window_radius.y, 16.0)
        
        furniture_radius = PathGeometry.get_entity_radius(EntityType.FURNITURE)
        self.assertEqual(furniture_radius.x, 64)
        self.assertEqual(furniture_radius.y, 32)

    def test_get_entity_radius_default(self):
        """Test default radius for unconfigured entity types."""
        other_radius = PathGeometry.get_entity_radius(EntityType.OTHER)
        self.assertIsNone(other_radius.x)
        self.assertIsNone(other_radius.y)

    def test_create_default_path_closed_no_entity_type(self):
        """Test closed path creation with default settings."""
        svg_path = PathGeometry.create_default_path_string(
            location_view=self.location_view,
            is_path_closed=True
        )
        
        # Should be a rectangle path
        self.assertIn('M ', svg_path)  # Move command
        self.assertIn(' L ', svg_path)  # Line commands  
        self.assertTrue(svg_path.endswith(' Z'))  # Close command
        
        # Should be centered at view center (100, 50)
        # Default radius: width=200*5%/50*100 = 20, height=100*5%/50*100 = 10
        expected_coords = [
            '80.0,40.0',   # top-left (100-20, 50-10)
            '120.0,40.0',  # top-right (100+20, 50-10)
            '120.0,60.0',  # bottom-right (100+20, 50+10)
            '80.0,60.0'    # bottom-left (100-20, 50+10)
        ]
        
        for coord in expected_coords:
            self.assertIn(coord, svg_path)

    def test_create_default_path_open_no_entity_type(self):
        """Test open path creation with default settings."""
        svg_path = PathGeometry.create_default_path_string(
            location_view=self.location_view,
            is_path_closed=False
        )
        
        # Should be a line path
        self.assertIn('M ', svg_path)  # Move command
        self.assertIn(' L ', svg_path)  # Line command
        self.assertNotIn(' Z', svg_path)  # No close command
        
        # Should be horizontal line centered at (100, 50)
        # Default radius_x: 200*5%/50*100 = 20
        self.assertIn('80.0,50.0', svg_path)   # start (100-20, 50)
        self.assertIn('120.0,50.0', svg_path)  # end (100+20, 50)

    def test_create_default_path_with_entity_type_door(self):
        """Test path creation with entity-specific radius (DOOR: y=16)."""
        svg_path = PathGeometry.create_default_path_string(
            location_view=self.location_view,
            is_path_closed=True,
            entity_type=EntityType.DOOR
        )
        
        # DOOR has y=16, x=None (defaults to 20)
        expected_coords = [
            '80.0,34.0',   # top-left (100-20, 50-16)  
            '120.0,34.0',  # top-right (100+20, 50-16)
            '120.0,66.0',  # bottom-right (100+20, 50+16)
            '80.0,66.0'    # bottom-left (100-20, 50+16)
        ]
        
        for coord in expected_coords:
            self.assertIn(coord, svg_path)

    def test_create_default_path_with_entity_type_wall(self):
        """Test path creation with entity-specific radius (WALL: x=16)."""
        svg_path = PathGeometry.create_default_path_string(
            location_view=self.location_view,
            is_path_closed=True,
            entity_type=EntityType.WALL
        )
        
        # WALL has x=16, y=None (defaults to 10)
        expected_coords = [
            '84.0,40.0',   # top-left (100-16, 50-10)
            '116.0,40.0',  # top-right (100+16, 50-10)
            '116.0,60.0',  # bottom-right (100+16, 50+10)
            '84.0,60.0'    # bottom-left (100-16, 50+10)
        ]
        
        for coord in expected_coords:
            self.assertIn(coord, svg_path)

    def test_create_default_path_custom_center(self):
        """Test path creation with custom center position."""
        svg_path = PathGeometry.create_default_path_string(
            location_view=self.location_view,
            is_path_closed=False,
            center_x=150.0,
            center_y=25.0
        )
        
        # Should be line centered at (150, 25)
        # Default radius_x: 20
        self.assertIn('130.0,25.0', svg_path)  # start (150-20, 25)
        self.assertIn('170.0,25.0', svg_path)  # end (150+20, 25)

    def test_create_default_path_radius_multiplier(self):
        """Test path creation with radius multiplier."""
        svg_path = PathGeometry.create_default_path_string(
            location_view=self.location_view,
            is_path_closed=True,
            radius_multiplier=2.0
        )
        
        # Default radius * 2: x=40, y=20
        expected_coords = [
            '60.0,30.0',   # top-left (100-40, 50-20)
            '140.0,30.0',  # top-right (100+40, 50-20)
            '140.0,70.0',  # bottom-right (100+40, 50+20)
            '60.0,70.0'    # bottom-left (100-40, 50+20)
        ]
        
        for coord in expected_coords:
            self.assertIn(coord, svg_path)

    def test_create_default_path_entity_type_with_multiplier(self):
        """Test path creation with entity type and radius multiplier."""
        svg_path = PathGeometry.create_default_path_string(
            location_view=self.location_view,
            is_path_closed=True,
            entity_type=EntityType.APPLIANCE,  # x=32, y=32
            radius_multiplier=0.5
        )
        
        # APPLIANCE radius * 0.5: x=16, y=16
        expected_coords = [
            '84.0,34.0',   # top-left (100-16, 50-16)
            '116.0,34.0',  # top-right (100+16, 50-16)
            '116.0,66.0',  # bottom-right (100+16, 50+16)
            '84.0,66.0'    # bottom-left (100-16, 50+16)
        ]
        
        for coord in expected_coords:
            self.assertIn(coord, svg_path)

    def test_default_radius_percent_constant(self):
        """Test the DEFAULT_RADIUS_PERCENT constant."""
        self.assertEqual(PathGeometry.DEFAULT_RADIUS_PERCENT, 5.0)
        self.assertGreater(PathGeometry.DEFAULT_RADIUS_PERCENT, 0)
        self.assertLess(PathGeometry.DEFAULT_RADIUS_PERCENT, 50)