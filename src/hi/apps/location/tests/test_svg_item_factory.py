import logging
from unittest.mock import Mock, patch

from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.location.enums import SvgItemType
from hi.apps.location.models import Location, LocationView
from hi.apps.entity.models import Entity
from hi.apps.entity.enums import EntityType
from hi.apps.collection.models import Collection
from hi.apps.collection.enums import CollectionType
from hi.apps.common.svg_models import SvgIconItem, SvgPathItem
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSvgItemFactory(BaseTestCase):

    def test_svg_item_factory_singleton_behavior(self):
        """Test SvgItemFactory singleton pattern - critical for system consistency."""
        factory1 = SvgItemFactory()
        factory2 = SvgItemFactory()
        
        # Should be the same instance
        self.assertIs(factory1, factory2)
        return

    def test_get_svg_item_type_entity_classification(self):
        """Test entity SVG item type classification - critical for rendering logic."""
        factory = SvgItemFactory()
        
        # Mock entity with different types
        camera_entity = Mock(spec=Entity)
        camera_entity.entity_type = EntityType.CAMERA
        
        # Test classification logic (specific types depend on EntityStyle configuration)
        item_type = factory.get_svg_item_type(camera_entity)
        self.assertIn(item_type, [SvgItemType.ICON, SvgItemType.OPEN_PATH, SvgItemType.CLOSED_PATH])
        return

    def test_get_svg_item_type_collection_classification(self):
        """Test collection SVG item type classification - critical for rendering logic."""
        factory = SvgItemFactory()
        
        # Mock collection
        mock_collection = Mock(spec=Collection)
        mock_collection.collection_type = CollectionType.OTHER
        
        # Collections should be closed paths
        item_type = factory.get_svg_item_type(mock_collection)
        self.assertEqual(item_type, SvgItemType.CLOSED_PATH)
        return

    def test_get_svg_item_type_unknown_object(self):
        """Test unknown object classification - error handling."""
        factory = SvgItemFactory()
        
        # Unknown object should default to icon
        unknown_object = Mock()
        item_type = factory.get_svg_item_type(unknown_object)
        self.assertEqual(item_type, SvgItemType.ICON)
        return

    @patch('hi.apps.location.svg_item_factory.EntityStyle')
    def test_create_svg_icon_item_entity(self, mock_entity_style):
        """Test SVG icon item creation for entities - complex rendering logic."""
        factory = SvgItemFactory()
        
        # Mock dependencies
        mock_entity_style.get_svg_icon_template_name.return_value = 'entity/icons/camera.html'
        mock_entity_style.get_svg_icon_viewbox.return_value = Mock(width=24, height=24)
        
        # Mock entity and position
        entity = Mock(spec=Entity)
        entity.entity_type = EntityType.CAMERA
        entity.html_id = 'entity-123'
        
        position = Mock()
        position.svg_x = 100.0
        position.svg_y = 200.0
        position.svg_rotate = 45.0
        position.svg_scale = 1.5
        
        # Create icon item
        icon_item = factory.create_svg_icon_item(
            item=entity,
            position=position,
            css_class='entity-icon'
        )
        
        # Should create proper SvgIconItem
        self.assertIsInstance(icon_item, SvgIconItem)
        self.assertEqual(icon_item.html_id, 'entity-123')
        self.assertEqual(icon_item.css_class, 'entity-icon')
        self.assertEqual(icon_item.position_x, 100.0)
        self.assertEqual(icon_item.position_y, 200.0)
        self.assertEqual(icon_item.rotate, 45.0)
        self.assertEqual(icon_item.scale, 1.5)
        self.assertEqual(icon_item.template_name, 'entity/icons/camera.html')
        return

    @patch('hi.apps.location.svg_item_factory.EntityStyle')
    def test_create_svg_path_item_entity(self, mock_entity_style):
        """Test SVG path item creation for entities - complex rendering logic."""
        factory = SvgItemFactory()
        
        # Mock style dependencies
        mock_status_style = Mock()
        mock_status_style.stroke_color = '#ff0000'
        mock_status_style.stroke_width = 2.0
        mock_status_style.stroke_dasharray = '5,5'
        mock_status_style.fill_color = '#00ff00'
        mock_status_style.fill_opacity = 0.5
        
        mock_entity_style.get_svg_path_status_style.return_value = mock_status_style
        
        # Mock entity and path
        entity = Mock(spec=Entity)
        entity.entity_type = EntityType.MOTION_SENSOR
        entity.html_id = 'entity-456'
        
        path = Mock()
        path.svg_path = 'M 10,10 L 50,50 L 10,50 Z'
        
        # Create path item
        path_item = factory.create_svg_path_item(
            item=entity,
            path=path,
            css_class='entity-path'
        )
        
        # Should create proper SvgPathItem
        self.assertIsInstance(path_item, SvgPathItem)
        self.assertEqual(path_item.html_id, 'entity-456')
        self.assertEqual(path_item.css_class, 'entity-path')
        self.assertEqual(path_item.svg_path, 'M 10,10 L 50,50 L 10,50 Z')
        self.assertEqual(path_item.stroke_color, '#ff0000')
        self.assertEqual(path_item.stroke_width, 2.0)
        self.assertEqual(path_item.fill_color, '#00ff00')
        return

    def test_get_default_svg_path_str_closed_path(self):
        """Test default closed path generation - complex geometric calculations."""
        factory = SvgItemFactory()
        
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 200 100'
        )
        
        location_view = LocationView.objects.create(
            location=location,
            location_view_type_str='DEFAULT',
            name='Test View',
            svg_view_box_str='0 0 200 100',
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )
        
        # Generate closed path (rectangle)
        svg_path = factory.get_default_svg_path_str(
            location_view=location_view,
            is_path_closed=True
        )
        
        # Should be a rectangle path centered in viewbox
        self.assertIn('M ', svg_path)  # Move to start
        self.assertIn(' L ', svg_path)  # Line commands
        self.assertIn(' Z', svg_path)   # Close path
        
        # Should contain reasonable coordinates
        # Path should be a rectangle with move and line commands
        coordinates = svg_path.replace('M ', '').replace(' L ', ',').replace(' Z', '').split(',')
        self.assertGreater(len(coordinates), 6)  # Should have multiple coordinate pairs
        return

    def test_get_default_svg_path_str_open_path(self):
        """Test default open path generation - geometric calculations."""
        factory = SvgItemFactory()
        
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 200 100'
        )
        
        location_view = LocationView.objects.create(
            location=location,
            location_view_type_str='DEFAULT',
            name='Test View',
            svg_view_box_str='0 0 200 100',
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )
        
        # Generate open path (line)
        svg_path = factory.get_default_svg_path_str(
            location_view=location_view,
            is_path_closed=False
        )
        
        # Should be a line path
        self.assertIn('M ', svg_path)    # Move to start
        self.assertIn(' L ', svg_path)   # Line command
        self.assertNotIn(' Z', svg_path) # No close command
        
        # Should contain reasonable coordinates
        self.assertIn('50', svg_path)   # Should have center Y coordinate
        return

    def test_new_path_radius_percent_constant(self):
        """Test NEW_PATH_RADIUS_PERCENT constant - important for UI consistency."""
        factory = SvgItemFactory()
        
        # Should have reasonable default radius percentage
        self.assertEqual(factory.NEW_PATH_RADIUS_PERCENT, 5.0)
        self.assertGreater(factory.NEW_PATH_RADIUS_PERCENT, 0)
        self.assertLess(factory.NEW_PATH_RADIUS_PERCENT, 50)
        return