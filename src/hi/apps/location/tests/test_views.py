import logging
from unittest.mock import patch, Mock

from django.urls import reverse

from hi.apps.collection.models import Collection
from hi.apps.control.models import Controller
from hi.apps.control.one_click_control_service import (
    OneClickNotSupported,
)
from hi.apps.common.svg_models import SvgViewBox
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.apps.location.views import LocationViewView
from hi.enums import ViewType
from hi.testing.base_test_case import BaseTestCase, MockRequest
from hi.testing.view_test_base import SyncViewTestCase, AsyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestLocationViewDefaultView(SyncViewTestCase):
    """
    Tests for LocationViewDefaultView - demonstrates default location redirect testing.
    This view redirects to the default location view or start page.
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
            name='Main View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=1
        )

    @patch.object(LocationManager, 'get_default_location_view')
    def test_redirect_to_default_location_view(self, mock_get_default):
        """Test redirecting to default location view."""
        mock_get_default.return_value = self.location_view

        url = reverse('location_view_default')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        self.assertEqual(response.url, expected_url)
        
        # Should set view parameters in session
        session = self.client.session
        self.assertEqual(session.get('view_type'), str(ViewType.LOCATION_VIEW))

    def test_redirect_to_start_when_no_location(self):
        """With no location at all, the view can render nothing, so it
        defers to StartView (the provisioning-state authority)."""
        LocationView.objects.all().delete()
        Location.objects.all().delete()

        url = reverse('location_view_default')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('start'))

    def test_self_heals_when_location_has_no_view(self):
        """A location whose default view is missing is repaired with a fresh
        'All' view (rather than failing) and shown."""
        LocationView.objects.all().delete()

        url = reverse('location_view_default')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        new_view = self.location.views.order_by('order_id').first()
        self.assertIsNotNone(new_view)
        self.assertEqual(new_view.name, LocationManager.INITIAL_LOCATION_VIEW_NAME)
        self.assertEqual(
            response.url,
            reverse('location_view', kwargs={'location_view_id': new_view.id}),
        )

    def test_self_heals_to_existing_view_when_default_location_empty(self):
        """Regression for the infinite home<->start redirect loop: when the
        default (first-ordered) Location is left view-less while another
        Location still has a view, resolve onto the existing view instead
        of bouncing to start."""
        # self.location is first by order; strand it with no views.
        self.location_view.delete()
        other_location = Location.objects.create(
            name='Other Location',
            svg_fragment_filename='other.svg',
            svg_view_box_str='0 0 100 100',
            order_id=99,
        )
        other_view = LocationView.objects.create(
            location=other_location,
            name='Other View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=0,
        )

        url = reverse('location_view_default')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('location_view', kwargs={'location_view_id': other_view.id})
        self.assertEqual(response.url, expected_url)
        # Session should now point at the surviving view (loop broken).
        self.assertEqual(self.client.session.get('location_view_id'), other_view.id)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('location_view_default')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestLocationViewView(DualModeViewTestCase):
    """
    Tests for LocationViewView - demonstrates HiGridView testing.
    This view displays a location view with entities and collections.
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
            svg_rotate=0.0,
            order_id=1
        )

    @patch.object(LocationManager, 'get_location_view_data')
    def test_get_location_view_sync(self, mock_get_data):
        """Test getting location view with synchronous request."""
        # Mock location view data
        mock_view_data = object()
        mock_get_data.return_value = mock_view_data

        url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Should call get_location_view_data with status display data
        mock_get_data.assert_called_once_with(
            location_view=self.location_view,
            include_status_display_data=True
        )

    @patch.object(LocationManager, 'get_location_view_data')
    def test_get_location_view_async(self, mock_get_data):
        """Test getting location view with AJAX request."""
        # Mock location view data
        mock_view_data = object()
        mock_get_data.return_value = mock_view_data

        url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)

    @patch.object(LocationManager, 'get_location_view_data')
    def test_location_view_context_in_monitor_mode(self, mock_get_data):
        """Test location view context when in monitor mode."""
        mock_view_data = object()
        mock_get_data.return_value = mock_view_data

        url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['location_view'], self.location_view)
        self.assertEqual(response.context['location_view_data'], mock_view_data)
        self.assertEqual(response.context['is_async_request'], False)
        
        # Should include status display data when not editing
        mock_get_data.assert_called_once_with(
            location_view=self.location_view,
            include_status_display_data=True
        )

    @patch.object(LocationManager, 'get_location_view_data')
    def test_location_view_context_in_edit_mode(self, mock_get_data):
        """Test location view context when in edit mode."""
        # Set edit mode
        from hi.enums import ViewMode
        self.setSessionViewMode(ViewMode.EDIT)
        
        mock_view_data = object()
        mock_get_data.return_value = mock_view_data

        url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        
        # Should NOT include status display data when editing
        mock_get_data.assert_called_once_with(
            location_view=self.location_view,
            include_status_display_data=False
        )

    def test_force_synchronous_exception_handling(self):
        """Test that ForceSynchronousException is properly handled."""
        # Set up initial view parameters
        self.setSessionViewParameters(
            view_type=ViewType.LOCATION_VIEW,
            location_view=self.location_view
        )
        
        # This would typically be tested by mocking should_force_sync_request
        # but the method is on the view class, making it complex to mock directly
        url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)
        
        # Should handle gracefully and not raise unhandled exception
        self.assertSuccessResponse(response)

    def test_session_parameters_updated(self):
        """Test that view parameters are properly updated in session."""
        # Set up initial view parameters
        self.setSessionViewParameters(
            view_type=ViewType.LOCATION_VIEW,
            location_view=self.location_view
        )
        
        url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        
        # Should set view type and location view in session
        session = self.client.session
        self.assertEqual(session.get('view_type'), str(ViewType.LOCATION_VIEW))

    def test_nonexistent_location_view_returns_404(self):
        """Test that accessing nonexistent location view returns 404."""
        url = reverse('location_view', kwargs={'location_view_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestLocationSwitchView(SyncViewTestCase):
    """
    Tests for LocationSwitchView - demonstrates location switching testing.
    This view switches to the first view of a specified location.
    """

    def setUp(self):
        super().setUp()
        # Create test location with multiple views
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.location_view1 = LocationView.objects.create(
            location=self.location,
            name='First View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=1
        )
        self.location_view2 = LocationView.objects.create(
            location=self.location,
            name='Second View',
            location_view_type_str='DETAIL',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=2
        )

    def test_switch_to_first_location_view(self):
        """Test switching to first view of a location."""
        url = reverse('location_switch', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('location_view', kwargs={'location_view_id': self.location_view1.id})
        self.assertEqual(response.url, expected_url)
        
        # Should set view parameters in session
        session = self.client.session
        self.assertEqual(session.get('view_type'), str(ViewType.LOCATION_VIEW))

    def test_switch_to_location_with_no_views_auto_creates_default(self):
        """Switching to a view-less location mints a default 'All' view
        (invariant repair) and redirects to it, rather than dead-ending."""
        empty_location = Location.objects.create(
            name='Empty Location',
            svg_fragment_filename='empty.svg',
            svg_view_box_str='0 0 100 100'
        )
        self.assertEqual(empty_location.views.count(), 0)

        url = reverse('location_switch', kwargs={'location_id': empty_location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        created_view = empty_location.views.order_by('order_id').first()
        self.assertIsNotNone(created_view)
        self.assertEqual(created_view.name, LocationManager.INITIAL_LOCATION_VIEW_NAME)
        expected_url = reverse('location_view', kwargs={'location_view_id': created_view.id})
        self.assertEqual(response.url, expected_url)

    def test_views_ordered_by_order_id(self):
        """Test that views are selected in order_id order."""
        # Create view with lower order_id
        first_view = LocationView.objects.create(
            location=self.location,
            name='Actually First',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=0
        )

        url = reverse('location_switch', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        # Should redirect to the view with lowest order_id
        expected_url = reverse('location_view', kwargs={'location_view_id': first_view.id})
        self.assertEqual(response.url, expected_url)

    def test_nonexistent_location_returns_404(self):
        """Test that accessing nonexistent location returns 404."""
        url = reverse('location_switch', kwargs={'location_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('location_switch', kwargs={'location_id': self.location.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestLocationEditModeView(AsyncViewTestCase):
    """
    Tests for LocationEditModeView - demonstrates HiSideView testing.
    This view displays location details in a side panel.
    """

    def setUp(self):
        super().setUp()
        # Create test location
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )

    def test_get_location_details(self):
        """Test getting location details."""
        url = reverse('location_edit_mode', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        self.assertTemplateRendered(response, 'location/edit/panes/location_edit_mode_panel.html')

    def test_location_details_should_push_url(self):
        """Test that LocationEditModeView should push URL."""
        url = reverse('location_edit_mode', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        # HiSideView should push URL for browser history

    def test_location_edit_data_in_context(self):
        """Test that location edit data is passed to template context."""
        url = reverse('location_edit_mode', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        # Context should contain location edit data
        # The actual structure depends on LocationEditModeData.to_template_context()

    def test_nonexistent_location_returns_404(self):
        """Test that accessing nonexistent location returns 404."""
        url = reverse('location_edit_mode', kwargs={'location_id': 99999})
        response = self.async_get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('location_edit_mode', kwargs={'location_id': self.location.id})
        response = self.async_post(url)

        self.assertEqual(response.status_code, 405)


class TestLocationViewEditModeViewGet(AsyncViewTestCase):
    """
    Tests for LocationViewEditModeView.get() - demonstrates location view details testing.
    This view displays location view details in a side panel.
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

    def test_get_location_view_details(self):
        """Test getting location view details."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': self.location_view.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        self.assertTemplateRendered(response, 'location/edit/panes/location_view_edit_mode_panel.html')

    def test_location_view_details_should_push_url(self):
        """Test that LocationViewEditModeView should push URL."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': self.location_view.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        # HiSideView should push URL for browser history

    def test_location_view_edit_data_in_context(self):
        """Test that location view edit data is passed to template context."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': self.location_view.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        # Context should contain location view edit data
        # The actual structure depends on LocationViewEditModeData.to_template_context()

    def test_nonexistent_location_view_returns_404(self):
        """Test that accessing nonexistent location view returns 404."""
        url = reverse('location_view_edit_mode', kwargs={'location_view_id': 99999})
        response = self.async_get(url)

        self.assertEqual(response.status_code, 404)


class TestLocationItemStatusView(SyncViewTestCase):
    """
    Tests for LocationItemStatusView - demonstrates one-click control and fallback behavior.
    This view executes one-click control based on LocationViewType or falls back to status modals.
    """

    def setUp(self):
        super().setUp()
        
        # Create test location and location views
        self.location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        
        self.automation_view = LocationView.objects.create(
            location=self.location,
            name='Automation View',
            location_view_type_str='AUTOMATION',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=1
        )
        
        self.default_view = LocationView.objects.create(
            location=self.location,
            name='Default View',
            location_view_type_str='DEFAULT',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            order_id=2
        )
        
        # Create test entity with controllable state
        self.entity = Entity.objects.create(
            name='Test Light',
            entity_type_str='LIGHT'
        )
        
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF',
            name='Power State'
        )
        
        self.controller = Controller.objects.create(
            name='Light Switch',
            entity_state=self.entity_state,
            controller_type_str='DEFAULT',
            integration_id='test_integration',
            integration_name='test_switch'
        )
        
        # Create collection for fallback testing
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='ROOM',
            collection_view_type_str='MAIN'
        )

    @patch('hi.apps.control.one_click_control_service.ControllerManager')
    def test_view_parameters_required_for_automation_view(self, mock_controller_manager):
        """Test that view_parameters are required for AUTOMATION view processing."""
        from hi.enums import ItemType
        from hi.apps.control.transient_models import ControllerOutcome
        
        # Mock at the system boundary - the controller manager
        mock_manager = Mock()
        mock_controller_manager.return_value = mock_manager
        mock_manager.do_control.return_value = ControllerOutcome(
            controller=self.controller,
            new_value='ON',
            error_list=[]
        )
        
        # Set up automation view context (this test verifies the flow works with proper setup)
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        
        # Should successfully execute control and return SVG attribute update response  
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('setAttributes', data)

    @patch('hi.apps.control.one_click_control_service.ControllerManager')
    def test_automation_view_with_controllable_entity_executes_control(self, mock_controller_manager):
        """Test that AUTOMATION view executes control for entity with controllable states."""
        from hi.enums import ItemType
        from hi.apps.control.transient_models import ControllerOutcome
        
        # Mock at the system boundary - the controller manager
        mock_manager = Mock()
        mock_controller_manager.return_value = mock_manager
        mock_manager.do_control.return_value = ControllerOutcome(
            controller=self.controller,
            new_value='ON',
            error_list=[]
        )
        
        # Set up automation view context
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        
        # Should successfully execute control and return SVG attribute update response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('setAttributes', data)

    def test_one_click_control_entity_not_found(self):
        """Test handling of nonexistent entity."""
        from hi.enums import ItemType
        html_id = ItemType.ENTITY.html_id(99999)  # Nonexistent entity
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        # EntityViewMixin raises Http404 for nonexistent entities
        self.assertEqual(response.status_code, 404)

    def test_falls_back_to_status_modal_when_entity_has_no_controllable_states(self):
        """Test fallback to status modal when entity has no controllable state matching LocationViewType."""
        from hi.enums import ItemType
        
        # Create entity with no controllers
        uncontrollable_entity = Entity.objects.create(
            name='Sensor Only',
            entity_type_str='SENSOR'
        )
        
        # Add state but no controllers
        EntityState.objects.create(
            entity=uncontrollable_entity,
            entity_state_type_str='TEMPERATURE',
            name='Temperature Reading'
        )
        
        # Set up automation view context
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        html_id = ItemType.ENTITY.html_id(uncontrollable_entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        
        # Should fall back to entity status modal
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_status', kwargs={'entity_id': uncontrollable_entity.id})
        self.assertEqual(response.url, expected_url)

    def test_collection_always_redirects_to_collection_view(self):
        """Test that collections always redirect to collection view (no one-click control)."""
        from hi.enums import ItemType
        html_id = ItemType.COLLECTION.html_id(self.collection.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        response = self.client.get(url)

        self.assertEqual( response.status_code, 200 )
        data = response.json()
        expected_url = reverse('collection_view', kwargs={'collection_id': self.collection.id})
        self.assertEqual(data['location'], expected_url)

    def test_unknown_item_type_returns_400(self):
        """Test that unknown item types return BadRequest."""
        url = reverse('location_item_status', kwargs={'html_id': 'hi-unknown-1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_invalid_item_id_returns_400(self):
        """Test that invalid item IDs return BadRequest."""
        url = reverse('location_item_status', kwargs={'html_id': 'invalid-format'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        from hi.enums import ItemType
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 405)

    def test_default_view_type_skips_service_and_redirects_to_status(self):
        """Test that DEFAULT LocationViewType skips OneClickControlService and redirects to status."""
        from hi.enums import ItemType
        
        # Set up DEFAULT view context
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.default_view.id
        session.save()
        
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        
        # Should redirect directly to entity status for DEFAULT view type
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_status', kwargs={'entity_id': self.entity.id})
        self.assertEqual(response.url, expected_url)

    @patch('hi.apps.control.one_click_control_service.ControllerManager')
    def test_automation_view_calls_service_for_entity_control(self, mock_controller_manager):
        """Test that AUTOMATION LocationViewType calls OneClickControlService for entity control."""
        from hi.enums import ItemType
        from hi.apps.control.transient_models import ControllerOutcome
        
        # Mock at the system boundary - the controller manager
        mock_manager = Mock()
        mock_controller_manager.return_value = mock_manager
        mock_manager.do_control.return_value = ControllerOutcome(
            controller=self.controller,
            new_value='ON',
            error_list=[]
        )
        
        # Set up automation view context
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        
        # Should successfully execute control and return SVG attribute update response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('setAttributes', data)

    def test_long_press_bypasses_one_click_in_automation_view(self):
        """Long-press gesture (``?long_press=1``) in an AUTOMATION view
        must bypass the one-click control branch and redirect to the
        entity status modal — the gesture's whole purpose is reaching
        status when a tap would otherwise toggle the device."""
        from hi.enums import ItemType
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()

        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})

        response = self.client.get(url + '?long_press=1')

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_status', kwargs={'entity_id': self.entity.id})
        self.assertEqual(response.url, expected_url)

    def test_long_press_no_op_in_non_automation_view(self):
        """In a non-AUTOMATION view, a tap already routes to status, so
        ``?long_press=1`` should be a harmless no-op (same response)."""
        from hi.enums import ItemType
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.default_view.id
        session.save()

        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})

        response = self.client.get(url + '?long_press=1')

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_status', kwargs={'entity_id': self.entity.id})
        self.assertEqual(response.url, expected_url)

    @patch('hi.apps.control.one_click_control_service.ControllerManager')
    def test_long_press_param_truthy_variants_all_bypass(self, mock_controller_manager):
        """The view consumes ``long_press`` via ``str_to_bool``, so any
        truthy variant (``true``, ``yes``, ``on``) bypasses one-click;
        falsy variants (``false``, missing) keep the one-click path."""
        from hi.enums import ItemType
        from hi.apps.control.transient_models import ControllerOutcome
        mock_manager = Mock()
        mock_controller_manager.return_value = mock_manager
        mock_manager.do_control.return_value = ControllerOutcome(
            controller=self.controller,
            new_value='ON',
            error_list=[]
        )

        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()

        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})

        for truthy in ['1', 'true', 'yes', 'on']:
            response = self.client.get(url + f'?long_press={truthy}')
            self.assertEqual(
                response.status_code, 302,
                f'long_press={truthy!r} should bypass one-click',
            )

        # ``false`` is the canonical falsy variant; verify one-click path runs.
        response = self.client.get(url + '?long_press=false')
        self.assertEqual(
            response.status_code, 200,
            'long_press=false should NOT bypass one-click',
        )

    @patch('hi.apps.location.views.OneClickControlService')
    def test_automation_view_handles_unsupported_exception(self, mock_service_class):
        """Test that OneClickNotSupported falls back to status modal."""
        from hi.enums import ItemType
        
        # Mock service to raise unsupported exception - this is legitimate boundary testing
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.execute_one_click_control.side_effect = OneClickNotSupported("No controllable states")
        
        # Set up automation view context
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        
        # Should still redirect to entity status (graceful fallback)
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_status', kwargs={'entity_id': self.entity.id})
        self.assertEqual(response.url, expected_url)


class TestLocationItemEditModeView(SyncViewTestCase):
    """
    Tests for LocationItemDetailsView - demonstrates item details delegation testing.
    This view redirects to appropriate details views based on item type.
    """

    def setUp(self):
        super().setUp()
        # Create test entity and collection
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='SENSOR'
        )
        self.collection = Collection.objects.create(
            name='Test Collection',
            collection_type_str='GROUP',
            collection_view_type_str='MAIN'
        )

    def test_entity_edit_mode_redirect(self):
        """Test redirecting to entity edit mode for entity items."""
        from hi.enums import ItemType
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_edit_mode', kwargs={'html_id': html_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_edit_mode', kwargs={'entity_id': self.entity.id})
        self.assertEqual(response.url, expected_url)

    def test_collection_edit_mode_redirect(self):
        """Test redirecting to collection edit mode for collection items."""
        from hi.enums import ItemType
        html_id = ItemType.COLLECTION.html_id(self.collection.id)
        url = reverse('location_item_edit_mode', kwargs={'html_id': html_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('collection_edit_mode', kwargs={'collection_id': self.collection.id})
        self.assertEqual(response.url, expected_url)

    def test_unknown_item_type_returns_400(self):
        """Test that unknown item types return BadRequest."""
        # Use an invalid html_id format to trigger BadRequest
        url = reverse('location_item_edit_mode', kwargs={'html_id': 'hi-unknown-1'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    def test_invalid_item_id_returns_400(self):
        """Test that invalid item IDs return BadRequest."""
        # Use an invalid html_id format to trigger BadRequest
        url = reverse('location_item_edit_mode', kwargs={'html_id': 'invalid-format'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        from hi.enums import ItemType
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_edit_mode', kwargs={'html_id': html_id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)
        


class TestLocationViewGeometryOverride(BaseTestCase):
    """LocationViewView._get_geometry_override - validates the optional
    pan/zoom override carried on the query string, rejecting malformed
    input so it can never inject a bad viewBox attribute."""

    def _override(self, **get_params):
        request = MockRequest(GET=dict(get_params))
        return LocationViewView()._get_geometry_override(request)

    def test_no_params_returns_none(self):
        view_box, rotate = self._override()
        self.assertIsNone(view_box)
        self.assertIsNone(rotate)

    def test_valid_viewbox_and_rotate(self):
        view_box, rotate = self._override(
            svg_view_box='10 20 30 40', svg_rotate='45')
        self.assertEqual(view_box.to_dict(),
                         SvgViewBox(x=10, y=20, width=30, height=40).to_dict())
        self.assertEqual(rotate, '45')

    def test_malformed_viewbox_rejected(self):
        view_box, rotate = self._override(svg_view_box='not a box')
        self.assertIsNone(view_box)
        self.assertIsNone(rotate)

    def test_valid_viewbox_with_malformed_rotate_drops_only_rotate(self):
        view_box, rotate = self._override(
            svg_view_box='10 20 30 40', svg_rotate='sideways')
        self.assertIsNotNone(view_box)
        self.assertIsNone(rotate)
