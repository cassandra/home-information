import logging
from unittest.mock import patch

from django.urls import reverse

from hi.apps.collection.models import Collection
from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.models import Location, LocationView
from hi.enums import ViewMode, ViewType
from hi.tests.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestEditStartView(SyncViewTestCase):
    """
    Tests for EditStartView - demonstrates edit mode activation testing.
    This view enables edit mode and redirects appropriately.
    """

    def setUp(self):
        super().setUp()
        # Create test location and location view for edit-capable context
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

    def test_edit_start_with_referer(self):
        """Test starting edit mode with valid referer."""
        # Set view type that allows edit mode
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        url = reverse('edit_start')
        response = self.client.get(url, HTTP_REFERER='/test/page/')

        # Should redirect to referer
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/test/page/')
        
        # Should set edit mode in session
        session = self.client.session
        self.assertEqual(session.get('view_mode'), str(ViewMode.EDIT))

    def test_edit_start_without_referer(self):
        """Test starting edit mode without referer."""
        # Set view type that allows edit mode
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        url = reverse('edit_start')
        response = self.client.get(url)

        # Should redirect to home
        home_url = reverse('home')
        self.assertRedirects(response, home_url, fetch_redirect_response=False)
        
        # Should set edit mode in session
        session = self.client.session
        self.assertEqual(session.get('view_mode'), str(ViewMode.EDIT))

    def test_edit_start_with_non_editable_view_type(self):
        """Test starting edit mode with view type that doesn't allow editing."""
        # Set view type that doesn't allow edit mode
        self.setSessionViewType(ViewType.CONFIGURATION)
        
        url = reverse('edit_start')
        response = self.client.get(url, HTTP_REFERER='/config/page/')

        # Should redirect to home instead of referer
        home_url = reverse('home')
        self.assertRedirects(response, home_url, fetch_redirect_response=False)
        
        # Should still set edit mode in session
        session = self.client.session
        self.assertEqual(session.get('view_mode'), str(ViewMode.EDIT))

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('edit_start')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestEditEndView(SyncViewTestCase):
    """
    Tests for EditEndView - demonstrates edit mode deactivation testing.
    This view disables edit mode and redirects with sidebar cleanup.
    """

    def test_edit_end_with_referer(self):
        """Test ending edit mode with referer containing sidebar URL."""
        # Set edit mode initially
        self.setSessionViewMode(ViewMode.EDIT)
        
        url = reverse('edit_end')
        referer_url = '/location/view/1?details=/item/details/123'
        response = self.client.get(url, HTTP_REFERER=referer_url)

        # Should redirect and clear sidebar parameter
        self.assertEqual(response.status_code, 302)
        self.assertIn('/location/view/1', response.url)
        self.assertIn('details=', response.url)  # Should be empty
        
        # Should set monitor mode in session
        session = self.client.session
        self.assertEqual(session.get('view_mode'), str(ViewMode.MONITOR))

    def test_edit_end_without_referer(self):
        """Test ending edit mode without referer."""
        # Set edit mode initially
        self.setSessionViewMode(ViewMode.EDIT)
        
        url = reverse('edit_end')
        response = self.client.get(url)

        # Should redirect to home
        home_url = reverse('home')
        self.assertRedirects(response, home_url, fetch_redirect_response=False)
        
        # Should set monitor mode in session
        session = self.client.session
        self.assertEqual(session.get('view_mode'), str(ViewMode.MONITOR))

    def test_edit_end_preserves_other_query_params(self):
        """Test that other query parameters are preserved when clearing sidebar."""
        # Set edit mode initially
        self.setSessionViewMode(ViewMode.EDIT)
        
        url = reverse('edit_end')
        referer_url = '/location/view/1?page=2&details=/item/details/123&sort=name'
        response = self.client.get(url, HTTP_REFERER=referer_url)

        # Should redirect and preserve other params while clearing details
        self.assertEqual(response.status_code, 302)
        self.assertIn('page=2', response.url)
        self.assertIn('sort=name', response.url)
        self.assertIn('details=', response.url)  # Should be empty

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('edit_end')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestItemDetailsCloseView(SyncViewTestCase):
    """
    Tests for ItemDetailsCloseView - demonstrates view type delegation testing.
    This view delegates to appropriate manage items views based on context.
    """

    def setUp(self):
        super().setUp()
        # Set edit mode (required by decorator)
        self.setSessionViewMode(ViewMode.EDIT)

    @patch('hi.apps.edit.views.LocationViewManageItemsView')
    def test_close_for_location_view(self, mock_view_class):
        """Test closing details for location view context."""
        from django.http import HttpResponse
        mock_view = mock_view_class.return_value
        mock_view.get.return_value = HttpResponse('mock_response')
        
        # Set location view context
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        url = reverse('edit_item_details_close')
        response = self.client.get(url)

        # Should delegate to LocationViewManageItemsView and return successful response
        self.assertSuccessResponse(response)
        mock_view.get.assert_called_once()

    @patch('hi.apps.edit.views.CollectionManageItemsView')
    def test_close_for_collection(self, mock_view_class):
        """Test closing details for collection context."""
        from django.http import HttpResponse
        mock_view = mock_view_class.return_value
        mock_view.get.return_value = HttpResponse('mock_response')
        
        # Set collection context
        self.setSessionViewType(ViewType.COLLECTION)
        
        url = reverse('edit_item_details_close')
        response = self.client.get(url)

        # Should delegate to CollectionManageItemsView and return successful response
        self.assertSuccessResponse(response)
        mock_view.get.assert_called_once()

    def test_close_for_unsupported_view_type(self):
        """Test closing details for unsupported view type."""
        # Set unsupported view type
        self.setSessionViewType(ViewType.CONFIGURATION)
        
        url = reverse('edit_item_details_close')
        response = self.client.get(url)

        # Should return BadRequest
        self.assertEqual(response.status_code, 400)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('edit_item_details_close')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestReorderItemsView(SyncViewTestCase):
    """
    Tests for ReorderItemsView - demonstrates item reordering delegation testing.
    This view handles reordering different types of items.
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
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    @patch('hi.apps.edit.views.CollectionReorderEntitiesView')
    def test_reorder_entities_in_collection(self, mock_view_class):
        """Test reordering entities within a collection."""
        from django.http import HttpResponse
        mock_view = mock_view_class.return_value
        mock_view.post.return_value = HttpResponse('mock_response')
        
        # Set collection context
        self.setSessionViewType(ViewType.COLLECTION)
        self.setSessionCollection(self.collection)
        
        url = reverse('edit_reorder_items')
        post_data = {
            'entity-1': '0',
            'entity-2': '1',
            'entity-3': '2',
        }
        _ = self.client.post(url, post_data)

        # Should delegate to CollectionReorderEntitiesView
        mock_view.post.assert_called_once()
        call_kwargs = mock_view.post.call_args[1]
        self.assertEqual(call_kwargs['collection_id'], self.collection.id)
        self.assertIn('[1, 2, 3]', call_kwargs['entity_id_list'])

    @patch('hi.apps.edit.views.CollectionReorder')
    def test_reorder_collections(self, mock_view_class):
        """Test reordering collections."""
        from django.http import HttpResponse
        mock_view = mock_view_class.return_value
        mock_view.post.return_value = HttpResponse('mock_response')
        
        url = reverse('edit_reorder_items')
        post_data = {
            'collection-1': '0',
            'collection-2': '1',
        }
        _ = self.client.post(url, post_data)

        # Should delegate to CollectionReorder
        mock_view.post.assert_called_once()
        call_kwargs = mock_view.post.call_args[1]
        self.assertIn('[1, 2]', call_kwargs['collection_id_list'])

    @patch('hi.apps.edit.views.LocationViewReorder')
    def test_reorder_location_views(self, mock_view_class):
        """Test reordering location views."""
        from django.http import HttpResponse
        mock_view = mock_view_class.return_value
        mock_view.post.return_value = HttpResponse('mock_response')
        
        url = reverse('edit_reorder_items')
        post_data = {
            'location_view-1': '0',
            'location_view-2': '1',
        }
        _ = self.client.post(url, post_data)

        # Should delegate to LocationViewReorder
        mock_view.post.assert_called_once()
        call_kwargs = mock_view.post.call_args[1]
        self.assertIn('[1, 2]', call_kwargs['location_view_id_list'])

    def test_reorder_entity_outside_collection_context(self):
        """Test that entity reordering outside collection context fails."""
        # Set non-collection context
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        url = reverse('edit_reorder_items')
        post_data = {
            'entity-1': '0',
            'entity-2': '1',
        }
        response = self.client.post(url, post_data)

        # Should return BadRequest
        self.assertEqual(response.status_code, 400)

    def test_reorder_mixed_item_types_fails(self):
        """Test that mixing item types in reorder fails."""
        url = reverse('edit_reorder_items')
        post_data = {
            'entity-1': '0',
            'collection-2': '1',  # Mixed types
        }
        response = self.client.post(url, post_data)

        # Should return BadRequest
        self.assertEqual(response.status_code, 400)

    def test_reorder_unknown_item_type_fails(self):
        """Test that unknown item types fail."""
        url = reverse('edit_reorder_items')
        post_data = {
            'unknown_type-1': '0',
        }
        response = self.client.post(url, post_data)

        # Should return BadRequest
        self.assertEqual(response.status_code, 400)

    def test_reorder_no_items_fails(self):
        """Test that reordering with no items fails."""
        url = reverse('edit_reorder_items')
        response = self.client.post(url, {})

        # Should return BadRequest
        self.assertEqual(response.status_code, 400)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('edit_reorder_items')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)


class TestEntityStateValueChoicesView(SyncViewTestCase):
    """
    Tests for EntityStateValueChoicesView - demonstrates JSON API testing.
    This view returns available choices for entity state values.
    """

    def setUp(self):
        super().setUp()
        # Create test entity and state
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
        )
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            key='power',
            entity_state_type_str='ON_OFF'
        )
        # Create test controller
        self.controller = Controller.objects.create(
            entity_state=self.entity_state,
            controller_type_str='SWITCH',
            integration_payload='{}'
        )

    def test_get_choices_for_entity_state(self):
        """Test getting choices for entity state instance."""
        url = reverse('entity_state_value_choices', kwargs={
            'instance_name': 'entity_state',
            'instance_id': str(self.entity_state.id)
        })
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Should return choices as JSON
        choices = response.json()
        self.assertIsInstance(choices, list)

    def test_get_choices_for_controller(self):
        """Test getting choices for controller instance."""
        url = reverse('entity_state_value_choices', kwargs={
            'instance_name': 'controller',
            'instance_id': str(self.controller.id)
        })
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Should return choices as JSON
        choices = response.json()
        self.assertIsInstance(choices, list)

    def test_get_choices_nonexistent_entity_state(self):
        """Test getting choices for nonexistent entity state."""
        url = reverse('entity_state_value_choices', kwargs={
            'instance_name': 'entity_state',
            'instance_id': '99999'
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_get_choices_nonexistent_controller(self):
        """Test getting choices for nonexistent controller."""
        url = reverse('entity_state_value_choices', kwargs={
            'instance_name': 'controller',
            'instance_id': '99999'
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_get_choices_unsupported_instance_name(self):
        """Test getting choices for unsupported instance name."""
        url = reverse('entity_state_value_choices', kwargs={
            'instance_name': 'unsupported',
            'instance_id': '1'
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    def test_get_choices_invalid_instance_id(self):
        """Test getting choices with invalid instance ID."""
        url = reverse('entity_state_value_choices', kwargs={
            'instance_name': 'entity_state',
            'instance_id': 'not_a_number'
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    def test_get_choices_missing_instance_name(self):
        """Test getting choices with missing instance name."""
        # This would normally be caught by URL routing, but test edge case
        url = reverse('entity_state_value_choices', kwargs={
            'instance_name': '',
            'instance_id': '1'
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('entity_state_value_choices', kwargs={
            'instance_name': 'entity_state',
            'instance_id': str(self.entity_state.id)
        })
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestEditHelpView(DualModeViewTestCase):
    """
    Tests for EditHelpView - demonstrates simple HiModalView testing.
    This view displays help information for edit mode.
    """

    def test_get_help_sync(self):
        """Test getting edit help with synchronous request."""
        url = reverse('edit_help')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'edit/modals/help.html')

    def test_get_help_async(self):
        """Test getting edit help with AJAX request."""
        url = reverse('edit_help')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('edit_help')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)
        
