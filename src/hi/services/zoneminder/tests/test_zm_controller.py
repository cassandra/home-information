import re
from unittest.mock import Mock, MagicMock, patch
from django.test import TestCase

from hi.integrations.transient_models import IntegrationDetails, IntegrationKey, IntegrationControlResult

from hi.services.zoneminder.zm_controller import ZoneMinderController
from hi.services.zoneminder.zm_manager import ZoneMinderManager
from hi.services.zoneminder.zm_metadata import ZmMetaData


class TestZoneMinderControllerIntegrationKeyParsing(TestCase):
    """Test integration key parsing and regex validation"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
        
        # Mock the zm_manager to avoid initialization
        self.mock_manager = Mock(spec=ZoneMinderManager)
        self.mock_manager.ZM_RUN_STATE_SENSOR_INTEGRATION_NAME = 'run.state'
        self.mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        self.mock_manager.clear_caches = Mock()
        
        # Mock the _zm_client
        self.mock_client = Mock()
        self.mock_manager._zm_client = self.mock_client
        
        self.controller._zm_manager = self.mock_manager
    
    def test_run_state_control_exact_match(self):
        """Test run state control with exact integration name match"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        self.mock_client.set_state.return_value = {'status': 'success'}
        
        result = self.controller.do_control(integration_details, 'start')
        
        self.mock_client.set_state.assert_called_once_with('start')
        self.assertEqual(result.new_value, 'start')
        self.assertEqual(result.error_list, [])
        self.mock_manager.clear_caches.assert_called_once()
    
    def test_monitor_function_regex_parsing_valid_id(self):
        """Test monitor function control with valid monitor ID regex parsing"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='monitor.function.123'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        # Mock monitor with ID 123
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123
        mock_monitor.set_parameter.return_value = {'message': 'success'}
        
        self.mock_manager.get_zm_monitors.return_value = [mock_monitor]
        
        result = self.controller.do_control(integration_details, 'Modect')
        
        # Verify regex extracted monitor ID correctly
        mock_monitor.set_parameter.assert_called_once_with({'function': 'Modect'})
        self.assertEqual(result.new_value, 'Modect')
        self.assertEqual(result.error_list, [])
    
    def test_monitor_function_regex_parsing_multi_digit_id(self):
        """Test monitor function regex correctly parses multi-digit IDs"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='monitor.function.4567'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        mock_monitor = Mock()
        mock_monitor.id.return_value = 4567
        mock_monitor.set_parameter.return_value = {'message': 'success'}
        
        self.mock_manager.get_zm_monitors.return_value = [mock_monitor]
        
        result = self.controller.do_control(integration_details, 'Record')
        
        # Verify regex extracted correct multi-digit ID
        mock_monitor.set_parameter.assert_called_once_with({'function': 'Record'})
        self.assertEqual(result.new_value, 'Record')
    
    def test_monitor_function_regex_no_match_invalid_format(self):
        """Test monitor function with integration name that doesn't match regex"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='monitor.function.abc'  # No numeric ID
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        result = self.controller.do_control(integration_details, 'Modect')
        
        # Should fall through to unknown action error
        self.assertIsNone(result.new_value)
        self.assertIn('Unknown ZM control action.', result.error_list[0])
    
    def test_unknown_integration_name_error(self):
        """Test error handling for unknown integration names"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='unknown.action'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        result = self.controller.do_control(integration_details, 'test')
        
        self.assertIsNone(result.new_value)
        self.assertIn('Unknown ZM control action.', result.error_list[0])
        self.mock_manager.clear_caches.assert_called_once()


class TestZoneMinderControllerRunStateControl(TestCase):
    """Test run state control functionality"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
        
        self.mock_manager = Mock(spec=ZoneMinderManager)
        self.mock_client = Mock()
        self.mock_manager._zm_client = self.mock_client
        self.controller._zm_manager = self.mock_manager
    
    def test_set_run_state_success(self):
        """Test successful run state setting"""
        self.mock_client.set_state.return_value = {'status': 'success'}
        
        result = self.controller.set_run_state('start')
        
        self.mock_client.set_state.assert_called_once_with('start')
        self.assertEqual(result.new_value, 'start')
        self.assertEqual(result.error_list, [])
    
    def test_set_run_state_different_values(self):
        """Test run state setting with different values"""
        test_values = ['start', 'stop', 'restart', 'pause']
        
        for value in test_values:
            with self.subTest(value=value):
                self.mock_client.reset_mock()
                self.mock_client.set_state.return_value = {'status': 'success'}
                
                result = self.controller.set_run_state(value)
                
                self.mock_client.set_state.assert_called_once_with(value)
                self.assertEqual(result.new_value, value)
                self.assertEqual(result.error_list, [])
    
    def test_set_run_state_with_api_exception(self):
        """Test run state setting handles API exceptions gracefully"""
        # Test is handled by do_control's exception handling
        pass  # This is tested in the integration exception tests


class TestZoneMinderControllerMonitorFunctionControl(TestCase):
    """Test monitor function control and external API response validation"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
        
        self.mock_manager = Mock(spec=ZoneMinderManager)
        self.controller._zm_manager = self.mock_manager
    
    def test_set_monitor_function_success(self):
        """Test successful monitor function setting"""
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123
        mock_monitor.set_parameter.return_value = {'message': 'Monitor saved'}
        
        self.mock_manager.get_zm_monitors.return_value = [mock_monitor]
        
        result = self.controller.set_monitor_function('123', 'Modect')
        
        mock_monitor.set_parameter.assert_called_once_with({'function': 'Modect'})
        self.assertEqual(result.new_value, 'Modect')
        self.assertEqual(result.error_list, [])
    
    def test_set_monitor_function_multiple_monitors_correct_match(self):
        """Test monitor function setting finds correct monitor among multiple"""
        mock_monitor1 = Mock()
        mock_monitor1.id.return_value = 111
        
        mock_monitor2 = Mock()
        mock_monitor2.id.return_value = 222
        mock_monitor2.set_parameter.return_value = {'message': 'Success'}
        
        mock_monitor3 = Mock()
        mock_monitor3.id.return_value = 333
        
        self.mock_manager.get_zm_monitors.return_value = [mock_monitor1, mock_monitor2, mock_monitor3]
        
        result = self.controller.set_monitor_function('222', 'Record')
        
        # Only the correct monitor should have set_parameter called
        mock_monitor1.set_parameter.assert_not_called()
        mock_monitor2.set_parameter.assert_called_once_with({'function': 'Record'})
        mock_monitor3.set_parameter.assert_not_called()
        
        self.assertEqual(result.new_value, 'Record')
    
    def test_set_monitor_function_string_id_comparison(self):
        """Test monitor function handles string/int ID comparison correctly"""
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123  # Integer ID from ZM API
        mock_monitor.set_parameter.return_value = {'message': 'Success'}
        
        self.mock_manager.get_zm_monitors.return_value = [mock_monitor]
        
        # Pass string ID (as comes from regex parsing)
        result = self.controller.set_monitor_function('123', 'Motion')
        
        mock_monitor.set_parameter.assert_called_once_with({'function': 'Motion'})
        self.assertEqual(result.new_value, 'Motion')
    
    def test_set_monitor_function_monitor_not_found(self):
        """Test monitor function raises error when monitor ID not found"""
        mock_monitor = Mock()
        mock_monitor.id.return_value = 111
        
        self.mock_manager.get_zm_monitors.return_value = [mock_monitor]
        
        with self.assertRaises(ValueError) as context:
            self.controller.set_monitor_function('999', 'Modect')
        
        self.assertEqual(str(context.exception), 'Unknown ZM entity.')
        mock_monitor.set_parameter.assert_not_called()
    
    def test_set_monitor_function_api_error_response(self):
        """Test monitor function handles API error responses"""
        mock_monitor = Mock()
        mock_monitor.id.return_value = 123
        mock_monitor.set_parameter.return_value = {'message': 'Error: Invalid function'}
        
        self.mock_manager.get_zm_monitors.return_value = [mock_monitor]
        
        with self.assertRaises(ValueError) as context:
            self.controller.set_monitor_function('123', 'InvalidFunction')
        
        self.assertEqual(str(context.exception), 'Problen setting ZM monitor function.')
    
    def test_set_monitor_function_various_function_values(self):
        """Test monitor function setting with various valid function values"""
        function_values = ['None', 'Monitor', 'Modect', 'Record', 'Mocord', 'Nodect']
        
        for function_value in function_values:
            with self.subTest(function_value=function_value):
                mock_monitor = Mock()
                mock_monitor.id.return_value = 123
                mock_monitor.set_parameter.return_value = {'message': 'Success'}
                
                self.mock_manager.get_zm_monitors.return_value = [mock_monitor]
                
                result = self.controller.set_monitor_function('123', function_value)
                
                mock_monitor.set_parameter.assert_called_with({'function': function_value})
                self.assertEqual(result.new_value, function_value)


class TestZoneMinderControllerExceptionHandling(TestCase):
    """Test exception handling in do_control method"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
        
        self.mock_manager = Mock(spec=ZoneMinderManager)
        self.mock_manager.ZM_RUN_STATE_SENSOR_INTEGRATION_NAME = 'run.state'
        self.mock_manager.MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
        self.mock_manager.clear_caches = Mock()
        
        self.controller._zm_manager = self.mock_manager
    
    def test_do_control_handles_set_run_state_exception(self):
        """Test do_control handles exceptions from set_run_state"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        # Mock an exception in the underlying ZM client
        mock_client = Mock()
        mock_client.set_state.side_effect = Exception("ZM API connection failed")
        self.mock_manager._zm_client = mock_client
        
        result = self.controller.do_control(integration_details, 'start')
        
        self.assertIsNone(result.new_value)
        self.assertIn('ZM API connection failed', result.error_list[0])
        self.mock_manager.clear_caches.assert_called_once()
    
    def test_do_control_handles_set_monitor_function_exception(self):
        """Test do_control handles exceptions from set_monitor_function"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='monitor.function.123'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        # Mock get_zm_monitors to raise exception
        self.mock_manager.get_zm_monitors.side_effect = Exception("Failed to fetch monitors")
        
        result = self.controller.do_control(integration_details, 'Modect')
        
        self.assertIsNone(result.new_value)
        self.assertIn('Failed to fetch monitors', result.error_list[0])
        self.mock_manager.clear_caches.assert_called_once()
    
    def test_do_control_always_clears_caches_on_success(self):
        """Test do_control always clears caches even on successful operations"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        mock_client = Mock()
        mock_client.set_state.return_value = {'status': 'success'}
        self.mock_manager._zm_client = mock_client
        
        result = self.controller.do_control(integration_details, 'start')
        
        self.assertEqual(result.new_value, 'start')
        self.mock_manager.clear_caches.assert_called_once()
    
    def test_do_control_always_clears_caches_on_exception(self):
        """Test do_control always clears caches even when exceptions occur"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        mock_client = Mock()
        mock_client.set_state.side_effect = Exception("Test exception")
        self.mock_manager._zm_client = mock_client
        
        result = self.controller.do_control(integration_details, 'start')
        
        self.assertIsNone(result.new_value)
        self.mock_manager.clear_caches.assert_called_once()


class TestZoneMinderControllerRegexPatterns(TestCase):
    """Test specific regex patterns used in integration key parsing"""
    
    def test_monitor_function_regex_pattern_validation(self):
        """Test the exact regex pattern used for monitor ID extraction"""
        # This is the actual regex pattern from the code: r'.+\D(\d+)'
        regex_pattern = r'.+\D(\d+)'
        
        # Test cases that should match
        valid_cases = [
            ('monitor.function.123', '123'),
            ('monitor.function.4567', '4567'),
            ('prefix.text.999', '999'),
            ('a.b.c.42', '42'),
        ]
        
        for test_input, expected_id in valid_cases:
            with self.subTest(input=test_input):
                match = re.match(regex_pattern, test_input)
                self.assertIsNotNone(match, f"Should match: {test_input}")
                self.assertEqual(match.group(1), expected_id)
        
        # Test cases that should NOT match
        invalid_cases = [
            'monitor.function.abc',  # No digits
            '123',                   # Just digits, no prefix
            'monitor.function.',     # No ID after dot
            '',                      # Empty string
        ]
        
        for test_input in invalid_cases:
            with self.subTest(input=test_input):
                match = re.match(regex_pattern, test_input)
                self.assertIsNone(match, f"Should NOT match: {test_input}")
    
    def test_monitor_function_regex_edge_cases(self):
        """Test regex behavior with edge cases"""
        regex_pattern = r'.+\D(\d+)'
        
        # Edge cases
        edge_cases = [
            ('monitor.function.123.extra', '123'),  # Extra content after ID
            ('a1b2c3.456', '456'),                   # Multiple numbers, gets last
            ('text.0', '0'),                         # Zero ID
            ('text.000123', '000123'),               # Leading zeros preserved
        ]
        
        for test_input, expected_id in edge_cases:
            with self.subTest(input=test_input):
                match = re.match(regex_pattern, test_input)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), expected_id)


class TestZoneMinderControllerMixin(TestCase):
    """Test ZoneMinderMixin functionality"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
    
    @patch('hi.services.zoneminder.zm_controller.ZoneMinderManager')
    def test_zm_manager_creates_and_initializes_manager(self, mock_manager_class):
        """Test zm_manager method creates and initializes manager instance"""
        mock_manager_instance = Mock()
        mock_manager_class.return_value = mock_manager_instance
        
        # Clear any existing manager
        if hasattr(self.controller, '_zm_manager'):
            delattr(self.controller, '_zm_manager')
        
        result = self.controller.zm_manager()
        
        mock_manager_class.assert_called_once()
        mock_manager_instance.ensure_initialized.assert_called_once()
        self.assertEqual(result, mock_manager_instance)
    
    @patch('hi.services.zoneminder.zm_controller.ZoneMinderManager')
    def test_zm_manager_reuses_existing_instance(self, mock_manager_class):
        """Test zm_manager method reuses existing manager instance"""
        mock_manager_instance = Mock()
        mock_manager_class.return_value = mock_manager_instance
        
        # First call
        result1 = self.controller.zm_manager()
        
        # Second call
        result2 = self.controller.zm_manager()
        
        # Should only create once
        mock_manager_class.assert_called_once()
        mock_manager_instance.ensure_initialized.assert_called_once()
        self.assertIs(result1, result2)