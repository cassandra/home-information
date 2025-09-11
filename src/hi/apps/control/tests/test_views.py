import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.control.controller_manager import ControllerManager
from hi.apps.control.models import Controller, ControllerHistory
from hi.apps.entity.models import Entity, EntityState
from hi.apps.entity.enums import EntityStateType, EntityStateValue
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestControllerView(SyncViewTestCase):
    """
    Tests for ControllerView - demonstrates controller action testing.
    This view handles POST requests to control devices.
    """

    def setUp(self):
        super().setUp()
        # Reset singleton managers for proper test isolation
        ControllerManager._instance = None
        ControllerHistoryManager._instance = None
        StatusDisplayManager._instance = None
        # Create test entity and controller
        self.entity = Entity.objects.create(
            name='Test Light',
            entity_type_str='LIGHT'
        )
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            name='power',
            entity_state_type_str='ON_OFF'
        )
        self.controller = Controller.objects.create(
            entity_state=self.entity_state,
            controller_type_str='SWITCH',
            integration_id='test_integration',
            integration_name='test_switch',
            integration_payload='{"device_id": "test_device"}'
        )

    @patch('hi.apps.control.controller_manager.IntegrationManager')
    def test_post_control_success(self, mock_integration_manager):
        """Test successful controller action."""
        from hi.integrations.transient_models import IntegrationControlResult
        
        # Mock at the system boundary - the integration gateway
        mock_manager = Mock()
        mock_integration_manager.return_value = mock_manager
        mock_gateway = Mock()
        mock_manager.get_integration_gateway.return_value = mock_gateway
        mock_gateway.get_controller.return_value.do_control.return_value = IntegrationControlResult(
            new_value='ON',
            error_list=[]
        )

        url = reverse('control_controller', kwargs={'controller_id': self.controller.id})
        response = self.client.post(url, {'value': 'ON'})

        # Should successfully execute control
        self.assertSuccessResponse(response)

    @patch.object(ControllerManager, 'do_control')
    @patch.object(StatusDisplayManager, 'add_entity_state_value_override')
    @patch.object(ControllerHistoryManager, 'add_to_controller_history')
    def test_post_control_with_errors(self, mock_add_history, mock_add_override, mock_do_control):
        """Test controller action with errors."""
        mock_result = Mock()
        mock_result.has_errors = True
        mock_result.error_list = ['Connection failed']
        mock_do_control.return_value = mock_result

        url = reverse('control_controller', kwargs={'controller_id': self.controller.id})
        response = self.client.post(url, {'value': 'ON'})

        self.assertSuccessResponse(response)
        mock_do_control.assert_called_once_with(
            controller=self.controller,
            control_value='ON'
        )
        # Should NOT add override or history when there are errors
        mock_add_override.assert_not_called()
        mock_add_history.assert_not_called()

    @patch.object(ControllerManager, 'do_control')
    def test_post_control_missing_value_checkbox(self, mock_do_control):
        """Test controller action with missing value (checkbox case)."""
        mock_result = Mock()
        mock_result.has_errors = False
        mock_result.error_list = []
        mock_do_control.return_value = mock_result

        url = reverse('control_controller', kwargs={'controller_id': self.controller.id})
        # POST without 'value' parameter (simulates unchecked checkbox)
        response = self.client.post(url, {})

        self.assertSuccessResponse(response)
        # Should use off as default for ON_OFF type (EntityStateValue enum returns lowercase)
        mock_do_control.assert_called_once_with(
            controller=self.controller,
            control_value='off'
        )

    def test_nonexistent_controller_returns_404(self):
        """Test that accessing nonexistent controller returns 404."""
        url = reverse('control_controller', kwargs={'controller_id': 99999})
        response = self.client.post(url, {'value': 'ON'})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('control_controller', kwargs={'controller_id': self.controller.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

    def test_missing_value_mapping(self):
        """Test that missing value mapping works for different entity state types."""
        from hi.apps.control.views import ControllerView
        view = ControllerView()
        
        # Test various entity state types
        test_cases = [
            (EntityStateType.MOVEMENT, EntityStateValue.IDLE),
            (EntityStateType.PRESENCE, EntityStateValue.IDLE),
            (EntityStateType.ON_OFF, EntityStateValue.OFF),
            (EntityStateType.OPEN_CLOSE, EntityStateValue.CLOSED),
            (EntityStateType.CONNECTIVITY, EntityStateValue.DISCONNECTED),
            (EntityStateType.HIGH_LOW, EntityStateValue.LOW),
        ]
        
        for state_type, expected_value in test_cases:
            with self.subTest(state_type=state_type):
                # Create controller with specific state type
                test_entity_state = Mock()
                test_entity_state.entity_state_type = state_type
                test_controller = Mock()
                test_controller.entity_state = test_entity_state
                
                result = view._get_value_for_missing_input(test_controller)
                self.assertEqual(result, str(expected_value))


class TestControllerHistoryView(DualModeViewTestCase):
    """
    Tests for ControllerHistoryView - demonstrates HiModalView with pagination testing.
    This view displays the history of controller actions.
    """

    def setUp(self):
        super().setUp()
        # Create test entity and controller
        self.entity = Entity.objects.create(
            name='Test Switch',
            entity_type_str='SWITCH'
        )
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            name='state',
            entity_state_type_str='ON_OFF'
        )
        self.controller = Controller.objects.create(
            entity_state=self.entity_state,
            controller_type_str='SWITCH',
            integration_payload='{"device_id": "test_switch"}'
        )
        
        # Create some test history entries
        for i in range(5):
            ControllerHistory.objects.create(
                controller=self.controller,
                value=f'test_value_{i}',
                created_datetime=f'2023-01-0{i+1}T12:00:00Z'
            )

    def test_get_controller_history_sync(self):
        """Test getting controller history with synchronous request."""
        url = reverse('control_controller_history', kwargs={'controller_id': self.controller.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'control/modals/controller_history.html')

    def test_get_controller_history_async(self):
        """Test getting controller history with AJAX request."""
        url = reverse('control_controller_history', kwargs={'controller_id': self.controller.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_controller_and_history_in_context(self):
        """Test that controller and history are passed to template context."""
        url = reverse('control_controller_history', kwargs={'controller_id': self.controller.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['controller'], self.controller)
        self.assertIn('controller_history_list', response.context)
        self.assertIn('pagination', response.context)

    def test_pagination_context(self):
        """Test that pagination is properly configured."""
        url = reverse('control_controller_history', kwargs={'controller_id': self.controller.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        pagination = response.context['pagination']
        self.assertIsNotNone(pagination)
        # Should have base URL for controller history
        self.assertIn(str(self.controller.id), pagination.base_url)

    def test_history_filtered_by_controller(self):
        """Test that history is filtered to only this controller."""
        # Create another controller with history
        other_entity = Entity.objects.create(
            name='Other Device',
            entity_type_str='LIGHT'
        )
        other_entity_state = EntityState.objects.create(
            entity=other_entity,
            name='brightness',
            entity_state_type_str='NUMERIC'
        )
        other_controller = Controller.objects.create(
            entity_state=other_entity_state,
            controller_type_str='DIMMER',
            integration_payload='{"device_id": "other_device"}'
        )
        ControllerHistory.objects.create(
            controller=other_controller,
            value='other_value',
            created_datetime='2023-01-10T12:00:00Z'
        )

        url = reverse('control_controller_history', kwargs={'controller_id': self.controller.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        history_list = response.context['controller_history_list']
        
        # All history entries should belong to our controller
        for history_entry in history_list:
            self.assertEqual(history_entry.controller, self.controller)

    def test_nonexistent_controller_returns_404(self):
        """Test that accessing nonexistent controller returns 404."""
        url = reverse('control_controller_history', kwargs={'controller_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_pagination_with_many_entries(self):
        """Test pagination when there are many history entries."""
        # Create many more history entries to test pagination
        for i in range(50):
            ControllerHistory.objects.create(
                controller=self.controller,
                value=f'bulk_value_{i}',
                created_datetime=f'2023-02-{(i % 28) + 1:02d}T12:00:00Z'
            )

        url = reverse('control_controller_history', kwargs={'controller_id': self.controller.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        history_list = response.context['controller_history_list']
        
        # Should be limited by page size (25)
        self.assertLessEqual(len(history_list), 25)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('control_controller_history', kwargs={'controller_id': self.controller.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)
        
