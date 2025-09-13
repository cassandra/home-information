import logging

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.enums import EntityType
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.enums import ItemType, ViewMode
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase

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

    def tearDown(self):
        """Clean up singletons when using real objects instead of mocks."""
        # Reset singleton managers to ensure clean state between tests
        try:
            LocationManager._instance = None
        except ImportError:
            pass
        try:
            CollectionManager._instance = None
        except ImportError:
            pass
        try:
            EntityManager._instance = None
        except ImportError:
            pass
        super().tearDown()

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

    def test_post_create_location_error(self):
        """Test POST request when location creation fails due to invalid data."""
        url = reverse('location_edit_location_add')
        
        # Provide invalid data that should cause form validation to fail
        response = self.client.post(url, {
            'name': '',  # Empty name should cause validation error
            # Missing required fields like SVG file
        })

        # Should return error response (400 or form validation error)
        # The exact status code depends on how the view handles validation errors
        self.assertIn(response.status_code, [200, 400])  # 200 if form errors shown, 400 if bad request
        
        # Verify no location was created when form validation fails
        self.assertEqual(Location.objects.filter(name='').count(), 0)


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
        url = reverse('location_edit_svg_replace', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_svg_replace.html')
        self.assertEqual(response.context['location'], self.location)
        self.assertIn('location_svg_file_form', response.context)

    def test_get_svg_replace_form_async(self):
        """Test getting SVG replace form with AJAX request."""
        url = reverse('location_edit_svg_replace', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_invalid_form(self):
        """Test POST request with invalid form data."""
        url = reverse('location_edit_svg_replace', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {
            # No SVG file provided - should cause form validation to fail
        })

        # Should return success but with form errors
        self.assertSuccessResponse(response)
        # Should render form with validation errors
        form = response.context['location_svg_file_form']
        self.assertFalse(form.is_valid())

    def test_post_valid_form(self):
        """Test POST request with valid form data."""
        # Create a simple SVG file for upload
        svg_content = b'<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><rect width="200" height="200" fill="blue"/></svg>'
        svg_file = SimpleUploadedFile(
            'new_location.svg',
            svg_content,
            content_type='image/svg+xml'
        )
        
        # Store original values to verify change
        original_filename = self.location.svg_fragment_filename
        original_viewbox = self.location.svg_view_box_str
        
        url = reverse('location_edit_svg_replace', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {
            'svg_file': svg_file,
            'remove_dangerous_svg_items': False,
            'has_dangerous_svg_items': 'false'
        })

        # Should return redirect response for antinode.js
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify the response contains the redirect
        response_data = response.json()
        expected_url = reverse('home')
        self.assertEqual(response_data['location'], expected_url)
        
        # Refresh from database to get updated values
        self.location.refresh_from_db()
        
        # Verify the location's SVG was updated
        self.assertNotEqual(self.location.svg_fragment_filename, original_filename)
        # The viewbox might be normalized to include decimals
        self.assertIn('200', self.location.svg_view_box_str)
        self.assertNotEqual(self.location.svg_view_box_str, original_viewbox)
        # The filename should contain 'new_location' from our uploaded file
        self.assertIn('new_location', self.location.svg_fragment_filename)

    def test_nonexistent_location_returns_404(self):
        """Test that accessing nonexistent location returns 404."""
        url = reverse('location_edit_svg_replace', kwargs={'location_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


# TODO: Add tests for LocationEditView V2 modal implementation
# Tests will be created following the Entity test patterns after V2 implementation is complete


class TestLocationDeleteView(DualModeViewTestCase):
    """
    Tests for LocationDeleteView - demonstrates location deletion testing.
    This view handles location deletion with confirmation.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location using synthetic data
        self.location = LocationSyntheticData.create_test_location(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )

    def test_get_location_delete_confirmation(self):
        """Test getting location delete confirmation."""
        url = reverse('location_edit_location_delete', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_delete.html')
        self.assertEqual(response.context['location'], self.location)

    def test_get_location_delete_async(self):
        """Test getting location delete confirmation with AJAX request."""
        url = reverse('location_edit_location_delete', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_delete_without_confirmation(self):
        """Test POST request without confirmation."""
        url = reverse('location_edit_location_delete', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_wrong_confirmation(self):
        """Test POST request with wrong confirmation value."""
        url = reverse('location_edit_location_delete', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'action': 'cancel'})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_confirmation(self):
        """Test POST request with proper confirmation."""
        url = reverse('location_edit_location_delete', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'action': 'confirm'})

        # HiModalView returns JSON redirect response for antinode.js
        self.assertEqual(response.status_code, 200)
        self.assertJsonResponse(response)
        response_data = response.json()
        expected_url = reverse('home')
        self.assertEqual(response_data['location'], expected_url)
        
        # Location should be deleted
        with self.assertRaises(Location.DoesNotExist):
            Location.objects.get(id=self.location.id)

    def test_post_invalid_location_id(self):
        """Test POST request with invalid location ID."""
        # Can't use 'invalid' as location_id in URL - pattern expects digits
        # So we'll test with a nonexistent numeric ID
        url = reverse('location_edit_location_delete', kwargs={'location_id': 99999})
        response = self.client.post(url, {'action': 'confirm'})

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_location_returns_404(self):
        """Test that accessing nonexistent location returns 404."""
        url = reverse('location_edit_location_delete', kwargs={'location_id': 99999})
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
        
        # Create test location using synthetic data
        self.location = LocationSyntheticData.create_test_location(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )

    def test_get_location_view_add_form(self):
        """Test getting location view add form."""
        # Make this location the default by ensuring it's the only one
        Location.objects.exclude(id=self.location.id).delete()
        
        url = reverse('location_edit_location_view_add')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_view_add.html')
        self.assertEqual(response.context['location'], self.location)
        self.assertIn('location_view_add_form', response.context)

    def test_get_location_view_add_no_location(self):
        """Test getting location view add form when no location exists."""
        # Delete all locations to test error case
        Location.objects.all().delete()

        url = reverse('location_edit_location_view_add')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    def test_post_valid_form(self):
        """Test POST request with valid form data."""
        # Make this location the default by ensuring it's the only one
        Location.objects.exclude(id=self.location.id).delete()
        
        url = reverse('location_edit_location_view_add')
        response = self.client.post(url, {'name': 'New View',
                                          'location_view_type_str': 'default',
                                          'svg_style_name_str': 'color' })

        # Expect JSON response for antinode.js
        self.assertEqual(response.status_code, 200)
        self.assertJsonResponse(response)
        response_data = response.json()
        expected_url = reverse('home')
        self.assertEqual(response_data['location'], expected_url)
        
        # Verify location view was created
        from hi.apps.location.models import LocationView
        new_view = LocationView.objects.filter(
            location=self.location,
            name='New View'
        ).first()
        self.assertIsNotNone(new_view)
        self.assertEqual(new_view.name, 'New View')

    def test_post_invalid_form(self):
        """Test POST request with invalid form data."""
        # Make this location the default by ensuring it's the only one
        Location.objects.exclude(id=self.location.id).delete()
        
        url = reverse('location_edit_location_view_add')
        response = self.client.post(url, {})  # Missing required name field

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Should render form with errors
        form = response.context.get('location_view_add_form')
        self.assertIsNotNone(form)
        self.assertFalse(form.is_valid())
        
        # Verify no location view was created
        from hi.apps.location.models import LocationView
        views = LocationView.objects.filter(location=self.location)
        self.assertEqual(views.count(), 0)


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
        url = reverse('location_edit_location_view_delete', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_view_delete.html')
        self.assertEqual(response.context['location_view'], self.location_view)

    def test_post_delete_without_confirmation(self):
        """Test POST request without confirmation."""
        url = reverse('location_edit_location_view_delete', kwargs={'location_view_id': self.location_view.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_delete_with_confirmation(self):
        """Test POST request with proper confirmation."""
        url = reverse('location_edit_location_view_delete',
                      kwargs={'location_view_id': self.location_view.id})
        response = self.client.post(url, {'action': 'confirm'})

        # Expect JSON response for antinode.js
        self.assertEqual(response.status_code, 200)
        self.assertJsonResponse(response)
        response_data = response.json()
        expected_url = reverse('home')
        self.assertEqual(response_data['location'], expected_url)
        
        # Location view should be deleted
        with self.assertRaises(LocationView.DoesNotExist):
            LocationView.objects.get(id=self.location_view.id)

    def test_nonexistent_location_view_returns_404(self):
        """Test that accessing nonexistent location view returns 404."""
        url = reverse('location_edit_location_view_delete', kwargs={'location_view_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestLocationViewEditModeView(DualModeViewTestCase):
    """
    Tests for LocationViewEditModeView - demonstrates location view editing testing.
    This view handles both displaying the edit interface (GET) and processing form submissions (POST).
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location and location view using synthetic data
        self.location = LocationSyntheticData.create_test_location(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view = LocationSyntheticData.create_test_location_view(
            location=self.location,
            name='Test View',
            svg_view_box_str='0 0 100 100'
        )

    def test_get_edit_mode_panel(self):
        """Test GET request returns the edit mode panel."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': self.location_view.id})
        response = self.async_get(url)

        # Should return success
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Should use the edit mode panel template
        self.assertTemplateRendered(response, 'location/edit/panes/location_view_edit_mode_panel.html')

    def test_post_valid_edit(self):
        """Test POST request with valid edit data."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': self.location_view.id})
        response = self.async_post(url, {
            'name': 'Updated View',
            'location_view_type_str': self.location_view.location_view_type_str,
            'svg_style_name_str': 'color',
            'svg_view_box_str': self.location_view.svg_view_box_str,
            'svg_rotate': str(self.location_view.svg_rotate),
            'order_id': str(self.location_view.order_id)
        })

        # Should return success (200 with JSON for antinode.js)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify the location view was updated
        self.location_view.refresh_from_db()
        self.assertEqual(self.location_view.name, 'Updated View')

    def test_post_invalid_edit(self):
        """Test POST request with invalid edit data."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': self.location_view.id})
        response = self.async_post(url, {'name': ''})  # Empty name should be invalid

        # Should return 400 for invalid form data
        self.assertEqual(response.status_code, 400)
        self.assertJsonResponse(response)
        
        # Verify the location view was not updated
        self.location_view.refresh_from_db()
        self.assertEqual(self.location_view.name, 'Test View')  # Original name unchanged

    def test_nonexistent_location_view_returns_404(self):
        """Test that accessing nonexistent location view returns 404."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': 99999})
        response = self.async_post(url, {'name': 'Test'})

        # Should return 404 for nonexistent location view
        self.assertEqual(response.status_code, 404)

    def test_get_nonexistent_location_view_returns_404(self):
        """Test that GET request for nonexistent location view returns 404."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': 99999})
        response = self.async_get(url)

        # Should return 404 for nonexistent location view
        self.assertEqual(response.status_code, 404)


class TestLocationViewManageItemsView(SyncViewTestCase):
    """
    Tests for LocationViewManageItemsView - demonstrates location view item management testing.
    This view displays interface for managing items in location views.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test location and location view using synthetic data
        self.location = LocationSyntheticData.create_test_location(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view = LocationSyntheticData.create_test_location_view(
            location=self.location,
            name='Test View',
            svg_view_box_str='0 0 100 100'
        )

    def test_get_manage_items_view(self):
        """Test getting location view manage items view."""
        # Make this location view the default by ensuring no others exist
        from hi.apps.location.models import LocationView
        LocationView.objects.exclude(id=self.location_view.id).delete()
        Location.objects.exclude(id=self.location.id).delete()

        url = reverse('location_edit_location_view_manage_items')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        self.assertTemplateRendered(response, 'location/edit/panes/location_view_manage_items.html')
        
        self.assertEqual(response.context['location_view'], self.location_view)
        # Verify context contains expected data structures (lists/groups)
        self.assertIn('entity_view_group_list', response.context)
        self.assertIn('collection_view_group', response.context)
        # Groups should be lists/objects (not mocks)
        self.assertIsNotNone(response.context['entity_view_group_list'])
        self.assertIsNotNone(response.context['collection_view_group'])


class TestLocationItemPositionView(SyncViewTestCase):
    """
    Tests for LocationItemPositionView - demonstrates item position delegation testing.
    This view delegates to appropriate position edit views based on item type.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)
        
        # Create test data using synthetic data helpers
        from hi.apps.entity.tests.synthetic_data import EntityAttributeSyntheticData
        self.entity = EntityAttributeSyntheticData.create_test_entity(
            name='Test Entity',
            entity_type_str=str(EntityType.LIGHT)
        )
        
        from hi.apps.collection.tests.synthetic_data import CollectionSyntheticData  
        self.collection = CollectionSyntheticData.create_test_collection(
            name='Test Collection'
        )

    def test_post_entity_position(self):
        """Test POST request for entity position."""
        # Create a location with the entity positioned on it
        location = LocationSyntheticData.create_test_location()
        entity_with_position = LocationSyntheticData.create_test_entity_with_position(
            location=location,
            name='Test Entity',
            entity_type_str=str(EntityType.LIGHT),
            svg_x=100.0,
            svg_y=100.0,
            svg_rotate=0.0,
            svg_scale=1.0
        )

        # Create HTML ID for the entity
        html_id = ItemType.ENTITY.html_id(entity_with_position.id)
        url = reverse('location_edit_location_item_position', kwargs={
            'html_id': html_id
        })
        
        # Post new position data
        response = self.client.post(url, {
            'svg_x': 200.0,
            'svg_y': 150.0,
            'svg_rotate': 90.0,
            'svg_scale': 1.5
        })

        # Should delegate to EntityPositionEditView and succeed
        self.assertSuccessResponse(response)
        
        # Verify position was updated in database
        from hi.apps.entity.models import EntityPosition
        position = EntityPosition.objects.get(
            entity=entity_with_position,
            location=location
        )
        self.assertEqual(position.svg_x, 200.0)
        self.assertEqual(position.svg_y, 150.0)

    def test_post_collection_position(self):
        """Test POST request for collection position."""
        # Create a location with the collection positioned on it
        location = LocationSyntheticData.create_test_location()
        collection_with_position = LocationSyntheticData.create_test_collection_with_position(
            location=location,
            name='Test Collection',
            svg_x=100.0,
            svg_y=100.0,
            svg_rotate=0.0,
            svg_scale=1.0
        )

        # Create HTML ID for the collection
        html_id = ItemType.COLLECTION.html_id(collection_with_position.id)
        url = reverse('location_edit_location_item_position', kwargs={
            'html_id': html_id
        })
        
        # Post new position data
        response = self.client.post(url, {
            'svg_x': 300.0,
            'svg_y': 250.0,
            'svg_rotate': 45.0,
            'svg_scale': 2.0
        })

        # Should delegate to CollectionPositionEditView and succeed
        self.assertSuccessResponse(response)
        
        # Verify position was updated in database
        from hi.apps.collection.models import CollectionPosition
        position = CollectionPosition.objects.get(
            collection=collection_with_position,
            location=location
        )
        self.assertEqual(position.svg_x, 300.0)
        self.assertEqual(position.svg_y, 250.0)

    def test_post_unknown_item_type(self):
        """Test POST request with unknown item type."""
        # Use an invalid HTML ID format
        url = reverse('location_edit_location_item_position', kwargs={
            'html_id': 'hi-invalid-1'
        })
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_invalid_item_id(self):
        """Test POST request with invalid item ID."""
        # Use an HTML ID with non-existent item
        html_id = ItemType.ENTITY.html_id(99999)
        url = reverse('location_edit_location_item_position', kwargs={
            'html_id': html_id
        })
        response = self.client.post(url, {})
        
        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_edit_location_item_position', kwargs={
            'html_id': html_id
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
        
        # Create test data using synthetic data
        self.location = LocationSyntheticData.create_test_location(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        from hi.apps.entity.tests.synthetic_data import EntityAttributeSyntheticData
        self.entity = EntityAttributeSyntheticData.create_test_entity(
            name='Test Entity',
            entity_type_str=str(EntityType.LIGHT)
        )
        
        from hi.apps.collection.tests.synthetic_data import CollectionSyntheticData
        self.collection = CollectionSyntheticData.create_test_collection(
            name='Test Collection'
        )

    def test_post_entity_path(self):
        """Test POST request to set entity SVG path."""
        # Make this location the default by ensuring it's the only one
        Location.objects.exclude(id=self.location.id).delete()
        
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_edit_location_item_path', kwargs={
            'html_id': html_id
        })
        response = self.client.post(url, {'svg_path': 'M 10 10 L 20 20'})

        # Should return success (200 with JSON for antinode.js)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify entity path was set in the database
        # Check if EntityPath model exists to verify path was saved
        from hi.apps.entity.models import EntityPath
        entity_path = EntityPath.objects.filter(
            entity=self.entity,
            location=self.location
        ).first()
        self.assertIsNotNone(entity_path)
        self.assertEqual(entity_path.svg_path, 'M 10 10 L 20 20')

    def test_post_collection_path(self):
        """Test POST request to set collection SVG path."""
        # Make this location the default by ensuring it's the only one
        Location.objects.exclude(id=self.location.id).delete()
        
        html_id = ItemType.COLLECTION.html_id(self.collection.id)
        url = reverse('location_edit_location_item_path', kwargs={
            'html_id': html_id
        })
        response = self.client.post(url, {'svg_path': 'M 30 30 L 40 40'})
        
        # Should return success (200 with JSON for antinode.js)
        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify collection path was set in the database
        # Check if CollectionPath model exists to verify path was saved
        from hi.apps.collection.models import CollectionPath
        collection_path = CollectionPath.objects.filter(
            collection=self.collection,
            location=self.location
        ).first()
        self.assertIsNotNone(collection_path)
        self.assertEqual(collection_path.svg_path, 'M 30 30 L 40 40')

    def test_post_missing_svg_path(self):
        """Test POST request without SVG path."""
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_edit_location_item_path', kwargs={
            'html_id': html_id
        })
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_unknown_item_type(self):
        """Test POST request with unknown item type."""
        html_id = 'hi-bogus-5'
        url = reverse('location_edit_location_item_path', kwargs={
            'html_id': html_id
        })
        response = self.client.post(url, {'svg_path': 'M 0 0 L 1 1'})
        
        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_edit_location_item_path', kwargs={
            'html_id': html_id
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        
