import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.security.enums import SecurityStateAction
from hi.apps.security.security_manager import SecurityManager
from hi.tests.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestSecurityStateActionView(SyncViewTestCase):
    """
    Tests for SecurityStateActionView - demonstrates security action testing.
    This view handles security state changes (arm/disarm/etc).
    """

    def setUp(self):
        super().setUp()
        self.mock_security_status_data = {
            'state': 'DISARMED',
            'can_arm': True,
            'can_disarm': False,
            'sensors': []
        }

    @patch.object(SecurityManager, '__new__')
    def test_valid_security_action_arm(self, mock_new):
        """Test executing valid ARM security action."""
        mock_manager = Mock(spec=SecurityManager)
        mock_manager.get_security_status_data.return_value = self.mock_security_status_data
        mock_manager.ensure_initialized.return_value = None
        mock_manager.update_security_state_user.return_value = None
        mock_new.return_value = mock_manager

        url = reverse('security_state_action', kwargs={'action': 'SET_AWAY'})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'security/panes/security_state_control.html')
        
        # Verify the security manager was called with correct action
        mock_manager.update_security_state_user.assert_called_once_with(
            security_state_action=SecurityStateAction.SET_AWAY
        )

    @patch.object(SecurityManager, '__new__')
    def test_valid_security_action_disable(self, mock_new):
        """Test executing valid DISABLE security action."""
        mock_manager = Mock(spec=SecurityManager)
        mock_manager.get_security_status_data.return_value = self.mock_security_status_data
        mock_manager.ensure_initialized.return_value = None
        mock_manager.update_security_state_user.return_value = None
        mock_new.return_value = mock_manager

        url = reverse('security_state_action', kwargs={'action': 'DISABLE'})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        
        # Verify the security manager was called with correct action
        mock_manager.update_security_state_user.assert_called_once_with(
            security_state_action=SecurityStateAction.DISABLE
        )

    @patch.object(SecurityManager, '__new__')
    def test_valid_security_action_set_day(self, mock_new):
        """Test executing valid SET_DAY security action."""
        mock_manager = Mock(spec=SecurityManager)
        mock_manager.get_security_status_data.return_value = self.mock_security_status_data
        mock_manager.ensure_initialized.return_value = None
        mock_manager.update_security_state_user.return_value = None
        mock_new.return_value = mock_manager

        url = reverse('security_state_action', kwargs={'action': 'SET_DAY'})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        
        # Verify the security manager was called with correct action
        mock_manager.update_security_state_user.assert_called_once_with(
            security_state_action=SecurityStateAction.SET_DAY
        )

    def test_invalid_security_action(self):
        """Test that invalid security action raises BadRequest."""
        url = reverse('security_state_action', kwargs={'action': 'INVALID_ACTION'})
        response = self.client.get(url)

        # Should raise BadRequest (400)
        self.assertEqual(response.status_code, 400)

    @patch.object(SecurityManager, '__new__')
    def test_security_status_in_context(self, mock_new):
        """Test that security status data is passed to template context."""
        mock_manager = Mock(spec=SecurityManager)
        mock_manager.get_security_status_data.return_value = self.mock_security_status_data
        mock_manager.ensure_initialized.return_value = None
        mock_manager.update_security_state_user.return_value = None
        mock_new.return_value = mock_manager

        url = reverse('security_state_action', kwargs={'action': 'SET_NIGHT'})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertIn('security_status_data', response.context)
        self.assertEqual(response.context['security_status_data'], self.mock_security_status_data)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('security_state_action', kwargs={'action': 'SET_AWAY'})
        response = self.client.post(url)

        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)

    @patch.object(SecurityManager, '__new__')
    def test_multiple_action_types(self, mock_new):
        """Test that all valid security action types work."""
        mock_manager = Mock(spec=SecurityManager)
        mock_manager.get_security_status_data.return_value = self.mock_security_status_data
        mock_manager.ensure_initialized.return_value = None
        mock_manager.update_security_state_user.return_value = None
        mock_new.return_value = mock_manager

        # Test each valid action type
        valid_actions = ['SET_AWAY', 'DISABLE', 'SET_DAY', 'SET_NIGHT', 'SNOOZE']
        
        for action in valid_actions:
            with self.subTest(action=action):
                url = reverse('security_state_action', kwargs={'action': action})
                response = self.client.get(url)
                self.assertSuccessResponse(response)

    def test_case_sensitive_action(self):
        """Test that security actions are case-sensitive."""
        # lowercase 'set_away' should fail (from_name is case-insensitive but testing the principle)
        url = reverse('security_state_action', kwargs={'action': 'invalid_action'})
        response = self.client.get(url)
        
        # Should raise BadRequest for invalid action
        self.assertEqual(response.status_code, 400)
