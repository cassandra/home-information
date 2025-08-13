import logging

from hi.apps.security.enums import SecurityLevel, SecurityState, SecurityStateAction
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSecurityLevel(BaseTestCase):

    def test_security_level_non_off_choices_filtering(self):
        """Test non_off_choices method - critical for UI form generation."""
        choices = SecurityLevel.non_off_choices()
        
        # Should exclude OFF level
        choice_values = [choice[0] for choice in choices]
        self.assertNotIn('off', choice_values)
        
        # Should include HIGH and LOW
        self.assertIn('high', choice_values)
        self.assertIn('low', choice_values)
        
        # Should return list of tuples with proper format
        for choice in choices:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            self.assertIsInstance(choice[0], str)  # value
            self.assertIsInstance(choice[1], str)  # label
        return

    def test_security_level_choice_format(self):
        """Test choice format consistency - important for form integration."""
        choices = SecurityLevel.non_off_choices()
        
        # Should have lowercase values and proper labels
        expected_mapping = {
            'high': 'High',
            'low': 'Low'
        }
        
        for value, label in choices:
            self.assertIn(value, expected_mapping)
            self.assertEqual(label, expected_mapping[value])
        return


class TestSecurityState(BaseTestCase):

    def test_security_state_auto_change_allowed_property(self):
        """Test auto_change_allowed property - critical for automation logic."""
        # States that allow auto change
        self.assertTrue(SecurityState.DAY.auto_change_allowed)
        self.assertTrue(SecurityState.NIGHT.auto_change_allowed)
        
        # States that don't allow auto change
        self.assertFalse(SecurityState.DISABLED.auto_change_allowed)
        self.assertFalse(SecurityState.AWAY.auto_change_allowed)
        return

    def test_security_state_uses_notifications_property(self):
        """Test uses_notifications property - critical for notification system."""
        # Only AWAY should use notifications
        self.assertTrue(SecurityState.AWAY.uses_notifications)
        
        # Other states should not use notifications
        self.assertFalse(SecurityState.DISABLED.uses_notifications)
        self.assertFalse(SecurityState.DAY.uses_notifications)
        self.assertFalse(SecurityState.NIGHT.uses_notifications)
        return

    def test_security_state_initialization_parameters(self):
        """Test SecurityState initialization with custom parameters - complex enum logic."""
        # Test that all states have proper initialization
        for state in SecurityState:
            # Should have boolean properties
            self.assertIsInstance(state.auto_change_allowed, bool)
            self.assertIsInstance(state.uses_notifications, bool)
            
            # Should have inherited label and description
            self.assertIsInstance(state.label, str)
            self.assertIsInstance(state.description, str)
        return

    def test_security_state_business_logic_consistency(self):
        """Test security state business logic consistency - critical for security system."""
        # AWAY state should use notifications (highest security)
        self.assertTrue(SecurityState.AWAY.uses_notifications)
        self.assertFalse(SecurityState.AWAY.auto_change_allowed)
        
        # DISABLED should not use notifications or allow auto change
        self.assertFalse(SecurityState.DISABLED.uses_notifications)
        self.assertFalse(SecurityState.DISABLED.auto_change_allowed)
        
        # DAY/NIGHT should allow auto change but not use notifications
        for state in [SecurityState.DAY, SecurityState.NIGHT]:
            self.assertTrue(state.auto_change_allowed)
            self.assertFalse(state.uses_notifications)
        return


class TestSecurityStateAction(BaseTestCase):

    def test_security_state_action_enum_values(self):
        """Test SecurityStateAction enum values - critical for action mapping."""
        expected_actions = {
            SecurityStateAction.DISABLE,
            SecurityStateAction.SET_DAY,
            SecurityStateAction.SET_NIGHT,
            SecurityStateAction.SET_AWAY,
            SecurityStateAction.SNOOZE
        }
        
        actual_actions = set(SecurityStateAction)
        self.assertEqual(actual_actions, expected_actions)
        return

    def test_security_state_action_labels(self):
        """Test SecurityStateAction labels - important for UI display."""
        expected_labels = {
            SecurityStateAction.DISABLE: 'Disable',
            SecurityStateAction.SET_DAY: 'Day',
            SecurityStateAction.SET_NIGHT: 'Night',
            SecurityStateAction.SET_AWAY: 'Away',
            SecurityStateAction.SNOOZE: 'Snooze'
        }
        
        for action, expected_label in expected_labels.items():
            self.assertEqual(action.label, expected_label)
        return
