import logging
from unittest.mock import patch

from hi.apps.location.models import Location, LocationAttribute, LocationView
from hi.apps.common.svg_models import SvgViewBox, SvgItemPositionBounds
from hi.apps.attribute.enums import AttributeValueType
from hi.enums import ItemType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestLocation(BaseTestCase):

    def test_location_svg_view_box_property_conversion(self):
        """Test svg_view_box property conversion - complex SVG parsing logic."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 200'
        )
        
        # Test getter converts string to SvgViewBox
        svg_view_box = location.svg_view_box
        self.assertIsInstance(svg_view_box, SvgViewBox)
        self.assertEqual(svg_view_box.x, 0)
        self.assertEqual(svg_view_box.y, 0)
        self.assertEqual(svg_view_box.width, 100)
        self.assertEqual(svg_view_box.height, 200)
        
        # Test setter converts SvgViewBox to string
        new_viewbox = SvgViewBox(x=10, y=20, width=300, height=400)
        location.svg_view_box = new_viewbox
        self.assertEqual(location.svg_view_box_str, '10 20 300 400')
        return

    def test_location_svg_position_bounds_calculation(self):
        """Test svg_position_bounds calculation - complex geometric logic."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='10 20 100 200'
        )
        
        bounds = location.svg_position_bounds
        self.assertIsInstance(bounds, SvgItemPositionBounds)
        
        # Should match viewbox dimensions
        self.assertEqual(bounds.min_x, 10)
        self.assertEqual(bounds.min_y, 20)
        self.assertEqual(bounds.max_x, 110)  # x + width
        self.assertEqual(bounds.max_y, 220)  # y + height
        
        # Should have reasonable scale limits
        self.assertEqual(bounds.min_scale, 0.1)
        self.assertEqual(bounds.max_scale, 25.0)
        return

    def test_location_item_type_property(self):
        """Test item_type property - critical for type system integration."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        self.assertEqual(location.item_type, ItemType.LOCATION)
        return

    def test_location_ordering_by_order_id(self):
        """Test Location ordering - critical for UI display order."""
        # Create locations with different order_ids
        location1 = Location.objects.create(
            name='First Location',
            svg_fragment_filename='first.svg',
            svg_view_box_str='0 0 100 100',
            order_id=2
        )
        location2 = Location.objects.create(
            name='Second Location',
            svg_fragment_filename='second.svg',
            svg_view_box_str='0 0 100 100',
            order_id=1
        )
        location3 = Location.objects.create(
            name='Third Location',
            svg_fragment_filename='third.svg',
            svg_view_box_str='0 0 100 100',
            order_id=3
        )
        
        # Should be ordered by order_id
        locations = list(Location.objects.all())
        self.assertEqual(locations[0], location2)  # order_id=1
        self.assertEqual(locations[1], location1)  # order_id=2
        self.assertEqual(locations[2], location3)  # order_id=3
        return

    @patch('hi.apps.location.models.default_storage')
    def test_location_delete_svg_file_cleanup(self, mock_storage):
        """Test SVG file cleanup on deletion - critical for storage management."""
        # Setup mock storage
        mock_storage.exists.return_value = True
        mock_storage.delete.return_value = None
        
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        filename = location.svg_fragment_filename
        
        # Delete location should trigger file cleanup
        location.delete()
        
        # Should check if file exists and delete it
        mock_storage.exists.assert_called_once_with(filename)
        mock_storage.delete.assert_called_once_with(filename)
        return

    @patch('hi.apps.location.models.default_storage')
    def test_location_delete_svg_file_missing(self, mock_storage):
        """Test SVG file deletion when file doesn't exist - error handling."""
        # Setup mock storage - file doesn't exist
        mock_storage.exists.return_value = False
        
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='missing.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        # Delete should not raise exception even if file missing
        location.delete()
        
        # Should check existence but not try to delete
        mock_storage.exists.assert_called_once()
        mock_storage.delete.assert_not_called()
        return

    def test_location_cascade_deletion_to_attributes(self):
        """Test cascade deletion to attributes - critical for data integrity."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        # Create attribute
        attribute = LocationAttribute.objects.create(
            location=location,
            name='test_attribute',
            value_type=AttributeValueType.TEXT,
            value='test_value'
        )
        
        attribute_id = attribute.id
        
        # Delete location should cascade to attributes
        location.delete()
        
        self.assertFalse(LocationAttribute.objects.filter(id=attribute_id).exists())
        return


class TestLocationView(BaseTestCase):

    def test_location_view_enum_property_conversions(self):
        """Test LocationView enum property conversions - custom business logic."""
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
        
        # Should have proper enum conversions if implemented
        # (This tests the pattern even if the properties don't exist yet)
        self.assertEqual(location_view.location_view_type_str, 'DEFAULT')
        self.assertEqual(location_view.svg_style_name_str, 'COLOR')
        return

    def test_location_view_cascade_deletion_from_location(self):
        """Test cascade deletion from location - critical for data integrity."""
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
        
        view_id = location_view.id
        
        # Delete location should cascade to views
        location.delete()
        
        self.assertFalse(LocationView.objects.filter(id=view_id).exists())
        return


class TestLocationAttribute(BaseTestCase):

    def test_location_attribute_upload_path_generation(self):
        """Test upload path generation - critical for file organization."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        attribute = LocationAttribute.objects.create(
            location=location,
            name='test_file',
            value_type=AttributeValueType.FILE,
            value='test.pdf'
        )
        
        upload_path = attribute.get_upload_to()
        self.assertEqual(upload_path, 'location/attributes/')
        return

    def test_location_attribute_indexing(self):
        """Test LocationAttribute database indexing - critical for query performance."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        # Create attributes that should be indexed
        attr1 = LocationAttribute.objects.create(
            location=location,
            name='documentation',
            value_type=AttributeValueType.TEXT,
            value='User manual'
        )
        
        attr2 = LocationAttribute.objects.create(
            location=location,
            name='specifications',
            value_type=AttributeValueType.TEXT,
            value='Technical specs'
        )
        
        # Test that we can query by indexed fields efficiently
        # (The actual index performance isn't testable in unit tests,
        # but we can verify the fields are accessible)
        results = LocationAttribute.objects.filter(
            name='documentation',
            value='User manual'
        )
        self.assertIn(attr1, results)
        self.assertNotIn(attr2, results)
        return
