import logging
from unittest.mock import Mock, patch
from django.test import TestCase

from hi.integrations.transient_models import IntegrationDetails, IntegrationKey

from hi.services.zoneminder.zm_controller import ZoneMinderController
from hi.services.zoneminder.zm_manager import ZoneMinderManager
from hi.services.zoneminder.zm_metadata import ZmMetaData

logging.disable(logging.CRITICAL)


class TestZoneMinderControllerIntegrationKeyParsing(TestCase):
    """Test integration key parsing and end-to-end behavior with real manager"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
        
        # Create real monitor objects that behave like pyzm Monitor objects
        self.mock_monitor_123 = Mock()
        self.mock_monitor_123.id.return_value = 123
        self.mock_monitor_123.set_parameter.return_value = {'message': 'success'}
        
        self.mock_monitor_4567 = Mock()
        self.mock_monitor_4567.id.return_value = 4567
        self.mock_monitor_4567.set_parameter.return_value = {'message': 'success'}
        
        # Mock ZMApi components
        self.mock_zm_api = Mock()
        self.mock_zm_api.set_state.return_value = {'status': 'success'}
        
        # Mock monitors response - this is what get_zm_monitors() calls
        self.mock_monitors_collection = Mock()
        self.mock_monitors_collection.list.return_value = [self.mock_monitor_123, self.mock_monitor_4567]
        self.mock_zm_api.monitors.return_value = self.mock_monitors_collection
        
        # Patch ZMApi creation to return our mock
        self.zm_api_patcher = patch('hi.services.zoneminder.zm_manager.ZMApi')
        self.mock_zm_api_class = self.zm_api_patcher.start()
        self.mock_zm_api_class.return_value = self.mock_zm_api
        
        # Mock the integration loading to avoid database dependency
        from hi.services.zoneminder.enums import ZmAttributeType
        from hi.integrations.transient_models import IntegrationKey
        
        self.integration_patcher = patch('hi.services.zoneminder.zm_manager.Integration.objects.get')
        self.mock_integration_get = self.integration_patcher.start()
        
        # Create mock integration attributes for required fields
        mock_attributes = {}
        for attr_type in ZmAttributeType:
            if attr_type.is_required:
                integration_key = IntegrationKey(
                    integration_id=ZmMetaData.integration_id,
                    integration_name=str(attr_type)
                )
                mock_attr = Mock()
                mock_attr.integration_key = integration_key
                mock_attr.is_required = attr_type.is_required
                mock_attr.value = f'test_{attr_type.name.lower()}'
                mock_attributes[integration_key] = mock_attr
        
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = ZmMetaData.integration_id
        mock_integration.attributes_by_integration_key = mock_attributes
        # Add attributes.all() mock for the new _load_attributes method
        mock_integration.attributes.all.return_value = list(mock_attributes.values())
        self.mock_integration_get.return_value = mock_integration
    
    def tearDown(self):
        self.zm_api_patcher.stop()
        self.integration_patcher.stop()
        # Clear any cached manager instance from controller
        if hasattr(self.controller, '_zm_manager'):
            delattr(self.controller, '_zm_manager')
        # Reset singleton instance to ensure clean state between tests
        ZoneMinderManager._instance = None
    
    def test_run_state_control_exact_match(self):
        """Test run state control end-to-end with real manager"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        self.mock_zm_api.set_state.return_value = {'status': 'success'}
        
        # Test actual behavior - manager should be created and used
        result = self.controller.do_control(integration_details, 'start')
        
        # Verify HTTP API call was made correctly
        self.mock_zm_api.set_state.assert_called_once_with('start')
        
        # Verify actual controller behavior
        self.assertEqual(result.new_value, 'start')
        self.assertEqual(result.error_list, [])
        
        # Verify manager singleton behavior
        manager1 = self.controller.zm_manager()
        manager2 = self.controller.zm_manager()
        self.assertIs(manager1, manager2, "Manager should be singleton")
        
        # Verify cache state was actually cleared
        self.assertEqual(manager1._zm_state_list, [])
        self.assertEqual(manager1._zm_monitor_list, [])
    
    def test_monitor_function_regex_parsing_valid_id(self):
        """Test monitor function control end-to-end with real integration key parsing"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='monitor.function.123'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        # Test end-to-end: controller should parse integration name, 
        # create real manager, get monitors, and call correct monitor
        result = self.controller.do_control(integration_details, 'Modect')
        
        # Verify correct monitor (ID 123) was called with correct parameters
        self.mock_monitor_123.set_parameter.assert_called_once_with({'function': 'Modect'})
        self.mock_monitor_4567.set_parameter.assert_not_called()
        
        # Verify controller return value
        self.assertEqual(result.new_value, 'Modect')
        self.assertEqual(result.error_list, [])
        
        # Verify real manager was used to get monitors
        self.mock_zm_api.monitors.assert_called_once_with({'force_reload': True})
        
        # Verify cache was actually cleared by checking manager state
        manager = self.controller.zm_manager()
        self.assertEqual(manager._zm_monitor_list, [])
    
    def test_monitor_function_regex_parsing_multi_digit_id(self):
        """Test monitor function control handles multi-digit monitor IDs correctly"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='monitor.function.4567'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        result = self.controller.do_control(integration_details, 'Record')
        
        # Verify correct monitor (ID 4567) was identified and called
        self.mock_monitor_4567.set_parameter.assert_called_once_with({'function': 'Record'})
        self.mock_monitor_123.set_parameter.assert_not_called()
        self.assertEqual(result.new_value, 'Record')
        
        # Verify manager processed monitor ID matching correctly  
        # (string '4567' should match integer 4567)
        self.mock_monitor_4567.id.assert_called()
    
    def test_monitor_function_regex_no_match_invalid_format(self):
        """Test error handling when integration name has invalid format"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='monitor.function.abc'  # No numeric ID
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        result = self.controller.do_control(integration_details, 'Modect')
        
        # Should fall through to unknown action error
        self.assertIsNone(result.new_value)
        self.assertIn('Unknown ZM control action.', result.error_list[0])
        
        # Verify manager cache was still cleared even on error
        manager = self.controller.zm_manager()
        self.assertEqual(manager._zm_state_list, [])
        self.assertEqual(manager._zm_monitor_list, [])
    
    def test_unknown_integration_name_error(self):
        """Test error handling for unknown integration names with real manager"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='unknown.action'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        result = self.controller.do_control(integration_details, 'test')
        
        self.assertIsNone(result.new_value)
        self.assertIn('Unknown ZM control action.', result.error_list[0])
        
        # Verify real manager was created and cache cleared
        manager = self.controller.zm_manager()
        self.assertIsInstance(manager, ZoneMinderManager)
        self.assertEqual(manager._zm_state_list, [])
        self.assertEqual(manager._zm_monitor_list, [])


class TestZoneMinderControllerRunStateControl(TestCase):
    """Test run state control with real manager and broader assertions"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
        
        # Mock ZMApi at HTTP boundary
        self.mock_zm_api = Mock()
        self.mock_zm_api.set_state.return_value = {'status': 'success'}
        
        # Patch ZMApi creation
        self.zm_api_patcher = patch('hi.services.zoneminder.zm_manager.ZMApi')
        self.mock_zm_api_class = self.zm_api_patcher.start()
        self.mock_zm_api_class.return_value = self.mock_zm_api
        
        # Mock integration loading
        from hi.services.zoneminder.enums import ZmAttributeType
        self.integration_patcher = patch('hi.services.zoneminder.zm_manager.Integration.objects.get')
        self.mock_integration_get = self.integration_patcher.start()
        
        # Create mock integration attributes
        mock_attributes = {}
        for attr_type in ZmAttributeType:
            if attr_type.is_required:
                integration_key = IntegrationKey(
                    integration_id=ZmMetaData.integration_id,
                    integration_name=str(attr_type)
                )
                mock_attr = Mock()
                mock_attr.integration_key = integration_key
                mock_attr.is_required = attr_type.is_required
                mock_attr.value = f'test_{attr_type.name.lower()}'
                mock_attributes[integration_key] = mock_attr
        
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = ZmMetaData.integration_id
        mock_integration.attributes_by_integration_key = mock_attributes
        # Add attributes.all() mock for the new _load_attributes method
        mock_integration.attributes.all.return_value = list(mock_attributes.values())
        self.mock_integration_get.return_value = mock_integration
    
    def tearDown(self):
        self.zm_api_patcher.stop()
        self.integration_patcher.stop()
        if hasattr(self.controller, '_zm_manager'):
            delattr(self.controller, '_zm_manager')
        ZoneMinderManager._instance = None
    
    def test_set_run_state_success(self):
        """Test successful run state setting with real manager integration"""
        result = self.controller.set_run_state('start')
        
        # Verify HTTP API was called correctly
        self.mock_zm_api.set_state.assert_called_once_with('start')
        
        # Verify controller behavior
        self.assertEqual(result.new_value, 'start')
        self.assertEqual(result.error_list, [])
        
        # Verify real manager was created and used
        manager = self.controller.zm_manager()
        self.assertIsInstance(manager, ZoneMinderManager)
        
        # Verify manager caching - same instance returned
        manager2 = self.controller.zm_manager()
        self.assertIs(manager, manager2)
    
    def test_set_run_state_different_values(self):
        """Test run state setting with different values and behavior verification"""
        test_values = ['start', 'stop', 'restart', 'pause']
        
        for value in test_values:
            with self.subTest(value=value):
                self.mock_zm_api.reset_mock()
                self.mock_zm_api.set_state.return_value = {'status': 'success'}
                
                result = self.controller.set_run_state(value)
                
                # Verify HTTP call
                self.mock_zm_api.set_state.assert_called_once_with(value)
                
                # Verify behavior
                self.assertEqual(result.new_value, value)
                self.assertEqual(result.error_list, [])
                
                # Verify manager state consistency across multiple calls
                manager = self.controller.zm_manager()
                self.assertIsInstance(manager, ZoneMinderManager)
                # Manager should maintain the same client
                self.assertIs(manager._zm_client, self.mock_zm_api)
    
    def test_set_run_state_with_api_exception(self):
        """Test run state setting handles API exceptions with real error propagation"""
        self.mock_zm_api.set_state.side_effect = Exception("API connection failed")
        
        # Test that exception is properly caught and handled by calling code
        with self.assertRaises(Exception) as context:
            self.controller.set_run_state('start')
        
        self.assertEqual(str(context.exception), "API connection failed")
        
        # Verify API was called despite exception
        self.mock_zm_api.set_state.assert_called_once_with('start')
        
        # Verify manager was still created and maintains state
        manager = self.controller.zm_manager()
        self.assertIsInstance(manager, ZoneMinderManager)


class TestZoneMinderControllerMonitorFunctionControl(TestCase):
    """Test monitor function control with real manager and end-to-end data flow"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
        
        # Create monitor mocks with realistic behavior
        self.mock_monitor_111 = Mock()
        self.mock_monitor_111.id.return_value = 111
        self.mock_monitor_111.set_parameter.return_value = {'message': 'Monitor saved'}
        
        self.mock_monitor_222 = Mock()
        self.mock_monitor_222.id.return_value = 222
        self.mock_monitor_222.set_parameter.return_value = {'message': 'Success'}
        
        self.mock_monitor_333 = Mock()
        self.mock_monitor_333.id.return_value = 333
        self.mock_monitor_333.set_parameter.return_value = {'message': 'Updated'}
        
        # Mock ZMApi at HTTP boundary
        self.mock_zm_api = Mock()
        self.mock_monitors_collection = Mock()
        self.mock_monitors_collection.list.return_value = [
            self.mock_monitor_111, self.mock_monitor_222, self.mock_monitor_333
        ]
        self.mock_zm_api.monitors.return_value = self.mock_monitors_collection
        
        # Patch ZMApi creation
        self.zm_api_patcher = patch('hi.services.zoneminder.zm_manager.ZMApi')
        self.mock_zm_api_class = self.zm_api_patcher.start()
        self.mock_zm_api_class.return_value = self.mock_zm_api
        
        # Mock integration loading
        from hi.services.zoneminder.enums import ZmAttributeType
        self.integration_patcher = patch('hi.services.zoneminder.zm_manager.Integration.objects.get')
        self.mock_integration_get = self.integration_patcher.start()
        
        mock_attributes = {}
        for attr_type in ZmAttributeType:
            if attr_type.is_required:
                integration_key = IntegrationKey(
                    integration_id=ZmMetaData.integration_id,
                    integration_name=str(attr_type)
                )
                mock_attr = Mock()
                mock_attr.integration_key = integration_key
                mock_attr.is_required = attr_type.is_required
                mock_attr.value = f'test_{attr_type.name.lower()}'
                mock_attributes[integration_key] = mock_attr
        
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = ZmMetaData.integration_id
        mock_integration.attributes_by_integration_key = mock_attributes
        # Add attributes.all() mock for the new _load_attributes method
        mock_integration.attributes.all.return_value = list(mock_attributes.values())
        self.mock_integration_get.return_value = mock_integration
    
    def tearDown(self):
        self.zm_api_patcher.stop()
        self.integration_patcher.stop()
        if hasattr(self.controller, '_zm_manager'):
            delattr(self.controller, '_zm_manager')
        ZoneMinderManager._instance = None
    
    def test_set_monitor_function_success(self):
        """Test successful monitor function setting with real manager integration"""
        result = self.controller.set_monitor_function('222', 'Modect')
        
        # Verify correct monitor was called
        self.mock_monitor_222.set_parameter.assert_called_once_with({'function': 'Modect'})
        self.mock_monitor_111.set_parameter.assert_not_called()
        self.mock_monitor_333.set_parameter.assert_not_called()
        
        # Verify controller behavior
        self.assertEqual(result.new_value, 'Modect')
        self.assertEqual(result.error_list, [])
        
        # Verify real manager was used to fetch monitors
        self.mock_zm_api.monitors.assert_called_once_with({'force_reload': True})
        
        # Verify manager state and behavior
        manager = self.controller.zm_manager()
        self.assertIsInstance(manager, ZoneMinderManager)
        
        # Test that caching works - subsequent calls use cached data
        cached_monitors = manager.get_zm_monitors()
        self.assertEqual(len(cached_monitors), 3)
        self.assertIn(self.mock_monitor_222, cached_monitors)
    
    def test_set_monitor_function_multiple_monitors_correct_match(self):
        """Test monitor function correctly identifies target monitor among multiple"""
        result = self.controller.set_monitor_function('111', 'Record')
        
        # Only the correct monitor should have set_parameter called
        self.mock_monitor_111.set_parameter.assert_called_once_with({'function': 'Record'})
        self.mock_monitor_222.set_parameter.assert_not_called()
        self.mock_monitor_333.set_parameter.assert_not_called()
        
        self.assertEqual(result.new_value, 'Record')
        
        # Verify correct monitor was found (others may or may not be checked depending on order)
        self.mock_monitor_111.id.assert_called()
        
        # Verify real data flow through manager
        manager = self.controller.zm_manager()
        monitors = manager.get_zm_monitors()
        self.assertEqual(len(monitors), 3)
    
    def test_set_monitor_function_string_id_comparison(self):
        """Test monitor function handles string/int ID comparison correctly in real manager"""
        # Pass string ID (as comes from regex parsing) that should match integer 222
        result = self.controller.set_monitor_function('222', 'Motion')
        
        # Verify string '222' matched integer 222
        self.mock_monitor_222.set_parameter.assert_called_once_with({'function': 'Motion'})
        self.assertEqual(result.new_value, 'Motion')
        
        # Verify the comparison logic worked correctly
        self.mock_monitor_111.set_parameter.assert_not_called()
        self.mock_monitor_333.set_parameter.assert_not_called()
        
        # Test edge case: leading zeros should not match
        self.mock_monitor_333.set_parameter.reset_mock()
        
        # This should not match because '0333' != '333' as strings
        # Testing real behavior - string comparison is exact
        with self.assertRaises(ValueError) as context:
            self.controller.set_monitor_function('0333', 'Nodect')
        self.assertEqual(str(context.exception), 'Unknown ZM entity.')
    
    def test_set_monitor_function_monitor_not_found(self):
        """Test monitor function raises error when monitor ID not found with real manager"""
        with self.assertRaises(ValueError) as context:
            self.controller.set_monitor_function('999', 'Modect')
        
        self.assertEqual(str(context.exception), 'Unknown ZM entity.')
        
        # Verify all monitors were checked but none matched
        self.mock_monitor_111.set_parameter.assert_not_called()
        self.mock_monitor_222.set_parameter.assert_not_called()
        self.mock_monitor_333.set_parameter.assert_not_called()
        
        # Verify real manager was used to fetch monitors
        self.mock_zm_api.monitors.assert_called_once_with({'force_reload': True})
    
    def test_set_monitor_function_api_error_response(self):
        """Test monitor function handles API error responses with real error propagation"""
        # Configure monitor to return error response
        self.mock_monitor_222.set_parameter.return_value = {'message': 'Error: Invalid function'}
        
        with self.assertRaises(ValueError) as context:
            self.controller.set_monitor_function('222', 'InvalidFunction')
        
        self.assertEqual(str(context.exception), 'Problem setting ZM monitor function.')
        
        # Verify the monitor was called and error was detected
        self.mock_monitor_222.set_parameter.assert_called_once_with({'function': 'InvalidFunction'})
        
        # Verify error detection logic works with real response checking
        response = self.mock_monitor_222.set_parameter.return_value
        self.assertIn('error', response['message'].lower())
    
    def test_set_monitor_function_various_function_values(self):
        """Test monitor function setting with various valid function values and real manager"""
        function_values = ['None', 'Monitor', 'Modect', 'Record', 'Mocord', 'Nodect']
        
        for function_value in function_values:
            with self.subTest(function_value=function_value):
                # Reset mock to track this specific call
                self.mock_monitor_111.set_parameter.reset_mock()
                self.mock_monitor_111.set_parameter.return_value = {'message': 'Success'}
                
                result = self.controller.set_monitor_function('111', function_value)
                
                # Verify correct function value was set
                self.mock_monitor_111.set_parameter.assert_called_with({'function': function_value})
                self.assertEqual(result.new_value, function_value)
                self.assertEqual(result.error_list, [])
                
                # Verify manager consistency across multiple function changes
                manager = self.controller.zm_manager()
                self.assertIsInstance(manager, ZoneMinderManager)


class TestZoneMinderControllerExceptionHandling(TestCase):
    """Test exception handling with real manager and error recovery scenarios"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
        
        # Mock ZMApi at HTTP boundary
        self.mock_zm_api = Mock()
        
        # Patch ZMApi creation
        self.zm_api_patcher = patch('hi.services.zoneminder.zm_manager.ZMApi')
        self.mock_zm_api_class = self.zm_api_patcher.start()
        self.mock_zm_api_class.return_value = self.mock_zm_api
        
        # Mock integration loading
        from hi.services.zoneminder.enums import ZmAttributeType
        self.integration_patcher = patch('hi.services.zoneminder.zm_manager.Integration.objects.get')
        self.mock_integration_get = self.integration_patcher.start()
        
        mock_attributes = {}
        for attr_type in ZmAttributeType:
            if attr_type.is_required:
                integration_key = IntegrationKey(
                    integration_id=ZmMetaData.integration_id,
                    integration_name=str(attr_type)
                )
                mock_attr = Mock()
                mock_attr.integration_key = integration_key
                mock_attr.is_required = attr_type.is_required
                mock_attr.value = f'test_{attr_type.name.lower()}'
                mock_attributes[integration_key] = mock_attr
        
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = ZmMetaData.integration_id
        mock_integration.attributes_by_integration_key = mock_attributes
        # Add attributes.all() mock for the new _load_attributes method
        mock_integration.attributes.all.return_value = list(mock_attributes.values())
        self.mock_integration_get.return_value = mock_integration
    
    def tearDown(self):
        self.zm_api_patcher.stop()
        self.integration_patcher.stop()
        if hasattr(self.controller, '_zm_manager'):
            delattr(self.controller, '_zm_manager')
        ZoneMinderManager._instance = None
    
    def test_do_control_handles_set_run_state_exception(self):
        """Test do_control handles HTTP API exceptions with real error recovery"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        # Configure API to raise exception
        self.mock_zm_api.set_state.side_effect = Exception("ZM API connection failed")
        
        result = self.controller.do_control(integration_details, 'start')
        
        # Verify error handling
        self.assertIsNone(result.new_value)
        self.assertIn('ZM API connection failed', result.error_list[0])
        
        # Verify real manager was created and cache cleared despite error
        manager = self.controller.zm_manager()
        self.assertIsInstance(manager, ZoneMinderManager)
        self.assertEqual(manager._zm_state_list, [])
        self.assertEqual(manager._zm_monitor_list, [])
        
        # Verify API was actually called before failing
        self.mock_zm_api.set_state.assert_called_once_with('start')
    
    def test_do_control_handles_set_monitor_function_exception(self):
        """Test do_control handles monitor fetch exceptions from real manager"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='monitor.function.123'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        # Configure monitors API to raise exception
        self.mock_zm_api.monitors.side_effect = Exception("Failed to fetch monitors")
        
        result = self.controller.do_control(integration_details, 'Modect')
        
        # Verify error handling
        self.assertIsNone(result.new_value)
        self.assertIn('Failed to fetch monitors', result.error_list[0])
        
        # Verify real manager was created and attempted to fetch monitors
        manager = self.controller.zm_manager()
        self.assertIsInstance(manager, ZoneMinderManager)
        
        # Verify cache was cleared despite error
        self.assertEqual(manager._zm_monitor_list, [])
        
        # Verify API was called before failing
        self.mock_zm_api.monitors.assert_called_once_with({'force_reload': True})
    
    def test_do_control_always_clears_caches_on_success(self):
        """Test do_control clears real manager caches on successful operations"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        self.mock_zm_api.set_state.return_value = {'status': 'success'}
        
        # Pre-populate cache to test clearing
        manager = self.controller.zm_manager()
        manager._zm_state_list = ['cached_state']
        manager._zm_monitor_list = ['cached_monitor']
        
        result = self.controller.do_control(integration_details, 'start')
        
        self.assertEqual(result.new_value, 'start')
        
        # Verify cache was actually cleared
        self.assertEqual(manager._zm_state_list, [])
        self.assertEqual(manager._zm_monitor_list, [])
        
        # Verify same manager instance was used throughout
        manager2 = self.controller.zm_manager()
        self.assertIs(manager, manager2)
    
    def test_do_control_always_clears_caches_on_exception(self):
        """Test do_control clears real manager caches even when exceptions occur"""
        integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name='run.state'
        )
        integration_details = IntegrationDetails(key=integration_key)
        
        self.mock_zm_api.set_state.side_effect = Exception("Test exception")
        
        # Pre-populate cache to test clearing on error
        manager = self.controller.zm_manager()
        manager._zm_state_list = ['cached_state']
        manager._zm_monitor_list = ['cached_monitor']
        
        result = self.controller.do_control(integration_details, 'start')
        
        self.assertIsNone(result.new_value)
        
        # Verify cache was cleared despite exception
        self.assertEqual(manager._zm_state_list, [])
        self.assertEqual(manager._zm_monitor_list, [])
        
        # Verify manager consistency even after error
        manager2 = self.controller.zm_manager()
        self.assertIs(manager, manager2)


class TestZoneMinderControllerMixin(TestCase):
    """Test ZoneMinderMixin functionality"""
    
    def setUp(self):
        self.controller = ZoneMinderController()
    
    @patch('hi.services.zoneminder.zm_mixins.ZoneMinderManager')
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
    
    @patch('hi.services.zoneminder.zm_mixins.ZoneMinderManager')
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
    
    def test_zm_manager_real_singleton_behavior(self):
        """Test real ZoneMinderManager singleton behavior"""
        # Mock ZMApi for initialization
        with patch('hi.services.zoneminder.zm_manager.ZMApi') as mock_api_class:
            mock_api = Mock()
            mock_api_class.return_value = mock_api
            
            # Mock integration loading with required attributes
            with patch('hi.services.zoneminder.zm_manager.Integration.objects.get') as mock_int:
                from hi.services.zoneminder.enums import ZmAttributeType
                
                mock_attributes = {}
                for attr_type in ZmAttributeType:
                    if attr_type.is_required:
                        integration_key = IntegrationKey(
                            integration_id=ZmMetaData.integration_id,
                            integration_name=str(attr_type)
                        )
                        mock_attr = Mock()
                        mock_attr.integration_key = integration_key
                        mock_attr.is_required = attr_type.is_required
                        mock_attr.value = f'test_{attr_type.name.lower()}'
                        mock_attributes[integration_key] = mock_attr
                
                mock_integration = Mock()
                mock_integration.is_enabled = True
                mock_integration.integration_id = ZmMetaData.integration_id
                mock_integration.attributes_by_integration_key = mock_attributes
                mock_int.return_value = mock_integration
                
                # Ensure clean singleton state
                ZoneMinderManager._instance = None
                
                try:
                    # Test across multiple controllers
                    controller1 = ZoneMinderController()
                    controller2 = ZoneMinderController()
                    
                    manager1 = controller1.zm_manager()
                    manager2 = controller2.zm_manager()
                    
                    # Should be same singleton instance
                    self.assertIs(manager1, manager2)
                    self.assertIsInstance(manager1, ZoneMinderManager)
                    
                    # Test state persistence across controller instances
                    manager1._test_value = 'shared_state'
                    self.assertEqual(manager2._test_value, 'shared_state')
                    
                finally:
                    # Clean up
                    ZoneMinderManager._instance = None
                    if hasattr(controller1, '_zm_manager'):
                        delattr(controller1, '_zm_manager')
                    if hasattr(controller2, '_zm_manager'):
                        delattr(controller2, '_zm_manager')
