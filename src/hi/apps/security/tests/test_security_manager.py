import logging
from unittest.mock import Mock, patch
from threading import Timer
import threading

from django.core.exceptions import BadRequest
from django.test import RequestFactory

from hi.apps.security.enums import SecurityLevel, SecurityState, SecurityStateAction
from hi.apps.security.security_manager import SecurityManager
from hi.apps.security.transient_models import SecurityStatusData
from hi.constants import DIVID
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSecurityManager(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Reset singleton instance for each test
        SecurityManager._instance = None

    def test_security_manager_singleton_behavior(self):
        """Test SecurityManager singleton pattern - critical for system consistency."""
        manager1 = SecurityManager()
        manager2 = SecurityManager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)
        
        # Should maintain state across references
        manager1._security_state = SecurityState.AWAY
        self.assertEqual(manager2._security_state, SecurityState.AWAY)

    def test_security_manager_initialization_state(self):
        """Test initial state values - important for system startup."""
        manager = SecurityManager()
        
        # Should start with default values
        self.assertEqual(manager._security_state, SecurityState.default())
        self.assertEqual(manager._security_level, SecurityLevel.OFF)
        self.assertIsNone(manager._delayed_security_state_timer)
        self.assertIsNone(manager._delayed_security_state)
        self.assertFalse(manager._was_initialized)

    @patch('hi.apps.security.security_manager.get_redis_client')
    def test_ensure_initialized_tracking(self, mock_get_redis_client):
        """Test initialization tracking - important for lazy loading."""
        mock_redis = Mock()
        mock_get_redis_client.return_value = mock_redis
        mock_redis.get.return_value = None
        
        manager = SecurityManager()
        
        # Should start uninitialized
        self.assertFalse(manager._was_initialized)
        
        # Should initialize once
        with patch.object(manager, 'settings_manager') as mock_settings:
            mock_settings_manager = Mock()
            mock_settings.return_value = mock_settings_manager
            mock_settings_manager.get_setting_value.side_effect = ['08:00', '23:00']
            
            manager.ensure_initialized()
            self.assertTrue(manager._was_initialized)
            
            # Should not reinitialize
            manager.ensure_initialized()
            self.assertTrue(manager._was_initialized)

    def test_update_security_state_immediate_state_level_mapping(self):
        """Test state to level mapping - critical for security system behavior."""
        manager = SecurityManager()
        
        # Test DISABLED -> OFF
        manager.update_security_state_immediate(SecurityState.DISABLED)
        self.assertEqual(manager.security_state, SecurityState.DISABLED)
        self.assertEqual(manager.security_level, SecurityLevel.OFF)
        
        # Test DAY -> LOW
        manager.update_security_state_immediate(SecurityState.DAY)
        self.assertEqual(manager.security_state, SecurityState.DAY)
        self.assertEqual(manager.security_level, SecurityLevel.LOW)
        
        # Test NIGHT -> HIGH
        manager.update_security_state_immediate(SecurityState.NIGHT)
        self.assertEqual(manager.security_state, SecurityState.NIGHT)
        self.assertEqual(manager.security_level, SecurityLevel.HIGH)
        
        # Test AWAY -> HIGH
        manager.update_security_state_immediate(SecurityState.AWAY)
        self.assertEqual(manager.security_state, SecurityState.AWAY)
        self.assertEqual(manager.security_level, SecurityLevel.HIGH)

    @patch('hi.apps.security.security_manager.get_redis_client')
    def test_update_security_state_immediate_redis_caching(self, mock_get_redis_client):
        """Test Redis state caching - important for persistence across restarts."""
        mock_redis = Mock()
        mock_get_redis_client.return_value = mock_redis
        
        manager = SecurityManager()
        manager.update_security_state_immediate(SecurityState.AWAY)
        
        # Should cache state in Redis
        mock_redis.set.assert_called_with(
            SecurityManager.SECURITY_STATE_CACHE_KEY,
            str(SecurityState.AWAY)
        )

    def test_update_security_state_immediate_cancels_delayed_transitions(self):
        """Test immediate update cancels delayed transitions - critical for state consistency."""
        manager = SecurityManager()
        
        # Set up a delayed transition
        mock_timer = Mock(spec=Timer)
        manager._delayed_security_state_timer = mock_timer
        manager._delayed_security_state = SecurityState.AWAY
        
        # Immediate update should cancel delayed state
        manager.update_security_state_immediate(SecurityState.DAY)
        
        mock_timer.cancel.assert_called_once()
        self.assertIsNone(manager._delayed_security_state)
        self.assertIsNone(manager._delayed_security_state_timer)

    def test_update_security_state_user_disable_action(self):
        """Test user disable action - immediate transition to DISABLED."""
        manager = SecurityManager()
        
        with patch.object(manager, '_update_security_state') as mock_update:
            manager.update_security_state_user(SecurityStateAction.DISABLE)
            
            mock_update.assert_called_once_with(
                immediate_security_state=SecurityState.DISABLED,
                future_security_state=None,
                delay_secs=0
            )

    def test_update_security_state_user_day_night_actions(self):
        """Test user day/night actions - immediate transitions."""
        manager = SecurityManager()
        
        with patch.object(manager, '_update_security_state') as mock_update:
            manager.update_security_state_user(SecurityStateAction.SET_DAY)
            mock_update.assert_called_with(
                immediate_security_state=SecurityState.DAY,
                future_security_state=None,
                delay_secs=0
            )
            
            mock_update.reset_mock()
            manager.update_security_state_user(SecurityStateAction.SET_NIGHT)
            mock_update.assert_called_with(
                immediate_security_state=SecurityState.NIGHT,
                future_security_state=None,
                delay_secs=0
            )

    def test_update_security_state_user_away_action_with_delay(self):
        """Test user away action - delayed transition behavior."""
        manager = SecurityManager()
        
        with patch.object(manager, 'settings_manager') as mock_settings:
            mock_settings_manager = Mock()
            mock_settings.return_value = mock_settings_manager
            mock_settings_manager.get_setting_value.return_value = '3'  # 3 minutes
            
            with patch.object(manager, '_update_security_state') as mock_update:
                manager.update_security_state_user(SecurityStateAction.SET_AWAY)
                
                mock_update.assert_called_once_with(
                    immediate_security_state=SecurityState.DISABLED,
                    future_security_state=SecurityState.AWAY,
                    delay_secs=180  # 3 minutes * 60 seconds
                )

    def test_update_security_state_user_snooze_action(self):
        """Test user snooze action - preserves current state with delay."""
        manager = SecurityManager()
        manager._security_state = SecurityState.NIGHT
        
        with patch.object(manager, 'settings_manager') as mock_settings:
            mock_settings_manager = Mock()
            mock_settings.return_value = mock_settings_manager
            mock_settings_manager.get_setting_value.return_value = '5'  # 5 minutes
            
            with patch.object(manager, '_update_security_state') as mock_update:
                manager.update_security_state_user(SecurityStateAction.SNOOZE)
                
                mock_update.assert_called_once_with(
                    immediate_security_state=SecurityState.DISABLED,
                    future_security_state=SecurityState.NIGHT,  # Current state preserved
                    delay_secs=300  # 5 minutes * 60 seconds
                )

    def test_update_security_state_user_invalid_delay_setting(self):
        """Test invalid delay setting handling - uses default delay."""
        manager = SecurityManager()
        
        with patch.object(manager, 'settings_manager') as mock_settings:
            mock_settings_manager = Mock()
            mock_settings.return_value = mock_settings_manager
            mock_settings_manager.get_setting_value.return_value = 'invalid'
            
            with patch.object(manager, '_update_security_state') as mock_update:
                manager.update_security_state_user(SecurityStateAction.SET_AWAY)
                
                mock_update.assert_called_once_with(
                    immediate_security_state=SecurityState.DISABLED,
                    future_security_state=SecurityState.AWAY,
                    delay_secs=SecurityManager.DEFAULT_TRANSITION_DELAY_SECS
                )

    def test_update_security_state_user_unsupported_action(self):
        """Test unsupported action handling - raises BadRequest."""
        manager = SecurityManager()
        
        # Create a mock action that's not in the enum
        mock_action = Mock()
        mock_action.__str__ = Mock(return_value='INVALID_ACTION')
        
        with self.assertRaises(BadRequest):
            manager.update_security_state_user(mock_action)

    @patch('hi.apps.security.security_manager.Timer')
    @patch('hi.apps.security.security_manager.get_redis_client')
    def test_update_security_state_delayed_timer_setup(self, mock_get_redis_client, mock_timer_class):
        """Test delayed state timer setup and Redis caching."""
        mock_redis = Mock()
        mock_get_redis_client.return_value = mock_redis
        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer
        
        manager = SecurityManager()
        manager._update_security_state_delayed(SecurityState.AWAY, 300)
        
        # Should create and start timer
        mock_timer_class.assert_called_once_with(300, manager._apply_delayed_state)
        mock_timer.start.assert_called_once()
        
        # Should cache future state in Redis
        mock_redis.set.assert_called_with(
            SecurityManager.SECURITY_STATE_CACHE_KEY,
            str(SecurityState.AWAY)
        )
        
        # Should track delayed state
        self.assertEqual(manager._delayed_security_state, SecurityState.AWAY)
        self.assertEqual(manager._delayed_security_state_timer, mock_timer)

    @patch('hi.apps.security.security_manager.Timer')
    def test_update_security_state_delayed_cancels_existing_timer(self, mock_timer_class):
        """Test delayed state update cancels existing timer."""
        manager = SecurityManager()
        
        # Set up existing timer
        existing_timer = Mock()
        manager._delayed_security_state_timer = existing_timer
        
        new_timer = Mock()
        mock_timer_class.return_value = new_timer
        
        manager._update_security_state_delayed(SecurityState.AWAY, 300)
        
        # Should cancel existing timer
        existing_timer.cancel.assert_called_once()

    def test_apply_delayed_state(self):
        """Test apply delayed state - calls immediate update with delayed state."""
        manager = SecurityManager()
        manager._delayed_security_state = SecurityState.AWAY
        
        with patch.object(manager, 'update_security_state_immediate') as mock_update:
            manager._apply_delayed_state()
            
            mock_update.assert_called_once_with(new_security_state=SecurityState.AWAY)

    def test_update_security_state_auto_blocked_by_state(self):
        """Test auto update blocked by non-auto-changeable state."""
        manager = SecurityManager()
        manager._security_state = SecurityState.DISABLED  # auto_change_allowed = False
        
        with patch.object(manager, 'update_security_state_immediate') as mock_update:
            manager.update_security_state_auto(SecurityState.DAY)
            
            # Should not update when auto change is not allowed
            mock_update.assert_not_called()

    def test_update_security_state_auto_no_delayed_state(self):
        """Test auto update with no delayed state - normal immediate update."""
        manager = SecurityManager()
        manager._security_state = SecurityState.DAY  # auto_change_allowed = True
        manager._delayed_security_state = None
        
        with patch.object(manager, 'update_security_state_immediate') as mock_update:
            manager.update_security_state_auto(SecurityState.NIGHT)
            
            mock_update.assert_called_once_with(
                new_security_state=SecurityState.NIGHT,
                lock_acquired=True
            )

    def test_update_security_state_auto_blocked_by_delayed_state(self):
        """Test auto update blocked by non-auto-changeable delayed state."""
        manager = SecurityManager()
        manager._security_state = SecurityState.DAY  # auto_change_allowed = True
        manager._delayed_security_state = SecurityState.AWAY  # auto_change_allowed = False
        
        with patch.object(manager, 'update_security_state_immediate') as mock_update:
            manager.update_security_state_auto(SecurityState.NIGHT)
            
            # Should not update when delayed state doesn't allow auto change
            mock_update.assert_not_called()

    def test_update_security_state_auto_updates_snooze_target(self):
        """Test auto update modifies snooze target state - important for time transitions."""
        manager = SecurityManager()
        manager._security_state = SecurityState.DAY  # auto_change_allowed = True
        manager._delayed_security_state = SecurityState.NIGHT  # Snoozing NIGHT state (auto_change_allowed = True)
        
        manager.update_security_state_auto(SecurityState.DAY)
        
        # Should update the delayed state to honor time-based transition
        self.assertEqual(manager._delayed_security_state, SecurityState.DAY)

    def test_get_security_status_data_basic_states(self):
        """Test security status data generation for basic states."""
        manager = SecurityManager()
        
        # Test DAY state
        manager._security_state = SecurityState.DAY
        manager._security_level = SecurityLevel.LOW
        status = manager.get_security_status_data()
        
        self.assertIsInstance(status, SecurityStatusData)
        self.assertEqual(status.current_security_level, SecurityLevel.LOW)
        self.assertEqual(status.current_security_state, SecurityState.DAY)
        self.assertEqual(status.current_action_value, str(SecurityStateAction.SET_DAY))
        self.assertEqual(status.current_action_label, 'Day')

    def test_get_security_status_data_delayed_away_state(self):
        """Test security status data with delayed away transition."""
        manager = SecurityManager()
        manager._security_state = SecurityState.DISABLED
        manager._delayed_security_state = SecurityState.AWAY
        
        status = manager.get_security_status_data()
        
        self.assertEqual(status.current_action_label, SecurityManager.SECURITY_STATE_LABEL_DELAYED_AWAY)
        self.assertEqual(status.current_action_value, str(SecurityStateAction.SET_AWAY))

    def test_get_security_status_data_snoozed_state(self):
        """Test security status data with snoozed state."""
        manager = SecurityManager()
        manager._security_state = SecurityState.DISABLED
        manager._delayed_security_state = SecurityState.NIGHT  # Any non-AWAY state
        
        status = manager.get_security_status_data()
        
        self.assertEqual(status.current_action_label, SecurityManager.SECURITY_STATE_LABEL_SNOOZED)
        self.assertEqual(status.current_action_value, str(SecurityStateAction.SNOOZE))

    @patch('hi.apps.security.security_manager.get_template')
    def test_get_status_id_replace_map_template_rendering(self, mock_get_template):
        """Test status ID replace map template rendering."""
        mock_template = Mock()
        mock_get_template.return_value = mock_template
        mock_template.render.return_value = '<div>Security Control</div>'
        
        manager = SecurityManager()
        request = RequestFactory().get('/')
        
        result = manager.get_status_id_replace_map(request)
        
        # Should render template with security status data
        mock_get_template.assert_called_once()
        mock_template.render.assert_called_once()
        
        # Should return proper div ID mapping
        expected_result = {
            DIVID['SECURITY_STATE_CONTROL']: '<div>Security Control</div>'
        }
        self.assertEqual(result, expected_result)

    def test_thread_safety_concurrent_state_updates(self):
        """Test thread safety of concurrent state updates - critical for multi-threaded access."""
        manager = SecurityManager()
        results = []
        errors = []
        
        def update_state(state):
            try:
                manager.update_security_state_immediate(state)
                results.append(manager.security_state)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads updating state concurrently
        threads = []
        states = [SecurityState.DAY, SecurityState.NIGHT, SecurityState.AWAY, SecurityState.DISABLED] * 5
        
        for state in states:
            thread = threading.Thread(target=update_state, args=(state,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), len(states))
        
        # Final state should be one of the valid states
        self.assertIn(manager.security_state, [SecurityState.DAY, SecurityState.NIGHT, SecurityState.AWAY, SecurityState.DISABLED])
