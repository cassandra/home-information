import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.control.controller_history_manager import ControllerHistoryManager
from hi.apps.control.controller_manager import ControllerManager
from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity, EntityState
from hi.apps.entity.enums import EntityStateType, EntityStateValue
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.testing.view_test_base import SyncViewTestCase

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
        mock_gateway.get_connector.return_value.get_controller.return_value.do_control.return_value = IntegrationControlResult(
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
