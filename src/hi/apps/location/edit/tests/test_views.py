import json
import logging
from unittest.mock import Mock, patch

from django.core.exceptions import BadRequest
from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.enums import ItemType, ViewMode
from hi.tests.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestLocationAddView(DualModeViewTestCase):
    """
    Tests for LocationAddView - demonstrates location creation testing.
    This view handles adding new locations with SVG uploads.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)

    def test_get_location_add_form(self):
        """Test getting location add form."""
        url = reverse('location_edit_location_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_add.html')
        self.assertIn('location_add_form', response.context)

    def test_get_location_add_form_async(self):
        """Test getting location add form with AJAX request."""
        url = reverse('location_edit_location_add')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_invalid_form(self):
        """Test POST request with invalid form data."""
        # Submit form with missing required fields
        form_data = {
            'name': '',  # Required field is empty
            # Missing svg_fragment_content (required)
        }

        url = reverse('location_edit_location_add')
        response = self.client.post(url, form_data)

        # Should return success with form errors (not redirect)
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Test that form errors are present in context
        self.assertIn('location_add_form', response.context)
        form = response.context['location_add_form']
        self.assertFalse(form.is_valid())
        
        # Should have validation errors for required fields
        self.assertTrue(form.errors)
        
        # Verify no Location was created with invalid data
        self.assertFalse(Location.objects.filter(name='').exists())

    def test_post_valid_form(self):
        """Test POST request with valid form data."""
        # Create comprehensive form data for new location
        form_data = {
            'name': 'Test Location',
            'use_default_svg_file': 'on',  # Use default SVG file
        }

        # Count existing locations before
        initial_location_count = Location.objects.count()

        url = reverse('location_edit_location_add')
        response = self.client.post(url, form_data)

        # Test actual redirect behavior (JSON redirect)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        home_url = reverse('home')
        self.assertEqual(data['location'], home_url)
        
        # Test that new Location was created
        self.assertEqual(Location.objects.count(), initial_location_count + 1)
        
        # Get the newly created location
        new_location = Location.objects.get(name='Test Location')
        self.assertEqual(new_location.name, 'Test Location')
        
        # Verify the location has the required SVG fields set
        self.assertTrue(new_location.svg_fragment_filename)
        self.assertTrue(new_location.svg_view_box_str)
        
        # Test that a default location view was created
        location_views = new_location.views.all()
        self.assertEqual(len(location_views), 1)
        self.assertEqual(location_views[0].location, new_location)

    @patch.object(LocationManager, 'create_location')
    @patch('hi.apps.location.edit.forms.LocationAddForm')
    def test_post_create_location_error(self, mock_form_class, mock_create_location):
        """Test POST request when location creation fails."""
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {'name': 'Test Location'}
        mock_form_class.return_value = mock_form

        # Mock location manager raising error
        mock_create_location.side_effect = ValueError("Invalid SVG")

        url = reverse('location_edit_location_add')
        response = self.client.post(url, {'name': 'Test Location'})

        self.assertEqual(response.status_code, 400)


class TestLocationAddFirstView(DualModeViewTestCase):
    """
    Tests for LocationAddFirstView - demonstrates specialized location creation testing.
    This view is used when adding the first location.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)

    def test_get_location_add_first_form(self):
        """Test getting first location add form."""
        url = reverse('location_add_first')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_add_first.html')

    def test_inherits_from_location_add_view(self):
        """Test that LocationAddFirstView inherits from LocationAddView."""
        from hi.apps.location.edit.views import LocationAddFirstView, LocationAddView
        self.assertTrue(issubclass(LocationAddFirstView, LocationAddView))


class TestLocationSvgReplaceView(DualModeViewTestCase):
    """
    Tests for LocationSvgReplaceView - demonstrates SVG replacement testing.
    This view handles replacing location SVG files.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )

    def test_get_svg_replace_form(self):
        """Test getting SVG replace form."""
        url = reverse('location_svg_replace', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_svg_replace.html')
        self.assertEqual(response.context['location'], self.location)
        self.assertIn('location_svg_file_form', response.context)

    def test_get_svg_replace_form_async(self):
        """Test getting SVG replace form with AJAX request."""
        url = reverse('location_svg_replace', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    @patch('hi.apps.location.edit.forms.LocationSvgReplaceForm')
    def test_post_invalid_form(self, mock_form_class):
        """Test POST request with invalid form data."""
        # Mock invalid form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        url = reverse('location_svg_replace', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        # Should render form with errors
        self.assertEqual(response.context['location_svg_file_form'], mock_form)

    @patch.object(LocationManager, 'update_location_svg')
    @patch.object(LocationManager, 'get_location')
    @patch('hi.apps.location.edit.forms.LocationSvgReplaceForm')
    @patch('hi.apps.common.antinode.redirect_response')
    def test_post_valid_form(self, mock_redirect, mock_form_class, mock_get_location, mock_update_svg):
        """Test POST request with valid form data."""
        # Mock get_location
        mock_get_location.return_value = self.location
        
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {
            'svg_fragment_filename': 'new.svg',
            'svg_fragment_content': '<svg>new</svg>',
            'svg_viewbox': '0 0 200 200'
        }
        mock_form_class.return_value = mock_form

        # Mock SVG update
        mock_update_svg.return_value = self.location
        mock_redirect.return_value = 'redirect_response'

        url = reverse('location_svg_replace', kwargs={'location_id': self.location.id})
        _ = self.client.post(url, {})

        # Should update SVG and redirect
        mock_update_svg.assert_called_once_with(
            location=self.location,
            svg_fragment_filename='new.svg',
            svg_fragment_content='<svg>new</svg>',
            svg_viewbox='0 0 200 200'
        )

    def test_post_invalid_location_id(self):
        """Test POST request with invalid location ID."""
        url = reverse('location_svg_replace', kwargs={'location_id': 'invalid'})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_nonexistent_location_returns_404(self):
        """Test that accessing nonexistent location returns 404."""
        url = reverse('location_svg_replace', kwargs={'location_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestLocationEditView(SyncViewTestCase):
    """
    Tests for LocationEditView - demonstrates location editing testing.
    This view handles location property updates and attribute management.
    """

    def setUp(self):
        super().setUp()
        # Create test location
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )

    def test_get_location_edit(self):
        """Test GET request for location edit."""
        url = reverse('location_edit', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)

    @patch('hi.apps.location.edit.forms.LocationEditForm')
    @patch('hi.apps.location.edit.forms.LocationAttributeFormSet')
    @patch('hi.apps.common.antinode.refresh_response')
    def test_post_valid_edit_with_changes(self, mock_refresh, mock_formset_class, mock_form_class):
        """Test POST request with valid edit data that has changes."""
        # Mock valid forms with changes
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.has_changed.return_value = True
        mock_form_class.return_value = mock_form

        mock_formset = Mock()
        mock_formset.is_valid.return_value = True
        mock_formset_class.return_value = mock_formset

        mock_refresh.return_value = 'refresh_response'

        url = reverse('location_edit', kwargs={'location_id': self.location.id})
        _ = self.client.post(url, {'name': 'Updated Location'})

        mock_form.save.assert_called_once()
        mock_formset.save.assert_called_once()
        mock_refresh.assert_called_once()

    @patch('hi.apps.location.edit.forms.LocationEditForm')
    @patch('hi.apps.location.edit.forms.LocationAttributeFormSet')
    def test_post_valid_edit_without_changes(self, mock_formset_class, mock_form_class):
        """Test POST request with valid edit data that has no changes."""
        # Mock valid forms without changes
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.has_changed.return_value = False
        mock_form_class.return_value = mock_form

        mock_formset = Mock()
        mock_formset.is_valid.return_value = True
        mock_formset_class.return_value = mock_formset

        url = reverse('location_edit', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'name': 'Same Name'})

        self.assertSuccessResponse(response)
        # Should not refresh if no changes

    @patch('hi.apps.location.edit.forms.LocationEditForm')
    @patch('hi.apps.location.edit.forms.LocationAttributeFormSet')
    def test_post_invalid_edit(self, mock_formset_class, mock_form_class):
        """Test POST request with invalid edit data."""
        # Mock invalid forms
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        mock_formset = Mock()
        mock_formset.is_valid.return_value = True
        mock_formset_class.return_value = mock_formset

        url = reverse('location_edit', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'name': ''})

        self.assertEqual(response.status_code, 400)
        mock_form.save.assert_not_called()

    def test_nonexistent_location_returns_404(self):
        """Test that accessing nonexistent location returns 404."""
        url = reverse('location_edit', kwargs={'location_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestLocationAttributeUploadView(SyncViewTestCase):
    """
    Tests for LocationAttributeUploadView - demonstrates location attribute upload testing.
    This view handles uploading location attribute files.
    """

    def setUp(self):
        super().setUp()
        # Create test location
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )

    @patch('hi.apps.location.edit.forms.LocationAttributeUploadForm')
    def test_post_valid_upload(self, mock_form_class):
        """Test POST request with valid upload data."""
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form_class.return_value = mock_form

        url = reverse('location_attribute_upload', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        mock_form.save.assert_called_once()

    @patch('hi.apps.location.edit.forms.LocationAttributeUploadForm')
    def test_post_invalid_upload(self, mock_form_class):
        """Test POST request with invalid upload data."""
        # Mock invalid form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        url = reverse('location_attribute_upload', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)
        mock_form.save.assert_not_called()

    def test_nonexistent_location_returns_404(self):
        """Test that accessing nonexistent location returns 404."""
        url = reverse('location_attribute_upload', kwargs={'location_id': 99999})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('location_attribute_upload', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestLocationDeleteView(DualModeViewTestCase):
    """
    Tests for LocationDeleteView - demonstrates location deletion testing.
    This view handles location deletion with confirmation.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )

    def test_get_location_delete_confirmation(self):
        """Test getting location delete confirmation."""
        url = reverse('location_delete', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_delete.html')
        self.assertEqual(response.context['location'], self.location)

    def test_get_location_delete_async(self):
        """Test getting location delete confirmation with AJAX request."""
        url = reverse('location_delete', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_delete_without_confirmation(self):
        """Test POST request without confirmation."""
        url = reverse('location_delete', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_wrong_confirmation(self):
        """Test POST request with wrong confirmation value."""
        url = reverse('location_delete', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'action': 'cancel'})

        self.assertEqual(response.status_code, 400)

    @patch.object(LocationManager, 'get_location')
    def test_post_delete_with_confirmation(self, mock_get_location):
        """Test POST request with proper confirmation."""
        mock_get_location.return_value = self.location

        url = reverse('location_delete', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'action': 'confirm'})

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Location should be deleted
        with self.assertRaises(Location.DoesNotExist):
            Location.objects.get(id=self.location.id)

    def test_post_invalid_location_id(self):
        """Test POST request with invalid location ID."""
        url = reverse('location_delete', kwargs={'location_id': 'invalid'})
        response = self.client.post(url, {'action': 'confirm'})

        self.assertEqual(response.status_code, 400)

    def test_nonexistent_location_returns_404(self):
        """Test that accessing nonexistent location returns 404."""
        url = reverse('location_delete', kwargs={'location_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestLocationViewAddView(DualModeViewTestCase):
    """
    Tests for LocationViewAddView - demonstrates location view creation testing.
    This view handles adding new location views.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )

    @patch.object(LocationManager, 'get_default_location')
    def test_get_location_view_add_form(self, mock_get_location):
        """Test getting location view add form."""
        mock_get_location.return_value = self.location

        url = reverse('location_view_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_view_add.html')
        self.assertEqual(response.context['location'], self.location)
        self.assertIn('location_view_add_form', response.context)

    @patch.object(LocationManager, 'get_default_location')
    def test_get_location_view_add_no_location(self, mock_get_location):
        """Test getting location view add form when no location exists."""
        mock_get_location.side_effect = Location.DoesNotExist()

        url = reverse('location_view_add')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    @patch.object(LocationManager, 'create_location_view')
    @patch.object(LocationManager, 'get_default_location')
    @patch('hi.apps.location.edit.forms.LocationViewAddForm')
    def test_post_valid_form(self, mock_form_class, mock_get_location, mock_create_view):
        """Test POST request with valid form data."""
        mock_get_location.return_value = self.location
        
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {'name': 'New View'}
        mock_form_class.return_value = mock_form

        # Mock location view creation
        mock_location_view = Mock()
        mock_location_view.id = 1
        mock_create_view.return_value = mock_location_view

        url = reverse('location_view_add')
        response = self.client.post(url, {'name': 'New View'})

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Should create location view
        mock_create_view.assert_called_once_with(
            location=self.location,
            name='New View'
        )

    @patch.object(LocationManager, 'get_default_location')
    @patch('hi.apps.location.edit.forms.LocationViewAddForm')
    def test_post_invalid_form(self, mock_form_class, mock_get_location):
        """Test POST request with invalid form data."""
        mock_get_location.return_value = self.location
        
        # Mock invalid form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        url = reverse('location_view_add')
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        # Should render form with errors
        self.assertEqual(response.context['location_view_add_form'], mock_form)


class TestLocationViewDeleteView(DualModeViewTestCase):
    """
    Tests for LocationViewDeleteView - demonstrates location view deletion testing.
    This view handles location view deletion with confirmation.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location and location view
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view = LocationView.objects.create(
            location=self.location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0
        )

    def test_get_location_view_delete_confirmation(self):
        """Test getting location view delete confirmation."""
        url = reverse('location_view_delete', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_view_delete.html')
        self.assertEqual(response.context['location_view'], self.location_view)

    def test_post_delete_without_confirmation(self):
        """Test POST request without confirmation."""
        url = reverse('location_view_delete', kwargs={'location_view_id': self.location_view.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_confirmation(self):
        """Test POST request with proper confirmation."""
        url = reverse('location_view_delete', kwargs={'location_view_id': self.location_view.id})
        response = self.client.post(url, {'action': 'confirm'})

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('home')
        self.assertEqual(response.url, expected_url)
        
        # Location view should be deleted
        with self.assertRaises(LocationView.DoesNotExist):
            LocationView.objects.get(id=self.location_view.id)

    def test_nonexistent_location_view_returns_404(self):
        """Test that accessing nonexistent location view returns 404."""
        url = reverse('location_view_delete', kwargs={'location_view_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestLocationViewEditView(SyncViewTestCase):
    """
    Tests for LocationViewEditView - demonstrates location view editing testing.
    This view handles location view property updates.
    """

    def setUp(self):
        super().setUp()
        # Create test location and location view
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view = LocationView.objects.create(
            location=self.location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0
        )

    @patch('hi.apps.location.edit.forms.LocationViewEditForm')
    @patch('hi.apps.common.antinode.refresh_response')
    def test_post_valid_edit(self, mock_refresh, mock_form_class):
        """Test POST request with valid edit data."""
        # Mock valid form
        mock_form = Mock()
        mock_form.is_valid.return_value = True
        mock_form_class.return_value = mock_form
        
        mock_refresh.return_value = 'refresh_response'

        url = reverse('location_view_edit', kwargs={'location_view_id': self.location_view.id})
        _ = self.client.post(url, {'name': 'Updated View'})

        mock_form.save.assert_called_once()
        mock_refresh.assert_called_once()

    @patch('hi.apps.location.edit.forms.LocationViewEditForm')
    def test_post_invalid_edit(self, mock_form_class):
        """Test POST request with invalid edit data."""
        # Mock invalid form
        mock_form = Mock()
        mock_form.is_valid.return_value = False
        mock_form_class.return_value = mock_form

        url = reverse('location_view_edit', kwargs={'location_view_id': self.location_view.id})
        response = self.client.post(url, {'name': ''})

        self.assertEqual(response.status_code, 400)
        mock_form.save.assert_not_called()

    def test_nonexistent_location_view_returns_404(self):
        """Test that accessing nonexistent location view returns 404."""
        url = reverse('location_view_edit', kwargs={'location_view_id': 99999})
        response = self.client.post(url, {'name': 'Test'})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('location_view_edit', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestLocationViewManageItemsView(SyncViewTestCase):
    """
    Tests for LocationViewManageItemsView - demonstrates location view item management testing.
    This view displays interface for managing items in location views.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location and location view
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view = LocationView.objects.create(
            location=self.location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0
        )

    @patch.object(CollectionManager, 'create_location_collection_view_group')
    @patch.object(EntityManager, 'create_location_entity_view_group_list')
    @patch.object(LocationManager, 'get_default_location_view')
    def test_get_manage_items_view(self, mock_get_location_view, mock_create_entity_groups,
                                   mock_create_collection_group):
        """Test getting location view manage items view."""
        mock_get_location_view.return_value = self.location_view
        mock_entity_groups = ['entity_group1', 'entity_group2']
        mock_create_entity_groups.return_value = mock_entity_groups
        mock_collection_group = 'collection_group'
        mock_create_collection_group.return_value = mock_collection_group

        url = reverse('location_view_manage_items')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/panes/location_view_manage_items.html')
        
        self.assertEqual(response.context['location_view'], self.location_view)
        self.assertEqual(response.context['entity_view_group_list'], mock_entity_groups)
        self.assertEqual(response.context['collection_view_group'], mock_collection_group)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('location_view_manage_items')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestLocationViewReorder(SyncViewTestCase):
    """
    Tests for LocationViewReorder - demonstrates location view reordering testing.
    This view handles reordering location views.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location and location views
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view1 = LocationView.objects.create(
            location=self.location,
            name='View 1',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0
        )
        self.location_view2 = LocationView.objects.create(
            location=self.location,
            name='View 2',
            location_view_type_str='DETAIL',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0
        )

    @patch.object(LocationManager, 'set_location_view_order')
    @patch('hi.apps.common.antinode.response')
    def test_post_valid_reorder(self, mock_antinode_response, mock_set_order):
        """Test POST request with valid reorder data."""
        mock_antinode_response.return_value = 'success_response'
        
        location_view_id_list = [self.location_view2.id, self.location_view1.id]
        url = reverse('location_view_reorder', kwargs={
            'location_view_id_list': json.dumps(location_view_id_list)
        })
        _ = self.client.post(url)

        mock_set_order.assert_called_once_with(location_view_id_list=location_view_id_list)
        mock_antinode_response.assert_called_once_with(main_content='OK')

    def test_post_invalid_json(self):
        """Test POST request with invalid JSON data."""
        url = reverse('location_view_reorder', kwargs={
            'location_view_id_list': 'invalid-json'
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    def test_post_empty_location_view_list(self):
        """Test POST request with empty location view list."""
        url = reverse('location_view_reorder', kwargs={
            'location_view_id_list': json.dumps([])
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('location_view_reorder', kwargs={
            'location_view_id_list': json.dumps([1, 2])
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestLocationItemPositionView(SyncViewTestCase):
    """
    Tests for LocationItemPositionView - demonstrates item position delegation testing.
    This view delegates to appropriate position edit views based on item type.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test data
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
        )
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    @patch('hi.apps.location.edit.views.EntityPositionEditView')
    def test_post_entity_position(self, mock_view_class):
        """Test POST request for entity position."""
        mock_view = mock_view_class.return_value
        mock_view.post.return_value = 'entity_response'

        url = reverse('location_item_position', kwargs={
            'item_type': 'entity',
            'item_id': self.entity.id
        })
        _ = self.client.post(url, {})

        # Should delegate to EntityPositionEditView
        mock_view.post.assert_called_once()
        call_kwargs = mock_view.post.call_args[1]
        self.assertEqual(call_kwargs['entity_id'], self.entity.id)

    @patch('hi.apps.location.edit.views.CollectionPositionEditView')
    def test_post_collection_position(self, mock_view_class):
        """Test POST request for collection position."""
        mock_view = mock_view_class.return_value
        mock_view.post.return_value = 'collection_response'

        url = reverse('location_item_position', kwargs={
            'item_type': 'collection',
            'item_id': self.collection.id
        })
        _ = self.client.post(url, {})

        # Should delegate to CollectionPositionEditView
        mock_view.post.assert_called_once()
        call_kwargs = mock_view.post.call_args[1]
        self.assertEqual(call_kwargs['collection_id'], self.collection.id)

    def test_post_unknown_item_type(self):
        """Test POST request with unknown item type."""
        url = reverse('location_item_position', kwargs={
            'item_type': 'unknown',
            'item_id': 1
        })
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_invalid_item_id(self):
        """Test POST request with invalid item ID."""
        # This would typically be caught by ItemType.parse_from_dict
        with self.assertRaises(BadRequest):
            # Simulate what happens in the view with invalid data
            ItemType.parse_from_dict({'item_type': 'entity', 'item_id': 'invalid'})

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('location_item_position', kwargs={
            'item_type': 'entity',
            'item_id': self.entity.id
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestLocationItemPathView(SyncViewTestCase):
    """
    Tests for LocationItemPathView - demonstrates SVG path setting testing.
    This view handles setting SVG paths for items in locations.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test data
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
        )
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    @patch.object(EntityManager, 'set_entity_path')
    @patch.object(LocationManager, 'get_default_location')
    @patch('hi.apps.common.antinode.response')
    def test_post_entity_path(self, mock_antinode_response, mock_get_location, mock_set_path):
        """Test POST request to set entity SVG path."""
        mock_get_location.return_value = self.location
        mock_antinode_response.return_value = 'success_response'

        url = reverse('location_item_path', kwargs={
            'item_type': 'entity',
            'item_id': self.entity.id
        })
        _ = self.client.post(url, {'svg_path': 'M 10 10 L 20 20'})

        mock_set_path.assert_called_once_with(
            entity_id=self.entity.id,
            location=self.location,
            svg_path_str='M 10 10 L 20 20'
        )
        mock_antinode_response.assert_called_once_with(main_content='OK')

    @patch.object(CollectionManager, 'set_collection_path')
    @patch.object(CollectionManager, 'get_collection')
    @patch.object(LocationManager, 'get_default_location')
    @patch('hi.apps.common.antinode.response')
    def test_post_collection_path(self, mock_antinode_response, mock_get_location,
                                  mock_get_collection, mock_set_path):
        """Test POST request to set collection SVG path."""
        mock_get_location.return_value = self.location
        mock_get_collection.return_value = self.collection
        mock_antinode_response.return_value = 'success_response'

        url = reverse('location_item_path', kwargs={
            'item_type': 'collection',
            'item_id': self.collection.id
        })
        _ = self.client.post(url, {'svg_path': 'M 30 30 L 40 40'})

        mock_set_path.assert_called_once_with(
            collection=self.collection,
            location=self.location,
            svg_path_str='M 30 30 L 40 40'
        )

    def test_post_missing_svg_path(self):
        """Test POST request without SVG path."""
        url = reverse('location_item_path', kwargs={
            'item_type': 'entity',
            'item_id': self.entity.id
        })
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_unknown_item_type(self):
        """Test POST request with unknown item type."""
        url = reverse('location_item_path', kwargs={
            'item_type': 'unknown',
            'item_id': 1
        })
        response = self.client.post(url, {'svg_path': 'M 0 0 L 1 1'})

        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('location_item_path', kwargs={
            'item_type': 'entity',
            'item_id': self.entity.id
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        
