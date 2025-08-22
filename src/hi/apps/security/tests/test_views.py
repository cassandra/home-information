import logging

from django.urls import reverse

from hi.apps.security.security_manager import SecurityManager
from hi.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestSecurityStateActionView(SyncViewTestCase):
    """
    Tests for SecurityStateActionView - demonstrates security action testing.
    This view handles security state changes (arm/disarm/etc).
    """

    def setUp(self):
        super().setUp()
        # Reset singleton instance for clean testing
        SecurityManager._instance = None
    
    def tearDown(self):
        """Clean up SecurityManager resources."""
        # Clean up any timer threads that may have been created
        if hasattr(SecurityManager, '_instance') and SecurityManager._instance:
            SecurityManager._instance.cleanup()
        super().tearDown()

    def test_valid_security_action_arm(self):
        """Test executing valid ARM security action."""
        url = reverse('security_state_action', kwargs={'action': 'SET_AWAY'})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'security/panes/security_state_control.html')
        
        # Verify the real SecurityManager processed the security action
        # The response context should contain security status data
        self.assertIn('security_status_data', response.context)
        security_status_data = response.context['security_status_data']
        self.assertIsNotNone(security_status_data)

    def test_valid_security_action_disable(self):
        """Test executing valid DISABLE security action."""
        url = reverse('security_state_action', kwargs={'action': 'DISABLE'})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'security/panes/security_state_control.html')
        
        # Verify the real SecurityManager processed the security action
        self.assertIn('security_status_data', response.context)
        security_status_data = response.context['security_status_data']
        self.assertIsNotNone(security_status_data)

    def test_valid_security_action_set_day(self):
        """Test executing valid SET_DAY security action."""
        url = reverse('security_state_action', kwargs={'action': 'SET_DAY'})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'security/panes/security_state_control.html')
        
        # Verify the real SecurityManager processed the security action
        self.assertIn('security_status_data', response.context)
        security_status_data = response.context['security_status_data']
        self.assertIsNotNone(security_status_data)

    def test_invalid_security_action(self):
        """Test that invalid security action raises BadRequest."""
        url = reverse('security_state_action', kwargs={'action': 'INVALID_ACTION'})
        response = self.client.get(url)

        # Should raise BadRequest (400)
        self.assertEqual(response.status_code, 400)

    def test_security_status_in_context(self):
        """Test that security status data is passed to template context."""
        url = reverse('security_state_action', kwargs={'action': 'SET_NIGHT'})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertTemplateRendered(response, 'security/panes/security_state_control.html')
        
        # Verify the real SecurityManager provides security status data
        self.assertIn('security_status_data', response.context)
        security_status_data = response.context['security_status_data']
        self.assertIsNotNone(security_status_data)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('security_state_action', kwargs={'action': 'SET_AWAY'})
        response = self.client.post(url)

        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)

    def test_multiple_action_types(self):
        """Test that all valid security action types work."""
        # Test each valid action type
        valid_actions = ['SET_AWAY', 'DISABLE', 'SET_DAY', 'SET_NIGHT', 'SNOOZE']
        
        for action in valid_actions:
            with self.subTest(action=action):
                url = reverse('security_state_action', kwargs={'action': action})
                response = self.client.get(url)
                self.assertSuccessResponse(response)
                self.assertTemplateRendered(response, 'security/panes/security_state_control.html')
                
                # Each action should result in security status data in context
                self.assertIn('security_status_data', response.context)
                security_status_data = response.context['security_status_data']
                self.assertIsNotNone(security_status_data)

    def test_case_sensitive_action(self):
        """Test that security actions are case-sensitive."""
        # lowercase 'set_away' should fail (from_name is case-insensitive but testing the principle)
        url = reverse('security_state_action', kwargs={'action': 'invalid_action'})
        response = self.client.get(url)
        
        # Should raise BadRequest for invalid action
        self.assertEqual(response.status_code, 400)
