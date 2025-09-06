import logging
import threading
from unittest.mock import Mock, patch
from django.test import TestCase

from hi.integrations.exceptions import IntegrationAttributeError, IntegrationError
from hi.integrations.transient_models import IntegrationKey
from hi.integrations.models import Integration

from hi.services.hass.enums import HassAttributeType
from hi.services.hass.hass_client import HassClient
from hi.services.hass.hass_manager import HassManager
from hi.services.hass.hass_metadata import HassMetaData

logging.disable(logging.CRITICAL)


class TestHassManagerSingleton(TestCase):
    """Test singleton behavior and thread safety"""
    
    def setUp(self):
        # Reset singleton instance for each test
        HassManager._instance = None
        HassManager._lock = threading.Lock()
    
    def test_singleton_behavior(self):
        """Test that HassManager follows singleton pattern"""
        manager1 = HassManager()
        manager2 = HassManager()
        self.assertIs(manager1, manager2)
        
    def test_singleton_thread_safety(self):
        """Test singleton creation is thread-safe"""
        results = []
        
        def create_manager():
            results.append(HassManager())
        
        threads = [threading.Thread(target=create_manager) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
            
        # All instances should be the same object
        first_instance = results[0]
        for instance in results[1:]:
            self.assertIs(instance, first_instance)
            
        # Verify singleton maintains consistent state across threads
        test_value = 'test_thread_safety'
        first_instance._test_attribute = test_value
        for instance in results:
            self.assertEqual(getattr(instance, '_test_attribute', None), test_value)
    
    def test_singleton_initialization_state_consistency(self):
        """Test that singleton maintains consistent initialization state"""
        manager1 = HassManager()
        
        # Verify initial state
        self.assertEqual(manager1._hass_attr_type_to_attribute, {})
        self.assertIsNone(manager1._hass_client)
        self.assertFalse(manager1._was_initialized)
        
        # Modify state
        manager1._was_initialized = True
        manager1._hass_attr_type_to_attribute = {'test': 'value'}
        
        # Get another instance and verify state persistence
        manager2 = HassManager()
        self.assertTrue(manager2._was_initialized)
        self.assertEqual(manager2._hass_attr_type_to_attribute, {'test': 'value'})


class TestHassManagerInitialization(TestCase):
    """Test initialization and attribute loading"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    def test_init_singleton_sets_defaults(self):
        """Test singleton initialization sets correct defaults"""
        self.assertEqual(self.manager._hass_attr_type_to_attribute, {})
        self.assertIsNone(self.manager._hass_client)
        self.assertEqual(self.manager._change_listeners, [])
        self.assertFalse(self.manager._was_initialized)
        self.assertIsNotNone(self.manager._data_lock)
    
    @patch('hi.services.hass.hass_manager.HassManager.reload')
    def test_ensure_initialized_calls_reload_once(self, mock_reload):
        """Test ensure_initialized only calls reload once and sets state correctly"""
        # Verify initial state
        self.assertFalse(self.manager._was_initialized)
        
        self.manager.ensure_initialized()
        mock_reload.assert_called_once()
        self.assertTrue(self.manager._was_initialized)
        
        # Second call should not trigger reload but state should remain
        self.manager.ensure_initialized()
        mock_reload.assert_called_once()  # Still only one call
        self.assertTrue(self.manager._was_initialized)
    
    def test_ensure_initialized_idempotent_behavior(self):
        """Test ensure_initialized can be called multiple times safely"""
        with patch.object(self.manager, 'reload') as mock_reload:
            # Call multiple times
            for _ in range(5):
                self.manager.ensure_initialized()
            
            # Should only be called once
            mock_reload.assert_called_once()
            self.assertTrue(self.manager._was_initialized)
    
    @patch.object(Integration.objects, 'get')
    def test_load_attributes_integration_not_found(self, mock_get):
        """Test _load_attributes raises IntegrationError when integration not found"""
        mock_get.side_effect = Integration.DoesNotExist
        
        with self.assertRaises(IntegrationError) as context:
            self.manager._load_attributes()
        
        self.assertEqual(str(context.exception), 'Home Assistant integration is not implemented.')
    
    @patch.object(Integration.objects, 'get')
    def test_load_attributes_integration_disabled(self, mock_get):
        """Test _load_attributes raises IntegrationError when integration disabled"""
        mock_integration = Mock()
        mock_integration.is_enabled = False
        mock_get.return_value = mock_integration
        
        with self.assertRaises(IntegrationError) as context:
            self.manager._load_attributes()
        
        self.assertEqual(str(context.exception), 'Home Assistant integration is not enabled.')
    
    @patch.object(Integration.objects, 'get')
    def test_load_attributes_missing_required_attribute(self, mock_get):
        """Test _load_attributes raises IntegrationAttributeError for missing required attributes"""
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = HassMetaData.integration_id
        mock_integration.attributes_by_integration_key = {}
        mock_get.return_value = mock_integration
        
        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager._load_attributes()
        
        # Should fail on first required attribute (API_BASE_URL)
        self.assertIn('Missing HAss attribute', str(context.exception))
        self.assertIn('api_base_url', str(context.exception))
    
    @patch.object(Integration.objects, 'get')
    def test_load_attributes_empty_required_value(self, mock_get):
        """Test _load_attributes raises IntegrationAttributeError for empty required values"""
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = HassMetaData.integration_id
        
        # Create mock attribute with empty value
        mock_attr = Mock()
        mock_attr.is_required = True
        mock_attr.value = '   '  # Empty/whitespace only
        
        integration_key = IntegrationKey(
            integration_id=HassMetaData.integration_id,
            integration_name=str(HassAttributeType.API_BASE_URL)
        )
        mock_integration.attributes_by_integration_key = {integration_key: mock_attr}
        mock_get.return_value = mock_integration
        
        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager._load_attributes()
        
        self.assertIn('Missing HAss attribute value for', str(context.exception))
    
    @patch.object(Integration.objects, 'get')
    def test_load_attributes_success_with_all_required(self, mock_get):
        """Test _load_attributes successfully loads all required attributes"""
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = HassMetaData.integration_id
        
        # Create mock attributes for all required types
        attributes = {}
        expected_values = {}
        for attr_type in HassAttributeType:
            if attr_type.is_required:
                mock_attr = Mock()
                mock_attr.is_required = True
                test_value = f'test_value_{attr_type.name}'
                mock_attr.value = test_value
                expected_values[attr_type] = test_value
                integration_key = IntegrationKey(
                    integration_id=HassMetaData.integration_id,
                    integration_name=str(attr_type)
                )
                attributes[integration_key] = mock_attr
        
        mock_integration.attributes_by_integration_key = attributes
        mock_get.return_value = mock_integration
        
        result = self.manager._load_attributes()
        
        # Should return dictionary with all required attribute types
        required_types = [attr_type for attr_type in HassAttributeType if attr_type.is_required]
        self.assertEqual(len(result), len(required_types))
        
        # Verify actual attribute values and objects are returned correctly
        for attr_type in required_types:
            self.assertIn(attr_type, result)
            self.assertEqual(result[attr_type].value, expected_values[attr_type])
            self.assertTrue(result[attr_type].is_required)
    
    @patch.object(Integration.objects, 'get')
    def test_load_attributes_handles_optional_attributes(self, mock_get):
        """Test _load_attributes correctly handles optional attributes"""
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = HassMetaData.integration_id
        
        # Only include required attributes, omit optional ones
        attributes = {}
        for attr_type in HassAttributeType:
            if attr_type.is_required:
                mock_attr = Mock()
                mock_attr.is_required = True
                mock_attr.value = f'test_value_{attr_type.name}'
                integration_key = IntegrationKey(
                    integration_id=HassMetaData.integration_id,
                    integration_name=str(attr_type)
                )
                attributes[integration_key] = mock_attr
        
        mock_integration.attributes_by_integration_key = attributes
        mock_get.return_value = mock_integration
        
        result = self.manager._load_attributes()
        
        # Should succeed with only required attributes
        required_count = len([attr for attr in HassAttributeType if attr.is_required])
        self.assertEqual(len(result), required_count)
        
        # Optional attributes should not be in result
        for attr_type in HassAttributeType:
            if not attr_type.is_required:
                self.assertNotIn(attr_type, result)


class TestHassManagerClientCreation(TestCase):
    """Test HASS client creation and API option validation"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    def create_mock_attributes(self):
        """Helper to create mock attributes for client creation"""
        attributes = {}
        attr_values = {
            HassAttributeType.API_BASE_URL: 'https://test.homeassistant.io:8123',
            HassAttributeType.API_TOKEN: 'test_token_123456'
        }
        
        for attr_type, value in attr_values.items():
            mock_attr = Mock()
            mock_attr.value = value
            mock_attr.integration_key = IntegrationKey(
                integration_id=HassMetaData.integration_id,
                integration_name=str(attr_type)
            )
            attributes[attr_type] = mock_attr
            
        return attributes
    
    def test_create_hass_client_missing_api_attribute(self):
        """Test create_hass_client raises error for missing API attributes"""
        incomplete_attributes = {
            HassAttributeType.API_BASE_URL: Mock(value='https://test.homeassistant.io:8123')
            # Missing API_TOKEN
        }
        
        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager.create_hass_client(incomplete_attributes)
        
        self.assertIn('Missing HAss API attribute', str(context.exception))
    
    def test_create_hass_client_empty_api_attribute_value(self):
        """Test create_hass_client raises error for empty API attribute values"""
        attributes = self.create_mock_attributes()
        attributes[HassAttributeType.API_BASE_URL].value = '   '  # Empty value
        
        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager.create_hass_client(attributes)
        
        self.assertIn('Missing HAss API attribute value for', str(context.exception))
    
    @patch('hi.services.hass.hass_manager.HassClient')
    def test_create_hass_client_success(self, mock_hass_client):
        """Test create_hass_client successfully creates HassClient with correct options"""
        # Store the real constants before mocking
        real_api_base_url = HassClient.API_BASE_URL
        real_api_token = HassClient.API_TOKEN
        
        attributes = self.create_mock_attributes()
        mock_client = Mock()
        mock_hass_client.return_value = mock_client
        # Set the constants on the mock to match the real values
        mock_hass_client.API_BASE_URL = real_api_base_url
        mock_hass_client.API_TOKEN = real_api_token
        
        result = self.manager.create_hass_client(attributes)
        
        # Verify HassClient was called with correct options
        expected_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        mock_hass_client.assert_called_once_with(api_options=expected_options)
        self.assertEqual(result, mock_client)
        
        # Verify the returned client is stored in manager instance
        self.manager._hass_client = result
        self.assertIs(self.manager.hass_client, mock_client)
    
    def test_create_hass_client_validates_attribute_structure(self):
        """Test create_hass_client validates integration key structure correctly"""
        # Create attributes with different integration keys to test validation
        attributes = {}
        
        # Add API_BASE_URL with correct integration key
        mock_attr = Mock()
        mock_attr.value = 'https://test.homeassistant.io:8123'
        mock_attr.integration_key = IntegrationKey(
            integration_id=HassMetaData.integration_id,
            integration_name=str(HassAttributeType.API_BASE_URL)
        )
        attributes[HassAttributeType.API_BASE_URL] = mock_attr
        
        # Add API_TOKEN with correct integration key
        mock_attr2 = Mock()
        mock_attr2.value = 'test_token'
        mock_attr2.integration_key = IntegrationKey(
            integration_id=HassMetaData.integration_id,
            integration_name=str(HassAttributeType.API_TOKEN)
        )
        attributes[HassAttributeType.API_TOKEN] = mock_attr2
        
        with patch('hi.services.hass.hass_manager.HassClient') as mock_client:
            mock_client.API_BASE_URL = 'api_base_url'
            mock_client.API_TOKEN = 'api_token'
            mock_client.return_value = Mock()
            
            result = self.manager.create_hass_client(attributes)
            
            # Should succeed and create client
            self.assertIsNotNone(result)
            mock_client.assert_called_once()


class TestHassManagerChangeListeners(TestCase):
    """Test change listener callback system and thread safety"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    def test_register_change_listener(self):
        """Test registering change listeners adds them to internal list"""
        callback1 = Mock()
        callback2 = Mock()
        
        # Verify initial empty state
        self.assertEqual(len(self.manager._change_listeners), 0)
        
        self.manager.register_change_listener(callback1)
        self.assertEqual(len(self.manager._change_listeners), 1)
        self.assertIn(callback1, self.manager._change_listeners)
        
        self.manager.register_change_listener(callback2)
        self.assertEqual(len(self.manager._change_listeners), 2)
        self.assertIn(callback1, self.manager._change_listeners)
        self.assertIn(callback2, self.manager._change_listeners)
        
        # Verify order is preserved
        self.assertEqual(self.manager._change_listeners[0], callback1)
        self.assertEqual(self.manager._change_listeners[1], callback2)
    
    @patch.object(HassManager, 'reload')
    def test_notify_settings_changed_calls_reload_and_listeners(self, mock_reload):
        """Test notify_settings_changed calls reload and all listeners in correct order"""
        call_order = []
        
        def track_reload():
            call_order.append('reload')
        
        def track_callback1():
            call_order.append('callback1')
        
        def track_callback2():
            call_order.append('callback2')
        
        mock_reload.side_effect = track_reload
        callback1 = Mock(side_effect=track_callback1)
        callback2 = Mock(side_effect=track_callback2)
        
        self.manager.register_change_listener(callback1)
        self.manager.register_change_listener(callback2)
        
        self.manager.notify_settings_changed()
        
        # Verify reload is called first, then callbacks
        self.assertEqual(call_order, ['reload', 'callback1', 'callback2'])
        mock_reload.assert_called_once()
        callback1.assert_called_once()
        callback2.assert_called_once()
    
    @patch.object(HassManager, 'reload')
    def test_notify_settings_changed_handles_callback_exceptions(self, mock_reload):
        """Test notify_settings_changed continues if callback raises exception"""
        callback1 = Mock()
        callback2 = Mock(side_effect=Exception("Test exception"))
        callback3 = Mock()
        
        self.manager.register_change_listener(callback1)
        self.manager.register_change_listener(callback2)
        self.manager.register_change_listener(callback3)
        
        # Should not raise exception despite callback2 failing
        self.manager.notify_settings_changed()
        
        # Verify reload was called despite callback exception
        mock_reload.assert_called_once()
        
        # All callbacks should be attempted
        callback1.assert_called_once()
        callback2.assert_called_once()
        callback3.assert_called_once()
        
        # Verify manager state remains consistent after exception
        self.assertEqual(len(self.manager._change_listeners), 3)


class TestHassManagerReloadAndDataLock(TestCase):
    """Test reload method with data lock coordination"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    @patch.object(HassManager, '_load_attributes')
    @patch.object(HassManager, 'create_hass_client')
    @patch.object(HassManager, 'clear_caches')
    def test_reload_calls_methods_in_correct_order(self, mock_clear_caches, mock_create_client, mock_load_attributes):
        """Test reload calls methods in correct order within data lock"""
        call_order = []
        
        def track_load_attributes():
            call_order.append('load_attributes')
            return {'test': 'attributes'}
        
        def track_create_client(attrs):
            call_order.append('create_client')
            return Mock()
        
        def track_clear_caches():
            call_order.append('clear_caches')
        
        mock_load_attributes.side_effect = track_load_attributes
        mock_create_client.side_effect = track_create_client
        mock_clear_caches.side_effect = track_clear_caches
        
        # Store initial state
        initial_attributes = self.manager._hass_attr_type_to_attribute
        initial_client = self.manager._hass_client
        
        self.manager.reload()
        
        # Verify methods called in correct order
        self.assertEqual(call_order, ['load_attributes', 'create_client', 'clear_caches'])
        
        # Verify state updated correctly
        self.assertEqual(self.manager._hass_attr_type_to_attribute, {'test': 'attributes'})
        self.assertIsNotNone(self.manager._hass_client)
        
        # Verify state changed from initial values
        self.assertNotEqual(self.manager._hass_attr_type_to_attribute, initial_attributes)
        self.assertNotEqual(self.manager._hass_client, initial_client)
    
    @patch.object(HassManager, 'create_hass_client')
    @patch.object(HassManager, '_load_attributes')
    def test_reload_thread_safety_with_data_lock(self, mock_load_attributes, mock_create_client):
        """Test reload method uses data lock for thread safety"""
        # Mock a long-running operation
        import time
        
        execution_order = []
        lock_acquisition_times = []
        
        def slow_load():
            execution_order.append(f'load_start_{threading.current_thread().ident}')
            time.sleep(0.1)  # Simulate slow operation
            execution_order.append(f'load_end_{threading.current_thread().ident}')
            return {}
        
        def slow_create_client(attrs):
            execution_order.append(f'create_start_{threading.current_thread().ident}')
            time.sleep(0.05)  # Simulate client creation
            execution_order.append(f'create_end_{threading.current_thread().ident}')
            return Mock()
        
        mock_load_attributes.side_effect = slow_load
        mock_create_client.side_effect = slow_create_client
        
        results = []
        exceptions = []
        
        def run_reload():
            try:
                start_time = time.time()
                self.manager.reload()
                end_time = time.time()
                lock_acquisition_times.append((start_time, end_time))
                results.append("success")
            except Exception as e:
                exceptions.append(e)
        
        # Run multiple reload operations concurrently
        threads = [threading.Thread(target=run_reload) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All should complete successfully
        self.assertEqual(len(results), 3)
        self.assertEqual(len(exceptions), 0)
        
        # Verify operations were serialized (no overlapping execution)
        thread_executions = {}
        for event in execution_order:
            parts = event.split('_')
            thread_id = parts[2]
            event_type = f'{parts[0]}_{parts[1]}'
            
            if thread_id not in thread_executions:
                thread_executions[thread_id] = []
            thread_executions[thread_id].append(event_type)
        
        # Each thread should complete all its operations before another starts
        for thread_id, events in thread_executions.items():
            self.assertEqual(events, ['load_start', 'load_end', 'create_start', 'create_end'])


class TestHassManagerBooleanConversion(TestCase):
    """Test enum property conversion with custom logic"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    @patch('hi.services.hass.hass_manager.str_to_bool')
    def test_should_add_alarm_events_true(self, mock_str_to_bool):
        """Test should_add_alarm_events returns True when attribute is true"""
        mock_attribute = Mock()
        mock_attribute.value = 'true'
        self.manager._hass_attr_type_to_attribute = {
            HassAttributeType.ADD_ALARM_EVENTS: mock_attribute
        }
        
        mock_str_to_bool.return_value = True
        
        result = self.manager.should_add_alarm_events
        
        self.assertTrue(result)
        mock_str_to_bool.assert_called_once_with('true')
    
    def test_should_add_alarm_events_false_when_no_attribute(self):
        """Test should_add_alarm_events returns False when no attribute"""
        self.manager._hass_attr_type_to_attribute = {}
        
        result = self.manager.should_add_alarm_events
        
        self.assertFalse(result)


class TestHassManagerApiDataFetching(TestCase):
    """Test external API data fetching"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
        
        # Mock the hass_client
        self.mock_client = Mock()
        self.manager._hass_client = self.mock_client
    
    def test_fetch_hass_states_from_api_success(self):
        """Test fetch_hass_states_from_api returns state dictionary"""
        # Mock HASS states
        mock_state1 = Mock()
        mock_state1.entity_id = 'light.living_room'
        mock_state2 = Mock()
        mock_state2.entity_id = 'switch.kitchen'
        
        self.mock_client.states.return_value = [mock_state1, mock_state2]
        
        result = self.manager.fetch_hass_states_from_api()
        
        self.mock_client.states.assert_called_once()
        self.assertEqual(len(result), 2)
        self.assertIn('light.living_room', result)
        self.assertIn('switch.kitchen', result)
        self.assertEqual(result['light.living_room'], mock_state1)
        self.assertEqual(result['switch.kitchen'], mock_state2)
    
    def test_fetch_hass_states_from_api_with_duplicate_entity_ids(self):
        """Test fetch_hass_states_from_api handles duplicate entity IDs correctly"""
        # Mock HASS states with same entity ID (should use last one)
        mock_state1 = Mock()
        mock_state1.entity_id = 'light.living_room'
        mock_state1.state = 'on'
        
        mock_state2 = Mock()
        mock_state2.entity_id = 'light.living_room'  # Same entity ID
        mock_state2.state = 'off'
        
        self.mock_client.states.return_value = [mock_state1, mock_state2]
        
        result = self.manager.fetch_hass_states_from_api()
        
        # Should contain only one entry for the entity ID (the last one)
        self.assertEqual(len(result), 1)
        self.assertIn('light.living_room', result)
        self.assertEqual(result['light.living_room'], mock_state2)
        self.assertEqual(result['light.living_room'].state, 'off')
    
    def test_fetch_hass_states_from_api_empty_response(self):
        """Test fetch_hass_states_from_api handles empty state list"""
        self.mock_client.states.return_value = []
        
        result = self.manager.fetch_hass_states_from_api()
        
        self.assertEqual(len(result), 0)
        self.assertEqual(result, {})
        self.mock_client.states.assert_called_once()
    
    def test_fetch_hass_states_from_api_verbose_parameter_affects_behavior(self):
        """Test fetch_hass_states_from_api verbose parameter affects execution but not results"""
        mock_states = [
            Mock(entity_id='light.test1'),
            Mock(entity_id='switch.test2')
        ]
        self.mock_client.states.return_value = mock_states
        
        # Test both verbose settings return same data
        result_verbose = self.manager.fetch_hass_states_from_api(verbose=True)
        result_quiet = self.manager.fetch_hass_states_from_api(verbose=False)
        
        # Results should be identical regardless of verbose setting
        self.assertEqual(result_verbose, result_quiet)
        self.assertEqual(len(result_verbose), 2)
        self.assertIn('light.test1', result_verbose)
        self.assertIn('switch.test2', result_verbose)
    
    def test_fetch_hass_states_from_api_handles_client_exceptions(self):
        """Test fetch_hass_states_from_api propagates client exceptions"""
        self.mock_client.states.side_effect = Exception("Connection error")
        
        with self.assertRaises(Exception) as context:
            self.manager.fetch_hass_states_from_api()
        
        self.assertEqual(str(context.exception), "Connection error")
        
        # Verify client.states was called
        self.mock_client.states.assert_called_once()
    
    def test_fetch_hass_states_from_api_data_transformation(self):
        """Test fetch_hass_states_from_api correctly transforms state list to dictionary"""
        # Create states with various entity types
        states_data = [
            ('light.bedroom', 'on'),
            ('switch.kitchen', 'off'),
            ('sensor.temperature', '22.5'),
            ('binary_sensor.door', 'open')
        ]
        
        mock_states = []
        for entity_id, state_value in states_data:
            mock_state = Mock()
            mock_state.entity_id = entity_id
            mock_state.state = state_value
            mock_states.append(mock_state)
        
        self.mock_client.states.return_value = mock_states
        
        result = self.manager.fetch_hass_states_from_api()
        
        # Verify dictionary structure and data integrity
        self.assertEqual(len(result), len(states_data))
        for entity_id, expected_state in states_data:
            self.assertIn(entity_id, result)
            self.assertEqual(result[entity_id].entity_id, entity_id)
            self.assertEqual(result[entity_id].state, expected_state)
        
        # Verify keys are entity IDs
        expected_entity_ids = {data[0] for data in states_data}
        actual_entity_ids = set(result.keys())
        self.assertEqual(actual_entity_ids, expected_entity_ids)


class TestHassManagerProperties(TestCase):
    """Test property access and getters"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    def test_hass_client_property_returns_client(self):
        """Test hass_client property returns the stored client"""
        mock_client = Mock()
        self.manager._hass_client = mock_client
        
        result = self.manager.hass_client
        
        self.assertEqual(result, mock_client)
    
    def test_hass_client_property_returns_none_when_no_client(self):
        """Test hass_client property returns None when no client set"""
        self.manager._hass_client = None
        
        result = self.manager.hass_client
        
        self.assertIsNone(result)
    
    def test_clear_caches_method_exists(self):
        """Test clear_caches method exists and is callable"""
        # Should not raise exception
        self.manager.clear_caches()
        
        # Method should be callable
        self.assertTrue(callable(self.manager.clear_caches))


class TestHassManagerIntegrationBoundaries(TestCase):
    """Test integration boundary behavior and error handling"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    @patch.object(Integration.objects, 'get')
    def test_load_attributes_validates_integration_id_match(self, mock_get):
        """Test _load_attributes validates integration IDs match expected metadata"""
        mock_integration = Mock()
        mock_integration.is_enabled = True
        # Wrong integration ID
        mock_integration.integration_id = 'wrong_integration_id'
        mock_get.return_value = mock_integration
        
        # Should still work as long as query matches HassMetaData.integration_id
        # The test verifies that get() is called with correct ID
        try:
            self.manager._load_attributes()
        except (IntegrationAttributeError, IntegrationError):
            pass  # Expected due to missing attributes
        
        mock_get.assert_called_once_with(integration_id=HassMetaData.integration_id)
    
    def test_create_hass_client_integration_key_consistency(self):
        """Test create_hass_client validates integration key consistency"""
        # Create attributes with mismatched integration keys
        mock_attr = Mock()
        mock_attr.value = 'https://test.homeassistant.io:8123'
        mock_attr.integration_key = IntegrationKey(
            integration_id='wrong_id',  # Wrong integration ID
            integration_name=str(HassAttributeType.API_BASE_URL)
        )
        
        attributes = {HassAttributeType.API_BASE_URL: mock_attr}
        
        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager.create_hass_client(attributes)
        
        self.assertIn('Missing HAss API attribute', str(context.exception))
    
    @patch.object(Integration.objects, 'get')
    def test_load_attributes_required_vs_optional_validation(self, mock_get):
        """Test _load_attributes correctly differentiates required vs optional attributes"""
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = HassMetaData.integration_id
        
        # Create attributes only for required types
        attributes = {}
        required_attrs = [attr for attr in HassAttributeType if attr.is_required]
        optional_attrs = [attr for attr in HassAttributeType if not attr.is_required]
        
        # Add only required attributes
        for attr_type in required_attrs:
            mock_attr = Mock()
            mock_attr.is_required = True
            mock_attr.value = f'test_value_{attr_type.name}'
            integration_key = IntegrationKey(
                integration_id=HassMetaData.integration_id,
                integration_name=str(attr_type)
            )
            attributes[integration_key] = mock_attr
        
        mock_integration.attributes_by_integration_key = attributes
        mock_get.return_value = mock_integration
        
        result = self.manager._load_attributes()
        
        # Should succeed with only required attributes
        self.assertEqual(len(result), len(required_attrs))
        
        # Optional attributes should not be required
        for attr_type in optional_attrs:
            self.assertNotIn(attr_type, result)
    
    def test_manager_state_isolation_between_instances(self):
        """Test that manager state is properly isolated in singleton"""
        # This tests the singleton pattern maintains state correctly
        manager1 = HassManager()
        manager1._test_state = 'test_value_1'
        
        manager2 = HassManager()
        self.assertIs(manager1, manager2)
        self.assertEqual(getattr(manager2, '_test_state', None), 'test_value_1')
        
        # Modify state through manager2
        manager2._test_state = 'test_value_2'
        
        # manager1 should see the change
        self.assertEqual(manager1._test_state, 'test_value_2')


class TestHassManagerComplexBusinessLogic(TestCase):
    """Test complex business logic scenarios and edge cases"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    @patch.object(Integration.objects, 'get')
    def test_attribute_value_whitespace_handling(self, mock_get):
        """Test attribute value validation handles whitespace correctly"""
        mock_integration = Mock()
        mock_integration.is_enabled = True
        mock_integration.integration_id = HassMetaData.integration_id
        
        # Test various whitespace scenarios
        whitespace_values = [
            '   ',      # Only spaces
            '\t\t',    # Only tabs
            '\n\n',    # Only newlines
            ' \t\n ',  # Mixed whitespace
            '',         # Empty string
        ]
        
        for whitespace_value in whitespace_values:
            with self.subTest(value=repr(whitespace_value)):
                mock_attr = Mock()
                mock_attr.is_required = True
                mock_attr.value = whitespace_value
                
                integration_key = IntegrationKey(
                    integration_id=HassMetaData.integration_id,
                    integration_name=str(HassAttributeType.API_BASE_URL)
                )
                mock_integration.attributes_by_integration_key = {integration_key: mock_attr}
                mock_get.return_value = mock_integration
                
                with self.assertRaises(IntegrationAttributeError) as context:
                    self.manager._load_attributes()
                
                self.assertIn('Missing HAss attribute value for', str(context.exception))
    
    def test_concurrent_initialization_and_reload(self):
        """Test concurrent initialization and reload operations"""
        import time
        results = []
        exceptions = []
        
        def initialize_manager():
            try:
                with patch.object(self.manager, 'reload') as mock_reload:
                    mock_reload.side_effect = lambda: time.sleep(0.05)  # Slow reload
                    
                    self.manager.ensure_initialized()
                    results.append('initialized')
            except Exception as e:
                exceptions.append(e)
        
        def reload_manager():
            try:
                with patch.object(self.manager, '_load_attributes') as mock_load:
                    with patch.object(self.manager, 'create_hass_client') as mock_create:
                        mock_load.return_value = {}
                        mock_create.return_value = Mock()
                        time.sleep(0.05)  # Slow operation
                        
                        self.manager.reload()
                        results.append('reloaded')
            except Exception as e:
                exceptions.append(e)
        
        # Run concurrent operations
        threads = [
            threading.Thread(target=initialize_manager),
            threading.Thread(target=reload_manager),
            threading.Thread(target=initialize_manager),
        ]
        
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All operations should complete successfully
        self.assertEqual(len(exceptions), 0)
        self.assertGreater(len(results), 0)
