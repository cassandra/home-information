import threading
from unittest.mock import Mock, MagicMock, patch, call
from django.test import TestCase

from hi.integrations.exceptions import IntegrationAttributeError, IntegrationError
from hi.integrations.transient_models import IntegrationKey
from hi.integrations.models import Integration, IntegrationAttribute

from hi.services.hass.enums import HassAttributeType
from hi.services.hass.hass_client import HassClient
from hi.services.hass.hass_manager import HassManager
from hi.services.hass.hass_metadata import HassMetaData


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
        
        threads = [threading.Thread(target=create_manager) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
            
        # All instances should be the same object
        first_instance = results[0]
        for instance in results[1:]:
            self.assertIs(instance, first_instance)


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
        """Test ensure_initialized only calls reload once"""
        self.manager.ensure_initialized()
        mock_reload.assert_called_once()
        
        # Second call should not trigger reload
        self.manager.ensure_initialized()
        mock_reload.assert_called_once()  # Still only one call
        
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
        self.assertIn('API_BASE_URL', str(context.exception))
    
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
        
        # Should return dictionary with all required attribute types
        required_types = [attr_type for attr_type in HassAttributeType if attr_type.is_required]
        self.assertEqual(len(result), len(required_types))
        for attr_type in required_types:
            self.assertIn(attr_type, result)


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
        attributes = self.create_mock_attributes()
        mock_client = Mock()
        mock_hass_client.return_value = mock_client
        
        result = self.manager.create_hass_client(attributes)
        
        # Verify HassClient was called with correct options
        expected_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        mock_hass_client.assert_called_once_with(api_options=expected_options)
        self.assertEqual(result, mock_client)


class TestHassManagerChangeListeners(TestCase):
    """Test change listener callback system and thread safety"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    def test_register_change_listener(self):
        """Test registering change listeners"""
        callback1 = Mock()
        callback2 = Mock()
        
        self.manager.register_change_listener(callback1)
        self.manager.register_change_listener(callback2)
        
        self.assertEqual(len(self.manager._change_listeners), 2)
        self.assertIn(callback1, self.manager._change_listeners)
        self.assertIn(callback2, self.manager._change_listeners)
    
    @patch.object(HassManager, 'reload')
    def test_notify_settings_changed_calls_reload_and_listeners(self, mock_reload):
        """Test notify_settings_changed calls reload and all listeners"""
        callback1 = Mock()
        callback2 = Mock()
        self.manager.register_change_listener(callback1)
        self.manager.register_change_listener(callback2)
        
        self.manager.notify_settings_changed()
        
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
        
        # All callbacks should be attempted
        callback1.assert_called_once()
        callback2.assert_called_once()
        callback3.assert_called_once()


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
        mock_attributes = {'test': 'attributes'}
        mock_client = Mock()
        
        mock_load_attributes.return_value = mock_attributes
        mock_create_client.return_value = mock_client
        
        self.manager.reload()
        
        # Verify methods called in correct order
        mock_load_attributes.assert_called_once()
        mock_create_client.assert_called_once_with(mock_attributes)
        mock_clear_caches.assert_called_once()
        
        # Verify state updated
        self.assertEqual(self.manager._hass_attr_type_to_attribute, mock_attributes)
        self.assertEqual(self.manager._hass_client, mock_client)
    
    @patch.object(HassManager, '_load_attributes')
    def test_reload_thread_safety_with_data_lock(self, mock_load_attributes):
        """Test reload method uses data lock for thread safety"""
        # Mock a long-running operation
        import time
        
        def slow_load():
            time.sleep(0.1)  # Simulate slow operation
            return {}
        
        mock_load_attributes.side_effect = slow_load
        
        results = []
        exceptions = []
        
        def run_reload():
            try:
                self.manager.reload()
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


class TestHassManagerBooleanConversion(TestCase):
    """Test enum property conversion with custom logic"""
    
    def setUp(self):
        HassManager._instance = None
        HassManager._lock = threading.Lock()
        self.manager = HassManager()
    
    @patch('hi.apps.common.utils.str_to_bool')
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
    
    def test_fetch_hass_states_from_api_verbose_logging(self):
        """Test fetch_hass_states_from_api verbose parameter controls logging"""
        self.mock_client.states.return_value = []
        
        # Test with verbose=True (default)
        with patch('hi.services.hass.hass_manager.logger') as mock_logger:
            self.manager.fetch_hass_states_from_api(verbose=True)
            mock_logger.debug.assert_called_with('Getting current HAss states.')
        
        # Test with verbose=False
        with patch('hi.services.hass.hass_manager.logger') as mock_logger:
            self.manager.fetch_hass_states_from_api(verbose=False)
            mock_logger.debug.assert_not_called()
    
    def test_fetch_hass_states_from_api_handles_client_exceptions(self):
        """Test fetch_hass_states_from_api handles client exceptions gracefully"""
        self.mock_client.states.side_effect = Exception("Connection error")
        
        with self.assertRaises(Exception) as context:
            self.manager.fetch_hass_states_from_api()
        
        self.assertEqual(str(context.exception), "Connection error")


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