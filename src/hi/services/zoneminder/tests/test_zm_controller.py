"""
Tests for ZoneMinder controller functionality.
Focuses on high-value testing: control logic, error handling, and business operations.
"""

from unittest.mock import Mock, patch
from django.test import TestCase

from hi.integrations.transient_models import IntegrationKey, IntegrationDetails, IntegrationControlResult

from hi.services.zoneminder.zm_controller import ZoneMinderController
from hi.services.zoneminder.zm_metadata import ZmMetaData


class TestZoneMinderController(TestCase):
    """Test ZoneMinderController control operations and business logic."""

    def setUp(self):
        self.controller = ZoneMinderController()

    def _create_integration_details(self, integration_name):
        """Create realistic IntegrationDetails for testing."""
        key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name=integration_name,
        )
        return IntegrationDetails(key=key, payload={})

    @patch('hi.services.zoneminder.zm_controller.ZoneMinderController.zm_manager')
    def test_do_control_run_state_success(self, mock_zm_manager_method):
        """Test successful run state control operation."""
        # Arrange
        mock_manager = Mock()
        mock_manager.ZM_RUN_STATE_SENSOR_INTEGRATION_NAME = 'run.state'
        mock_manager.clear_caches.return_value = None
        mock_zm_manager_method.return_value = mock_manager

        mock_client = Mock()
        mock_client.set_state.return_value = {'status': 'success'}
        mock_manager._zm_client = mock_client

        integration_details = self._create_integration_details('run.state')
        control_value = 'active'

        # Act
        result = self.controller.do_control(integration_details, control_value)

        # Assert - Test actual behavior
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertEqual(result.new_value, 'active')
        self.assertEqual(result.error_list, [])
        self.assertFalse(result.has_errors)

        # Verify the client was called correctly
        mock_client.set_state.assert_called_once_with('active')
        mock_manager.clear_caches.assert_called_once()

    @patch('hi.services.zoneminder.zm_controller.ZoneMinderController.zm_manager')
    def test_do_control_monitor_function_success(self, mock_zm_manager_method):
        """Test successful monitor function control operation."""
        # Arrange
        mock_manager = Mock()
        mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        mock_manager.clear_caches.return_value = None
        mock_zm_manager_method.return_value = mock_manager

        # Create mock monitor with proper id() method
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123
        mock_monitor.set_parameter.return_value = {'message': 'success'}
        mock_manager.get_zm_monitors.return_value = [mock_monitor]

        integration_details = self._create_integration_details('monitor.function.123')
        control_value = 'modect'

        # Act
        result = self.controller.do_control(integration_details, control_value)

        # Assert - Test actual behavior
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertEqual(result.new_value, 'modect')
        self.assertEqual(result.error_list, [])
        self.assertFalse(result.has_errors)

        # Verify the monitor was called correctly
        mock_monitor.set_parameter.assert_called_once_with({'function': 'modect'})
        mock_manager.clear_caches.assert_called_once()

    @patch('hi.services.zoneminder.zm_controller.ZoneMinderController.zm_manager')
    def test_do_control_monitor_function_error_response(self, mock_zm_manager_method):
        """Test monitor function control with error response from ZM."""
        # Arrange
        mock_manager = Mock()
        mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        mock_manager.clear_caches.return_value = None
        mock_zm_manager_method.return_value = mock_manager

        # Create mock monitor that returns error response
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123
        mock_monitor.set_parameter.return_value = {'message': 'Error: Invalid function'}
        mock_manager.get_zm_monitors.return_value = [mock_monitor]

        integration_details = self._create_integration_details('monitor.function.123')
        control_value = 'invalid_function'

        # Act
        result = self.controller.do_control(integration_details, control_value)

        # Assert - Test error handling behavior
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertIsNone(result.new_value)
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('Problem setting ZM monitor function', result.error_list[0])
        self.assertTrue(result.has_errors)

        # Verify caches are still cleared even on error
        mock_manager.clear_caches.assert_called_once()

    @patch('hi.services.zoneminder.zm_controller.ZoneMinderController.zm_manager')
    def test_do_control_monitor_function_monitor_not_found(self, mock_zm_manager_method):
        """Test monitor function control when monitor ID is not found."""
        # Arrange
        mock_manager = Mock()
        mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        mock_manager.clear_caches.return_value = None
        mock_zm_manager_method.return_value = mock_manager

        # Create mock monitor with different ID
        mock_monitor = Mock()
        mock_monitor.id.return_value = 456  # Different from requested 123
        mock_manager.get_zm_monitors.return_value = [mock_monitor]

        integration_details = self._create_integration_details('monitor.function.123')
        control_value = 'modect'

        # Act
        result = self.controller.do_control(integration_details, control_value)

        # Assert - Test error handling behavior
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertIsNone(result.new_value)
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('Unknown ZM entity', result.error_list[0])
        self.assertTrue(result.has_errors)

        # Verify monitor was not called
        mock_monitor.set_parameter.assert_not_called()
        mock_manager.clear_caches.assert_called_once()

    @patch('hi.services.zoneminder.zm_controller.ZoneMinderController.zm_manager')
    def test_do_control_unknown_integration_name(self, mock_zm_manager_method):
        """Test control operation with unknown integration name."""
        # Arrange
        mock_manager = Mock()
        mock_manager.ZM_RUN_STATE_SENSOR_INTEGRATION_NAME = 'run.state'
        mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        mock_manager.clear_caches.return_value = None
        mock_zm_manager_method.return_value = mock_manager

        integration_details = self._create_integration_details('unknown.integration')
        control_value = 'some_value'

        # Act
        result = self.controller.do_control(integration_details, control_value)

        # Assert - Test error handling behavior
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertIsNone(result.new_value)
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('Unknown ZM control action', result.error_list[0])
        self.assertTrue(result.has_errors)

        # Verify caches are still cleared
        mock_manager.clear_caches.assert_called_once()

    @patch('hi.services.zoneminder.zm_controller.ZoneMinderController.zm_manager')
    def test_do_control_exception_handling(self, mock_zm_manager_method):
        """Test that exceptions during control operations are properly handled."""
        # Arrange
        mock_manager = Mock()
        mock_manager.ZM_RUN_STATE_SENSOR_INTEGRATION_NAME = 'run.state'
        mock_manager.clear_caches.return_value = None
        mock_zm_manager_method.return_value = mock_manager

        # Make the client raise an exception
        mock_client = Mock()
        mock_client.set_state.side_effect = ConnectionError("Network error")
        mock_manager._zm_client = mock_client

        integration_details = self._create_integration_details('run.state')
        control_value = 'active'

        # Act
        result = self.controller.do_control(integration_details, control_value)

        # Assert - Test exception handling behavior
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertIsNone(result.new_value)
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('Network error', result.error_list[0])
        self.assertTrue(result.has_errors)

        # Verify caches are still cleared in finally block
        mock_manager.clear_caches.assert_called_once()

    def test_monitor_id_regex_parsing(self):
        """Test the regex pattern used to extract monitor IDs from integration names."""
        # Test cases for the regex pattern r'.+\D(\d+)'
        test_cases = [
            ('monitor.function.123', '123'),
            ('monitor.function.456', '456'),
            ('monitor.function.12', '12'),
            ('monitor.function.1', '1'),
        ]

        import re
        pattern = r'.+\D(\d+)'

        for integration_name, expected_id in test_cases:
            with self.subTest(integration_name=integration_name):
                match = re.match(pattern, integration_name)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), expected_id)

    def test_monitor_id_regex_no_match(self):
        """Test regex pattern with invalid monitor function names."""
        import re
        pattern = r'.+\D(\d+)'

        invalid_names = [
            'monitor.function',  # No ID
            'monitor.function.',  # No ID after dot
            'monitor.function.abc',  # Non-numeric ID
            '123',  # Just numbers
        ]

        for integration_name in invalid_names:
            with self.subTest(integration_name=integration_name):
                match = re.match(pattern, integration_name)
                self.assertIsNone(match)

    @patch('hi.services.zoneminder.zm_controller.ZoneMinderController.zm_manager')
    def test_set_run_state_direct_call(self, mock_zm_manager_method):
        """Test direct call to set_run_state method."""
        # Arrange
        mock_manager = Mock()
        mock_zm_manager_method.return_value = mock_manager

        mock_client = Mock()
        mock_client.set_state.return_value = {'status': 'ok'}
        mock_manager._zm_client = mock_client

        # Act
        result = self.controller.set_run_state('stopped')

        # Assert
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertEqual(result.new_value, 'stopped')
        self.assertEqual(result.error_list, [])
        self.assertFalse(result.has_errors)

        mock_client.set_state.assert_called_once_with('stopped')

    @patch('hi.services.zoneminder.zm_controller.ZoneMinderController.zm_manager')
    def test_set_monitor_function_direct_call(self, mock_zm_manager_method):
        """Test direct call to set_monitor_function method."""
        # Arrange
        mock_manager = Mock()
        mock_zm_manager_method.return_value = mock_manager

        mock_monitor = Mock()
        mock_monitor.id.return_value = 789
        mock_monitor.set_parameter.return_value = {'message': 'Monitor updated'}
        mock_manager.get_zm_monitors.return_value = [mock_monitor]

        # Act
        result = self.controller.set_monitor_function('789', 'record')

        # Assert
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertEqual(result.new_value, 'record')
        self.assertEqual(result.error_list, [])
        self.assertFalse(result.has_errors)

        mock_monitor.set_parameter.assert_called_once_with({'function': 'record'})
        
