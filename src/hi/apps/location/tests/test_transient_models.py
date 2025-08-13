import logging

from hi.apps.location.transient_models import LocationEditData, LocationViewEditData
from hi.apps.location.models import Location, LocationView
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestLocationEditData(BaseTestCase):

    def test_location_edit_data_form_initialization(self):
        """Test LocationEditData form auto-initialization - critical for edit UI."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        edit_data = LocationEditData(location=location)
        
        # Forms should be automatically initialized
        self.assertIsNotNone(edit_data.location_edit_form)
        self.assertIsNotNone(edit_data.location_attribute_formset)
        self.assertIsNotNone(edit_data.location_attribute_upload_form)
        
        # Form should be bound to location instance
        self.assertEqual(edit_data.location_edit_form.instance, location)
        self.assertEqual(edit_data.location_attribute_formset.instance, location)
        return

    def test_location_edit_data_template_context_generation(self):
        """Test template context generation - critical for template rendering."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        edit_data = LocationEditData(location=location)
        context = edit_data.to_template_context()
        
        # Should contain all required template variables
        expected_keys = {
            'location',
            'location_edit_form',
            'location_attribute_formset',
            'location_attribute_upload_form'
        }
        self.assertEqual(set(context.keys()), expected_keys)
        self.assertEqual(context['location'], location)
        return

    def test_location_edit_data_formset_prefix_generation(self):
        """Test formset prefix generation - critical for form handling."""
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        edit_data = LocationEditData(location=location)
        
        # Prefix should include location ID
        expected_prefix = f'location-{location.id}'
        self.assertEqual(edit_data.location_attribute_formset.prefix, expected_prefix)
        return


class TestLocationViewEditData(BaseTestCase):

    def test_location_view_edit_data_form_initialization(self):
        """Test LocationViewEditData form auto-initialization - critical for edit UI."""
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
        
        edit_data = LocationViewEditData(location_view=location_view)
        
        # Form should be automatically initialized
        self.assertIsNotNone(edit_data.location_view_edit_form)
        
        # Form should be bound to location_view instance
        self.assertEqual(edit_data.location_view_edit_form.instance, location_view)
        return

    def test_location_view_edit_data_template_context_generation(self):
        """Test template context generation - critical for template rendering."""
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
        
        edit_data = LocationViewEditData(location_view=location_view)
        context = edit_data.to_template_context()
        
        # Should contain all required template variables
        expected_keys = {'location_view', 'location_view_edit_form'}
        self.assertEqual(set(context.keys()), expected_keys)
        self.assertEqual(context['location_view'], location_view)
        return