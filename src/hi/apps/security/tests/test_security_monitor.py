import logging
from unittest.mock import Mock, patch, AsyncMock

from hi.testing.async_task_utils import AsyncTaskTestCase

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.security.enums import SecurityState
from hi.apps.security.monitors import SecurityMonitor
from hi.apps.security.settings import SecuritySetting

logging.disable(logging.CRITICAL)


class TestSecurityMonitor(AsyncTaskTestCase):
    """Test SecurityMonitor async behavior and time-based transitions.
    
    Uses AsyncTaskTestCase to avoid database locking issues with async code.
    """
    
    def setUp(self):
        super().setUp()
        datetimeproxy.reset()
    
    def test_security_monitor_initialization(self):
        """Test SecurityMonitor initialization - basic monitor setup."""
        monitor = SecurityMonitor()
        
        # Should be properly configured as periodic monitor
        self.assertEqual(monitor.id, monitor.MONITOR_ID)
        self.assertEqual(monitor._query_interval_secs, SecurityMonitor.SECURITY_POLLING_INTERVAL_SECS)
        self.assertIsNotNone(monitor._last_security_state_check_datetime)
    
    def test_security_monitor_interval_timing(self):
        """Test monitor interval configuration - important for polling frequency."""
        monitor = SecurityMonitor()
        
        # Should use configured polling interval
        self.assertEqual(monitor._query_interval_secs, 5)  # SECURITY_POLLING_INTERVAL_SECS
    
    async def test_do_work_calls_check_security_state(self):
        """Test do_work method calls security state checking."""
        monitor = SecurityMonitor()
        
        with patch.object(monitor, '_check_security_state', new_callable=AsyncMock) as mock_check:
            await monitor.do_work()
            
            mock_check.assert_called_once()
    
    async def test_check_security_state_no_settings_manager(self):
        """Test security state check with missing settings manager - graceful handling."""
        monitor = SecurityMonitor()
        
        with patch.object(monitor, 'settings_manager_async', new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = None
            
            with patch.object(monitor, 'security_manager_async', new_callable=AsyncMock) as mock_security:
                await monitor._check_security_state()
                
                # Should not call security manager if settings manager unavailable
                mock_security.assert_not_called()
    
    async def test_check_security_state_no_security_manager(self):
        """Test security state check with missing security manager - graceful handling."""
        monitor = SecurityMonitor()
        
        mock_settings_manager = Mock()
        with patch.object(monitor, 'settings_manager_async', new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = mock_settings_manager
            
            with patch.object(monitor, 'security_manager_async', new_callable=AsyncMock) as mock_security:
                mock_security.return_value = None
                
                await monitor._check_security_state()
                
                # Should exit gracefully without error
                # (No exceptions should be raised)
    
    @patch('hi.apps.security.monitors.datetimeproxy')
    @patch('hi.apps.security.monitors.ConsoleSettingsHelper')
    async def test_check_security_state_day_start_transition(self, mock_console_helper, mock_datetimeproxy):
        """Test day start time transition - critical time-based automation."""
        monitor = SecurityMonitor()
        
        # Mock datetime and timezone
        mock_current_time = Mock()
        mock_datetimeproxy.now.return_value = mock_current_time
        mock_console_helper.return_value.get_tz_name.return_value = 'UTC'
        
        # Mock time interval check to return True for day start
        mock_datetimeproxy.is_time_of_day_in_interval.side_effect = [True, False]  # Day=True, Night=False
        
        mock_settings_manager = Mock()
        mock_settings_manager.get_setting_value.side_effect = ['08:00', '23:00']  # Day start, Night start
        
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.NIGHT  # auto_change_allowed = True
        
        with patch.object(monitor, 'settings_manager_async', new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = mock_settings_manager
            
            with patch.object(monitor, 'security_manager_async', new_callable=AsyncMock) as mock_security:
                mock_security.return_value = mock_security_manager
                
                await monitor._check_security_state()
                
                # Should transition to DAY state
                mock_security_manager.update_security_state_auto.assert_called_once_with(
                    new_security_state=SecurityState.DAY
                )
                
                # Should check day start time interval (returns early when day=True)
                calls = mock_datetimeproxy.is_time_of_day_in_interval.call_args_list
                self.assertEqual(len(calls), 1)  # Only day check, returns early
                
                # Verify day check call
                day_call = calls[0]
                self.assertEqual(day_call[1]['time_of_day_str'], '08:00')
                self.assertEqual(day_call[1]['tz_name'], 'UTC')
    
    @patch('hi.apps.security.monitors.datetimeproxy')
    @patch('hi.apps.security.monitors.ConsoleSettingsHelper')
    async def test_check_security_state_night_start_transition(self, mock_console_helper, mock_datetimeproxy):
        """Test night start time transition - critical time-based automation."""
        monitor = SecurityMonitor()
        
        # Mock datetime and timezone
        mock_current_time = Mock()
        mock_datetimeproxy.now.return_value = mock_current_time
        mock_console_helper.return_value.get_tz_name.return_value = 'UTC'
        
        # Mock time interval check to return False for day, True for night
        mock_datetimeproxy.is_time_of_day_in_interval.side_effect = [False, True]  # Day=False, Night=True
        
        mock_settings_manager = Mock()
        mock_settings_manager.get_setting_value.side_effect = ['08:00', '23:00']  # Day start, Night start
        
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.DAY  # auto_change_allowed = True
        
        with patch.object(monitor, 'settings_manager_async', new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = mock_settings_manager
            
            with patch.object(monitor, 'security_manager_async', new_callable=AsyncMock) as mock_security:
                mock_security.return_value = mock_security_manager
                
                await monitor._check_security_state()
                
                # Should transition to NIGHT state
                mock_security_manager.update_security_state_auto.assert_called_once_with(
                    new_security_state=SecurityState.NIGHT
                )
                
                # Should check night start time interval
                calls = mock_datetimeproxy.is_time_of_day_in_interval.call_args_list
                self.assertEqual(len(calls), 2)  # Day check, then Night check
                
                # Verify night check call
                night_call = calls[1]
                self.assertEqual(night_call[1]['time_of_day_str'], '23:00')
                self.assertEqual(night_call[1]['tz_name'], 'UTC')
    
    @patch('hi.apps.security.monitors.datetimeproxy')
    @patch('hi.apps.security.monitors.ConsoleSettingsHelper')
    async def test_check_security_state_no_transition_needed(self, mock_console_helper, mock_datetimeproxy):
        """Test no transition when not in time intervals - maintains current state."""
        monitor = SecurityMonitor()
        
        # Mock datetime and timezone
        mock_current_time = Mock()
        mock_datetimeproxy.now.return_value = mock_current_time
        mock_console_helper.return_value.get_tz_name.return_value = 'UTC'
        
        # Mock time interval check to return False for both day and night
        mock_datetimeproxy.is_time_of_day_in_interval.side_effect = [False, False]  # Day=False, Night=False
        
        mock_settings_manager = Mock()
        mock_settings_manager.get_setting_value.side_effect = ['08:00', '23:00']  # Day start, Night start
        
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.DAY  # auto_change_allowed = True
        
        with patch.object(monitor, 'settings_manager_async', new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = mock_settings_manager
            
            with patch.object(monitor, 'security_manager_async', new_callable=AsyncMock) as mock_security:
                mock_security.return_value = mock_security_manager
                
                await monitor._check_security_state()
                
                # Should not call state update when no transition needed
                mock_security_manager.update_security_state_auto.assert_not_called()
    
    @patch('hi.apps.security.monitors.datetimeproxy')
    async def test_check_security_state_updates_last_check_time(self, mock_datetimeproxy):
        """Test last check time tracking - important for time interval calculations."""
        monitor = SecurityMonitor()
        initial_time = monitor._last_security_state_check_datetime
        
        mock_current_time = Mock()
        mock_datetimeproxy.now.return_value = mock_current_time
        
        mock_settings_manager = Mock()
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.DAY  # auto_change_allowed = True
        
        with patch.object(monitor, 'settings_manager_async', new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = mock_settings_manager
            
            with patch.object(monitor, 'security_manager_async', new_callable=AsyncMock) as mock_security:
                mock_security.return_value = mock_security_manager
                
                await monitor._check_security_state()
                
                # Should update last check time even if no state change
                self.assertEqual(monitor._last_security_state_check_datetime, mock_current_time)
                self.assertNotEqual(monitor._last_security_state_check_datetime, initial_time)
    
    @patch('hi.apps.security.monitors.datetimeproxy')
    async def test_check_security_state_updates_time_on_exception(self, mock_datetimeproxy):
        """Test last check time updated even when exceptions occur - ensures proper time tracking."""
        monitor = SecurityMonitor()
        
        mock_current_time = Mock()
        mock_datetimeproxy.now.return_value = mock_current_time
        
        mock_settings_manager = Mock()
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.DAY
        
        # Force an exception during processing after try block starts
        with patch.object(monitor, 'settings_manager_async', new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = mock_settings_manager
            
            with patch.object(monitor, 'security_manager_async', new_callable=AsyncMock) as mock_security:
                mock_security.return_value = mock_security_manager
                # Force exception in the try block
                mock_security_manager.security_state.auto_change_allowed = True
                mock_settings_manager.get_setting_value.side_effect = Exception("Test exception")
                
                # Should handle exception gracefully and still update time
                try:
                    await monitor._check_security_state()
                except Exception:
                    pass  # Exception is expected but handled by finally
                
                # Should still update last check time due to finally block
                self.assertEqual(monitor._last_security_state_check_datetime, mock_current_time)
    
    async def test_check_security_state_time_interval_parameters(self):
        """Test time interval checking uses correct parameters - validates time calculation logic."""
        monitor = SecurityMonitor()
        
        # Set up initial last check time
        initial_time = datetimeproxy.now()
        monitor._last_security_state_check_datetime = initial_time
        
        mock_settings_manager = Mock()
        mock_settings_manager.get_setting_value.side_effect = ['06:30', '22:45']  # Day start, Night start
        
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.NIGHT  # auto_change_allowed = True
        
        with patch('hi.apps.security.monitors.datetimeproxy.is_time_of_day_in_interval') as mock_interval_check:
            mock_interval_check.return_value = False  # No transitions
            
            with patch('hi.apps.security.monitors.ConsoleSettingsHelper') as mock_console_helper:
                mock_console_helper.return_value.get_tz_name.return_value = 'America/New_York'
                
                with patch.object(monitor, 'settings_manager_async', new_callable=AsyncMock) as mock_settings:
                    mock_settings.return_value = mock_settings_manager
                    
                    with patch.object(monitor, 'security_manager_async', new_callable=AsyncMock) as mock_security:
                        mock_security.return_value = mock_security_manager
                        
                        await monitor._check_security_state()
                        
                        # Should check both day and night intervals with correct parameters
                        calls = mock_interval_check.call_args_list
                        self.assertEqual(len(calls), 2)
                        
                        # Verify day start check
                        day_call = calls[0]
                        self.assertEqual(day_call[1]['time_of_day_str'], '06:30')
                        self.assertEqual(day_call[1]['tz_name'], 'America/New_York')
                        self.assertEqual(day_call[1]['start_datetime'], initial_time)
                        
                        # Verify night start check
                        night_call = calls[1]
                        self.assertEqual(night_call[1]['time_of_day_str'], '22:45')
                        self.assertEqual(night_call[1]['tz_name'], 'America/New_York')
                        self.assertEqual(night_call[1]['start_datetime'], initial_time)
    
    def test_security_monitor_mixin_inheritance(self):
        """Test SecurityMonitor inheritance - ensures proper mixin integration."""
        monitor = SecurityMonitor()
        
        # Should inherit from PeriodicMonitor
        from hi.apps.monitor.periodic_monitor import PeriodicMonitor
        self.assertIsInstance(monitor, PeriodicMonitor)
        
        # Should inherit from SecurityMixin
        from hi.apps.security.security_mixins import SecurityMixin
        self.assertIsInstance(monitor, SecurityMixin)
        
        # Should inherit from SettingsMixin
        from hi.apps.config.settings_mixins import SettingsMixin
        self.assertIsInstance(monitor, SettingsMixin)
        
        # Should have access to mixin methods
        self.assertTrue(hasattr(monitor, 'security_manager'))
        self.assertTrue(hasattr(monitor, 'security_manager_async'))
        self.assertTrue(hasattr(monitor, 'settings_manager'))
        self.assertTrue(hasattr(monitor, 'settings_manager_async'))


    async def test_do_work_reports_health_status_success(self):
        """Test do_work reports healthy status when security state check succeeds."""
        monitor = SecurityMonitor()
        
        with patch.object(monitor, "_check_security_state", new_callable=AsyncMock) as mock_check:
            with patch.object(monitor, "record_healthy") as mock_healthy:
                mock_check.return_value = "No change needed (Day mode)"
                
                await monitor.do_work()
                
                mock_check.assert_called_once()
                mock_healthy.assert_called_once_with("No change needed (Day mode)")

    async def test_do_work_reports_health_status_error(self):
        """Test do_work reports error status when security state check fails."""
        monitor = SecurityMonitor()
        
        with patch.object(monitor, "_check_security_state", new_callable=AsyncMock) as mock_check:
            with patch.object(monitor, "record_error") as mock_error:
                mock_check.side_effect = Exception("Test exception")
                
                await monitor.do_work()
                
                mock_check.assert_called_once()
                mock_error.assert_called_once()
                # Check that error message contains the exception
                error_call_args = mock_error.call_args[0][0]
                self.assertIn("Security state check failed", error_call_args)
                self.assertIn("Test exception", error_call_args)

    async def test_check_security_state_returns_appropriate_messages(self):
        """Test _check_security_state returns appropriate status messages."""
        monitor = SecurityMonitor()
        
        # Test settings manager not available
        with patch.object(monitor, "settings_manager_async", new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = None
            
            result = await monitor._check_security_state()
            
            self.assertEqual(result, "Settings manager not available")

    async def test_check_security_state_security_manager_not_available(self):
        """Test _check_security_state handles missing security manager."""
        monitor = SecurityMonitor()
        
        mock_settings_manager = Mock()
        
        with patch.object(monitor, "settings_manager_async", new_callable=AsyncMock) as mock_settings:
            with patch.object(monitor, "security_manager_async", new_callable=AsyncMock) as mock_security:
                mock_settings.return_value = mock_settings_manager
                mock_security.return_value = None
                
                result = await monitor._check_security_state()
                
                self.assertEqual(result, "Security manager not available")

    async def test_check_security_state_auto_change_blocked(self):
        """Test _check_security_state reports when auto-change is blocked."""
        monitor = SecurityMonitor()

        mock_settings_manager = Mock()
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.AWAY  # auto_change_allowed = False

        with patch.object(monitor, "settings_manager_async", new_callable=AsyncMock) as mock_settings:
            with patch.object(monitor, "security_manager_async", new_callable=AsyncMock) as mock_security:
                with patch("hi.apps.security.monitors.ConsoleSettingsHelper") as mock_console:
                    mock_settings.return_value = mock_settings_manager
                    mock_security.return_value = mock_security_manager
                    mock_console.return_value.get_tz_name.return_value = "UTC"

                    result = await monitor._check_security_state()

                    self.assertEqual(result, "Auto-change blocked (Away mode)")

    async def test_check_security_state_no_change_needed(self):
        """Test _check_security_state reports when no change is needed."""
        monitor = SecurityMonitor()

        mock_settings_manager = Mock()
        mock_settings_manager.get_setting_value.return_value = "06:00"  # Day/night start times

        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.DAY  # auto_change_allowed = True

        with patch.object(monitor, "settings_manager_async", new_callable=AsyncMock) as mock_settings:
            with patch.object(monitor, "security_manager_async", new_callable=AsyncMock) as mock_security:
                with patch("hi.apps.security.monitors.datetimeproxy.is_time_of_day_in_interval") as mock_interval:
                    with patch("hi.apps.security.monitors.ConsoleSettingsHelper") as mock_console:
                        mock_settings.return_value = mock_settings_manager
                        mock_security.return_value = mock_security_manager
                        mock_console.return_value.get_tz_name.return_value = "UTC"
                        mock_interval.return_value = False  # No time interval match

                        result = await monitor._check_security_state()

                        self.assertEqual(result, "No change needed (Day mode)")

    async def test_check_security_state_day_transition(self):
        """Test _check_security_state reports day transition."""
        monitor = SecurityMonitor()
        
        mock_settings_manager = Mock()
        mock_settings_manager.get_setting_value.side_effect = lambda setting: {
            SecuritySetting.SECURITY_DAY_START: "06:00"
        }.get(setting, "18:00")
        
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.NIGHT  # auto_change_allowed = True
        
        with patch.object(monitor, "settings_manager_async", new_callable=AsyncMock) as mock_settings:
            with patch.object(monitor, "security_manager_async", new_callable=AsyncMock) as mock_security:
                with patch("hi.apps.security.monitors.datetimeproxy.is_time_of_day_in_interval") as mock_interval:
                    with patch("hi.apps.security.monitors.ConsoleSettingsHelper") as mock_console:
                        mock_settings.return_value = mock_settings_manager
                        mock_security.return_value = mock_security_manager
                        mock_console.return_value.get_tz_name.return_value = "UTC"
                        mock_interval.side_effect = [True, False]  # Day start time matches, night does not

                        result = await monitor._check_security_state()

                        self.assertEqual(result, "Transitioned Night → Day")
                        mock_security_manager.update_security_state_auto.assert_called_once_with(
                            new_security_state=SecurityState.DAY
                        )

    async def test_check_security_state_night_transition(self):
        """Test _check_security_state reports night transition."""
        monitor = SecurityMonitor()
        
        mock_settings_manager = Mock()
        mock_settings_manager.get_setting_value.side_effect = lambda setting: {
            SecuritySetting.SECURITY_NIGHT_START: "18:00"
        }.get(setting, "06:00")
        
        mock_security_manager = Mock()
        mock_security_manager.security_state = SecurityState.DAY  # auto_change_allowed = True
        
        with patch.object(monitor, "settings_manager_async", new_callable=AsyncMock) as mock_settings:
            with patch.object(monitor, "security_manager_async", new_callable=AsyncMock) as mock_security:
                with patch("hi.apps.security.monitors.datetimeproxy.is_time_of_day_in_interval") as mock_interval:
                    with patch("hi.apps.security.monitors.ConsoleSettingsHelper") as mock_console:
                        mock_settings.return_value = mock_settings_manager
                        mock_security.return_value = mock_security_manager
                        mock_console.return_value.get_tz_name.return_value = "UTC"
                        mock_interval.side_effect = [False, True]  # Day start doesnt match, night does

                        result = await monitor._check_security_state()

                        self.assertEqual(result, "Transitioned Day → Night")
                        mock_security_manager.update_security_state_auto.assert_called_once_with(
                            new_security_state=SecurityState.NIGHT
                        )

