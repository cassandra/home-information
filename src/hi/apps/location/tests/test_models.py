import logging
from unittest.mock import patch

from hi.apps.location.models import Location, LocationAttribute, LocationView
from hi.apps.common.svg_models import SvgViewBox, SvgItemPositionBounds
from hi.apps.attribute.enums import AttributeValueType
from hi.enums import ItemType
from hi.testing.base_test_case import BaseTestCase

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

    def test_location_cascade_deletion_comprehensive(self):
        """Test comprehensive cascade deletion behavior - critical for data integrity."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        # Create multiple attributes with different types
        text_attr = LocationAttribute.objects.create(
            location=location,
            name='documentation',
            value_type_str=str(AttributeValueType.TEXT),
            value='User manual content'
        )
        file_attr = LocationAttribute.objects.create(
            location=location,
            name='specifications',
            value_type_str=str(AttributeValueType.FILE),
            value='specs.pdf'
        )
        
        # Create multiple location views
        default_view = LocationView.objects.create(
            location=location,
            location_view_type_str='DEFAULT',
            name='Default View',
            svg_view_box_str='0 0 50 50',
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )
        security_view = LocationView.objects.create(
            location=location,
            location_view_type_str='AUTOMATION',
            name='Automation View',
            svg_view_box_str='0 0 75 75',
            svg_rotate=45,
            svg_style_name_str='GREYSCALE'
        )
        
        # Store IDs for verification
        location_id = location.id
        attr_ids = [text_attr.id, file_attr.id]
        view_ids = [default_view.id, security_view.id]
        
        # Verify initial state
        self.assertEqual(LocationAttribute.objects.filter(location_id=location_id).count(), 2)
        self.assertEqual(LocationView.objects.filter(location_id=location_id).count(), 2)
        
        # Delete location should cascade to all related objects
        location.delete()
        
        # Verify complete cascade deletion
        self.assertFalse(Location.objects.filter(id=location_id).exists())
        for attr_id in attr_ids:
            self.assertFalse(LocationAttribute.objects.filter(id=attr_id).exists())
        for view_id in view_ids:
            self.assertFalse(LocationView.objects.filter(id=view_id).exists())
        return


class TestLocationView(BaseTestCase):

    def test_location_view_enum_property_conversions_complete(self):
        """Test LocationView enum property conversions - comprehensive business logic."""
        from hi.apps.location.enums import LocationViewType, SvgStyleName
        
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        location_view = LocationView.objects.create(
            location=location,
            location_view_type_str='AUTOMATION',
            name='Automation View',
            svg_view_box_str='0 0 50 50',
            svg_rotate=45,
            svg_style_name_str='GREYSCALE'
        )
        
        # Test getter conversions return proper enum objects
        view_type = location_view.location_view_type
        style_name = location_view.svg_style_name
        
        self.assertEqual(view_type, LocationViewType.AUTOMATION)
        self.assertEqual(style_name, SvgStyleName.GREYSCALE)
        self.assertEqual(view_type.label, 'Automation')
        self.assertEqual(style_name.label, 'Grey Scale ')
        
        # Test setter conversions work correctly
        location_view.location_view_type = LocationViewType.AUTOMATION
        location_view.svg_style_name = SvgStyleName.COLOR
        
        self.assertEqual(location_view.location_view_type_str, 'automation')
        self.assertEqual(location_view.svg_style_name_str, 'color')
        
        # Test that enum business logic is accessible
        automation_priorities = location_view.location_view_type.entity_state_type_priority_list
        self.assertGreater(len(automation_priorities), 0)
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
        
    def test_location_svg_viewbox_modification_persistence(self):
        """Test SVG viewbox modifications persist correctly in database."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='10 20 100 200'
        )
        
        # Modify viewbox through property
        new_viewbox = SvgViewBox(x=50, y=60, width=300, height=400)
        location.svg_view_box = new_viewbox
        location.save()
        
        # Reload from database and verify persistence
        location.refresh_from_db()
        persisted_viewbox = location.svg_view_box
        
        self.assertEqual(persisted_viewbox.x, 50)
        self.assertEqual(persisted_viewbox.y, 60)
        self.assertEqual(persisted_viewbox.width, 300)
        self.assertEqual(persisted_viewbox.height, 400)
        self.assertEqual(location.svg_view_box_str, '50 60 300 400')
        return

    def test_location_position_bounds_calculation_edge_cases(self):
        """Test position bounds calculation with edge case viewbox values."""
        # Test with zero origin
        location = Location.objects.create(
            name='Zero Origin Location',
            svg_fragment_filename='zero.svg',
            svg_view_box_str='0 0 100 50'
        )
        bounds = location.svg_position_bounds
        self.assertEqual(bounds.min_x, 0)
        self.assertEqual(bounds.min_y, 0)
        self.assertEqual(bounds.max_x, 100)
        self.assertEqual(bounds.max_y, 50)
        
        # Test with negative origin
        location_negative = Location.objects.create(
            name='Negative Origin Location',
            svg_fragment_filename='negative.svg',
            svg_view_box_str='-50 -25 200 150'
        )
        bounds_negative = location_negative.svg_position_bounds
        self.assertEqual(bounds_negative.min_x, -50)
        self.assertEqual(bounds_negative.min_y, -25)
        self.assertEqual(bounds_negative.max_x, 150)  # -50 + 200
        self.assertEqual(bounds_negative.max_y, 125)  # -25 + 150
        
        # Verify scale limits are consistent across all locations
        self.assertEqual(bounds.min_scale, bounds_negative.min_scale)
        self.assertEqual(bounds.max_scale, bounds_negative.max_scale)
        return

    def test_location_view_svg_viewbox_inheritance_and_modification(self):
        """Test LocationView viewbox can differ from parent Location viewbox."""
        location = Location.objects.create(
            name='Parent Location',
            svg_fragment_filename='parent.svg',
            svg_view_box_str='0 0 500 400'
        )
        
        # Create view with different viewbox (zoomed in)
        zoomed_view = LocationView.objects.create(
            location=location,
            location_view_type_str='AUTOMATION',
            name='Zoomed Automation View',
            svg_view_box_str='100 100 200 200',
            svg_rotate=0,
            svg_style_name_str='COLOR'
        )
        
        # Create view with different viewbox (different aspect ratio)
        wide_view = LocationView.objects.create(
            location=location,
            location_view_type_str='DEFAULT',
            name='Wide Overview',
            svg_view_box_str='0 150 500 100',
            svg_rotate=0,
            svg_style_name_str='GREYSCALE'
        )
        
        # Verify each has independent viewbox
        parent_vb = location.svg_view_box
        zoomed_vb = zoomed_view.svg_view_box
        wide_vb = wide_view.svg_view_box
        
        self.assertNotEqual(parent_vb, zoomed_vb)
        self.assertNotEqual(parent_vb, wide_vb)
        self.assertNotEqual(zoomed_vb, wide_vb)
        
        # Verify specific viewbox values
        self.assertEqual(zoomed_vb.width, 200)
        self.assertEqual(zoomed_vb.height, 200)
        self.assertEqual(wide_vb.width, 500)
        self.assertEqual(wide_vb.height, 100)
        return

    def test_location_multiple_view_types_coexistence(self):
        """Test multiple view types can coexist with different configurations."""
        location = Location.objects.create(
            name='Multi-View Location',
            svg_fragment_filename='multi.svg',
            svg_view_box_str='0 0 1000 800'
        )
        
        # Create views of different types with varied configurations
        views_config = [
            ('DEFAULT', 'Main View', '0 0 1000 800', 0, 'COLOR'),
            ('AUTOMATION', 'Automation Zone', '200 200 600 400', 0, 'GREYSCALE'),
        ]
        
        created_views = []
        for i, (view_type, name, viewbox, rotate, style) in enumerate(views_config):
            view = LocationView.objects.create(
                location=location,
                location_view_type_str=view_type,
                name=name,
                svg_view_box_str=viewbox,
                svg_rotate=rotate,
                svg_style_name_str=style,
                order_id=i + 1
            )
            created_views.append(view)
        
        # Verify all views exist and have correct configurations
        all_views = LocationView.objects.filter(location=location).order_by('order_id')
        self.assertEqual(len(all_views), 2)
        
        # Verify each view maintains its distinct configuration
        for view, expected_config in zip(all_views, views_config):
            view_type, name, viewbox, rotate, style = expected_config
            self.assertEqual(view.location_view_type_str, view_type)
            self.assertEqual(view.name, name)
            self.assertEqual(view.svg_view_box_str, viewbox)
            self.assertEqual(float(view.svg_rotate), rotate)
            self.assertEqual(view.svg_style_name_str, style)
        return

    def test_location_attribute_value_type_handling(self):
        """Test LocationAttribute handles different value types correctly."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        # Create attributes with different value types
        attribute_configs = [
            ('description', AttributeValueType.TEXT, 'Main living room area'),
            ('manual', AttributeValueType.FILE, 'room_manual.pdf'),
            ('temperature', AttributeValueType.FLOAT, '72.5'),
            ('active', AttributeValueType.BOOLEAN, 'true'),
            ('count', AttributeValueType.INTEGER, '5'),
        ]
        
        created_attributes = []
        for name, value_type, value in attribute_configs:
            attr = LocationAttribute.objects.create(
                location=location,
                name=name,
                value_type_str=str(value_type),
                value=value
            )
            created_attributes.append(attr)
        
        # Verify all attributes were created with correct types
        all_attrs = LocationAttribute.objects.filter(location=location)
        self.assertEqual(len(all_attrs), 5)
        
        # Verify each attribute maintains its value type and content
        for attr, expected_config in zip(created_attributes, attribute_configs):
            name, value_type, value = expected_config
            self.assertEqual(attr.name, name)
            self.assertEqual(attr.value_type_str, str(value_type))
            self.assertEqual(attr.value, value)
        
        # Test value type specific behavior
        file_attrs = LocationAttribute.objects.filter(
            location=location,
            value_type_str=str(AttributeValueType.FILE)
        )
        self.assertEqual(len(file_attrs), 1)
        self.assertEqual(file_attrs.first().value, 'room_manual.pdf')
        return
