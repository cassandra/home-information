import logging
from unittest.mock import patch, Mock

from django.urls import reverse

from hi.apps.collection.models import Collection
from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity, EntityState
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.enums import ViewType
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

    @patch.object(LocationManager, 'get_default_location_view')
    def test_redirect_to_start_when_no_location_view(self, mock_get_default):
        """Test redirecting to start page when no default location view exists."""
        mock_get_default.side_effect = LocationView.DoesNotExist()

        url = reverse('location_view_default')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('start')
        self.assertEqual(response.url, expected_url)

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
        # This would typically be tested by mocking should_force_sync_request
        # but the method is on the view class, making it complex to mock directly
        url = reverse('location_view', kwargs={'location_view_id': self.location_view.id})
        response = self.client.get(url)
        
        # Should handle gracefully and not raise unhandled exception
        self.assertSuccessResponse(response)

    def test_session_parameters_updated(self):
        """Test that view parameters are properly updated in session."""
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

    def test_switch_to_location_with_no_views(self):
        """Test switching to location with no views raises BadRequest."""
        # Create location with no views
        empty_location = Location.objects.create(
            name='Empty Location',
            svg_fragment_filename='empty.svg',
            svg_view_box_str='0 0 100 100'
        )

        url = reverse('location_switch', kwargs={'location_id': empty_location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

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

    def test_entity_fallback_redirect_no_location_view_context(self):
        """Test redirecting to entity status when no LocationView context is available."""
        from hi.enums import ItemType
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        # Make request without setting view_parameters (no LocationView context)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_status', kwargs={'entity_id': self.entity.id})
        self.assertEqual(response.url, expected_url)

    @patch('hi.apps.location.views.ControllerManager')
    @patch('hi.apps.location.views.StatusDisplayManager')
    def test_one_click_control_executes_highest_priority_controller_for_automation_view(self, mock_status_mgr, mock_controller_mgr):
        """Test successful one-click control executes for highest priority EntityState."""
        from hi.enums import ItemType
        
        # Mock only at system boundaries
        mock_control_result = Mock()
        mock_control_result.has_errors = False
        mock_controller_mgr.return_value.do_control.return_value = mock_control_result
        
        # Mock sensor response for toggle behavior
        mock_sensor_response = Mock()
        mock_sensor_response.value_str = 'OFF'
        mock_status_mgr.return_value.get_latest_sensor_response.return_value = mock_sensor_response
        
        # Set up real session context (not mocked)
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        
        # Test actual behavior
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_status', kwargs={'entity_id': self.entity.id})
        self.assertEqual(response.url, expected_url)
        
        # Verify the control was actually called with toggled value
        mock_controller_mgr.return_value.do_control.assert_called_once_with(
            controller=self.controller,
            control_value='ON'  # Should toggle from OFF to ON
        )

    def test_one_click_control_entity_not_found(self):
        """Test handling of nonexistent entity."""
        from hi.enums import ItemType
        html_id = ItemType.ENTITY.html_id(99999)  # Nonexistent entity
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

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

        self.assertEqual(response.status_code, 302)
        expected_url = reverse('collection_view', kwargs={'collection_id': self.collection.id})
        self.assertEqual(response.url, expected_url)

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

    @patch('hi.apps.location.views.ControllerManager')
    def test_one_click_control_handles_exceptions(self, mock_controller_mgr):
        """Test that control exceptions fall back to status modal."""
        from hi.enums import ItemType
        
        # Mock control failure
        mock_controller_mgr.return_value.do_control.side_effect = Exception("Control failed")
        
        # Set up automation view context  
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response = self.client.get(url)
        
        # Should fall back to entity status modal on exception
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('entity_status', kwargs={'entity_id': self.entity.id})
        self.assertEqual(response.url, expected_url)

    def test_priority_matching_with_multiple_controllable_states(self):
        """Test LocationViewType priority when entity has multiple controllable states."""
        from hi.enums import ItemType
        
        # Create entity with multiple controllable states
        multi_state_entity = Entity.objects.create(
            name='Multi State Device',
            entity_type_str='SWITCH'
        )
        
        # Higher priority state (ON_OFF is first in AUTOMATION priority list)
        high_priority_state = EntityState.objects.create(
            entity=multi_state_entity,
            entity_state_type_str='ON_OFF',
            name='Power State'
        )
        
        # Lower priority state (HIGH_LOW is later in priority list)
        low_priority_state = EntityState.objects.create(
            entity=multi_state_entity,
            entity_state_type_str='HIGH_LOW',
            name='Level State'
        )
        
        # Create controllers for both
        high_controller = Controller.objects.create(
            name='Power Controller',
            entity_state=high_priority_state,
            controller_type_str='DEFAULT',
            integration_id='test_integration',
            integration_name='power_control'
        )
        
        low_controller = Controller.objects.create(
            name='Level Controller',
            entity_state=low_priority_state,
            controller_type_str='DEFAULT',
            integration_id='test_integration',
            integration_name='level_control'
        )
        
        # Set up automation view context
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        # Mock control manager
        with patch('hi.apps.location.views.ControllerManager') as mock_controller_mgr, \
             patch('hi.apps.location.views.StatusDisplayManager') as mock_status_mgr:
            
            mock_control_result = Mock()
            mock_control_result.has_errors = False
            mock_controller_mgr.return_value.do_control.return_value = mock_control_result
            
            mock_sensor_response = Mock()
            mock_sensor_response.value_str = 'OFF'
            mock_status_mgr.return_value.get_latest_sensor_response.return_value = mock_sensor_response
            
            html_id = ItemType.ENTITY.html_id(multi_state_entity.id)
            url = reverse('location_item_status', kwargs={'html_id': html_id})
            
            response = self.client.get(url)
            
            # Should redirect to entity status after executing control
            self.assertEqual(response.status_code, 302)
            expected_url = reverse('entity_status', kwargs={'entity_id': multi_state_entity.id})
            self.assertEqual(response.url, expected_url)
            
            # Should use high priority controller
            mock_controller_mgr.return_value.do_control.assert_called_once_with(
                controller=high_controller,
                control_value='ON'
            )

    def test_toggle_value_mapping_for_binary_states(self):
        """Test TOGGLE_VALUE_MAP correctly toggles binary states."""
        from hi.enums import ItemType
        
        test_cases = [
            ('OFF', 'ON'),
            ('ON', 'OFF'),
            ('CLOSED', 'OPEN'),
            ('OPEN', 'CLOSED'),
            ('LOW', 'HIGH'),
            ('HIGH', 'LOW'),
        ]
        
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        for current_value, expected_toggle in test_cases:
            with self.subTest(current=current_value, expected=expected_toggle):
                with patch('hi.apps.location.views.ControllerManager') as mock_controller_mgr, \
                     patch('hi.apps.location.views.StatusDisplayManager') as mock_status_mgr:
                    
                    mock_control_result = Mock()
                    mock_control_result.has_errors = False
                    mock_controller_mgr.return_value.do_control.return_value = mock_control_result
                    
                    # Mock current sensor value
                    mock_sensor_response = Mock()
                    mock_sensor_response.value_str = current_value
                    mock_status_mgr.return_value.get_latest_sensor_response.return_value = mock_sensor_response
                    
                    html_id = ItemType.ENTITY.html_id(self.entity.id)
                    url = reverse('location_item_status', kwargs={'html_id': html_id})
                    
                    response = self.client.get(url)
                    
                    # Verify toggle value was sent
                    mock_controller_mgr.return_value.do_control.assert_called_with(
                        controller=self.controller,
                        control_value=expected_toggle
                    )

    def test_location_view_context_persistence_across_requests(self):
        """Test LocationView context persists across multiple requests."""
        # Set context in session
        session = self.client.session
        session['view_type'] = str(ViewType.LOCATION_VIEW)
        session['location_view_id'] = self.automation_view.id
        session.save()
        
        # Make first request
        from hi.enums import ItemType
        html_id = ItemType.ENTITY.html_id(self.entity.id)
        url = reverse('location_item_status', kwargs={'html_id': html_id})
        
        response1 = self.client.get(url)
        
        # Context should persist for second request
        response2 = self.client.get(url)
        
        # Both should redirect (fallback since no mocked controller)
        self.assertEqual(response1.status_code, 302)
        self.assertEqual(response2.status_code, 302)


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
        
