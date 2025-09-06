import json
import logging
import os
from unittest.mock import Mock, patch
from django.test import TestCase
from requests.exceptions import ConnectionError

from hi.services.hass.hass_client import HassClient
from hi.services.hass.hass_models import HassState

logging.disable(logging.CRITICAL)


class TestHassClientInitialization(TestCase):
    """Test HassClient initialization and configuration"""
    
    def test_init_with_valid_options(self):
        """Test HassClient initialization with valid API options"""
        api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        
        client = HassClient(api_options)
        
        self.assertEqual(client._api_base_url, 'https://test.homeassistant.io:8123')
        self.assertEqual(client._headers['Authorization'], 'Bearer test_token_123456')
        self.assertEqual(client._headers['content-type'], 'application/json')
    
    def test_init_strips_trailing_slash_from_url(self):
        """Test URL trailing slash is stripped during initialization"""
        api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123/',  # With trailing slash
            'api_token': 'test_token_123456'
        }
        
        client = HassClient(api_options)
        
        self.assertEqual(client._api_base_url, 'https://test.homeassistant.io:8123')
    
    def test_init_missing_base_url_raises_assertion(self):
        """Test initialization fails with missing API base URL"""
        api_options = {
            'api_token': 'test_token_123456'
            # Missing api_base_url
        }
        
        with self.assertRaises(AssertionError):
            HassClient(api_options)
    
    def test_init_missing_token_raises_assertion(self):
        """Test initialization fails with missing API token"""
        api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123'
            # Missing api_token
        }
        
        with self.assertRaises(AssertionError):
            HassClient(api_options)
    
    def test_init_none_values_raise_assertion(self):
        """Test initialization fails with None values"""
        api_options_with_none_url = {
            'api_base_url': None,
            'api_token': 'test_token_123456'
        }
        
        with self.assertRaises(AssertionError):
            HassClient(api_options_with_none_url)
        
        api_options_with_none_token = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': None
        }
        
        with self.assertRaises(AssertionError):
            HassClient(api_options_with_none_token)


class TestHassClientStatesMethod(TestCase):
    """Test states() method with focus on real behavior and error handling"""
    
    def setUp(self):
        self.api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        self.client = HassClient(self.api_options)
    
    def test_states_returns_empty_list_for_empty_response(self):
        """Test states() returns empty list when HASS returns no entities"""
        with patch('hi.services.hass.hass_client.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '[]'
            mock_get.return_value = mock_response
            
            result = self.client.states()
            
            self.assertEqual(result, [])
            self.assertIsInstance(result, list)
    
    def test_states_processes_real_hass_data_correctly(self):
        """Test states() correctly transforms real HASS JSON into HassState objects"""
        # Use real HASS data structure from our test files
        test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        with open(os.path.join(test_data_dir, 'hass-states.json'), 'r') as f:
            real_hass_data = json.load(f)
        
        with patch('hi.services.hass.hass_client.get') as mock_get:
            mock_response = Mock()
            mock_response.text = json.dumps(real_hass_data)
            mock_get.return_value = mock_response
            
            result = self.client.states()
            
            # Verify data transformation quality
            self.assertEqual(len(result), len(real_hass_data))
            self.assertIsInstance(result, list)
            
            # Test that HassConverter properly processes each entity
            for i, state in enumerate(result):
                original_data = real_hass_data[i]
                self.assertIsInstance(state, HassState)
                self.assertEqual(state.entity_id, original_data['entity_id'])
                self.assertEqual(state.state_value, original_data['state'])
                self.assertIn('.', state.entity_id)  # Proper domain.name format
                # Verify domain extraction works
                expected_domain = original_data['entity_id'].split('.')[0]
                self.assertEqual(state.domain, expected_domain)
    
    def test_states_network_error_handling(self):
        """Test states() handles network connection errors properly"""
        with patch('hi.services.hass.hass_client.get') as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")
            
            with self.assertRaises(ConnectionError):
                self.client.states()
    
    def test_states_propagates_json_decode_errors(self):
        """Test states() properly propagates JSON parsing errors with context"""
        with patch('hi.services.hass.hass_client.get') as mock_get:
            mock_response = Mock()
            mock_response.text = 'invalid json {"incomplete"'
            mock_get.return_value = mock_response
            
            with self.assertRaises(json.JSONDecodeError) as context:
                self.client.states()
            
            # Verify the error provides useful information for debugging
            self.assertIn('Expecting', str(context.exception))
    
    def test_states_handles_single_entity_response(self):
        """Test states() correctly processes single entity response"""
        single_entity = {
            'entity_id': 'sensor.temperature',
            'state': '22.5',
            'attributes': {
                'unit_of_measurement': '°C',
                'device_class': 'temperature'
            }
        }
        
        with patch('hi.services.hass.hass_client.get') as mock_get:
            mock_response = Mock()
            mock_response.text = json.dumps([single_entity])
            mock_get.return_value = mock_response
            
            result = self.client.states()
            
            self.assertEqual(len(result), 1)
            state = result[0]
            self.assertEqual(state.entity_id, 'sensor.temperature')
            self.assertEqual(state.state_value, '22.5')
            self.assertEqual(state.domain, 'sensor')
            self.assertEqual(state.unit_of_measurement, '°C')
            self.assertEqual(state.device_class, 'temperature')
    
    def test_states_preserves_entity_attributes_and_metadata(self):
        """Test states() preserves important entity attributes from HASS response"""
        sample_entity = {
            'entity_id': 'light.kitchen_light',
            'state': 'on',
            'attributes': {
                'friendly_name': 'Kitchen Light',
                'brightness': 200,
                'device_class': 'light'
            },
            'context': {'id': 'test-context'},
            'last_changed': '2023-01-01T12:00:00Z',
            'last_updated': '2023-01-01T12:00:00Z'
        }
        
        with patch('hi.services.hass.hass_client.get') as mock_get:
            mock_response = Mock()
            mock_response.text = json.dumps([sample_entity])
            mock_get.return_value = mock_response
            
            result = self.client.states()
            
            self.assertEqual(len(result), 1)
            hass_state = result[0]
            
            # Verify attribute preservation
            self.assertEqual(hass_state.friendly_name, 'Kitchen Light')
            self.assertEqual(hass_state.attributes['brightness'], 200)
            self.assertEqual(hass_state.device_class, 'light')
            self.assertEqual(hass_state.domain, 'light')
            self.assertEqual(hass_state.entity_name_sans_prefix, 'kitchen_light')


class TestHassClientSetStateMethod(TestCase):
    """Test set_state() method HTTP calls and error handling"""
    
    def setUp(self):
        self.api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        self.client = HassClient(self.api_options)
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_returns_response_data_without_attributes(self, mock_post):
        """Test set_state returns parsed JSON response for successful calls without attributes"""
        expected_response_data = {
            'entity_id': 'light.living_room', 
            'state': 'on',
            'last_changed': '2023-01-01T12:00:00Z',
            'context': {'id': 'test-context'}
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response_data
        mock_post.return_value = mock_response
        
        result = self.client.set_state('light.living_room', 'on')
        
        # Test the actual return value, not the mock call
        self.assertEqual(result, expected_response_data)
        self.assertIn('entity_id', result)
        self.assertIn('state', result)
        self.assertIn('last_changed', result)
        self.assertEqual(result['entity_id'], 'light.living_room')
        self.assertEqual(result['state'], 'on')
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_includes_attributes_in_response(self, mock_post):
        """Test set_state properly handles attributes and returns updated entity state"""
        input_attributes = {'brightness': 255, 'color_temp': 300}
        expected_response = {
            'entity_id': 'light.living_room', 
            'state': 'on',
            'attributes': {
                'brightness': 255, 
                'color_temp': 300,
                'friendly_name': 'Living Room Light'
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_response
        mock_post.return_value = mock_response
        
        result = self.client.set_state('light.living_room', 'on', input_attributes)
        
        # Test that attributes are preserved in the response
        self.assertEqual(result, expected_response)
        self.assertEqual(result['attributes']['brightness'], 255)
        self.assertEqual(result['attributes']['color_temp'], 300)
        self.assertIn('friendly_name', result['attributes'])  # HASS may add additional attributes
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_raises_descriptive_error_for_bad_requests(self, mock_post):
        """Test set_state raises ValueError with descriptive message for HTTP 400 errors"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid entity ID format'
        mock_post.return_value = mock_response
        
        with self.assertRaises(ValueError) as context:
            self.client.set_state('invalid.entity.format', 'on')
        
        error_message = str(context.exception)
        self.assertIn('Failed to set state', error_message)
        self.assertIn('400', error_message)
        self.assertIn('Invalid entity ID format', error_message)
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_distinguishes_between_error_types(self, mock_post):
        """Test set_state provides different error messages for different HTTP error types"""
        # Test 404 error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Entity not found'
        mock_post.return_value = mock_response
        
        with self.assertRaises(ValueError) as context:
            self.client.set_state('light.nonexistent', 'on')
        
        error_404 = str(context.exception)
        self.assertIn('404', error_404)
        self.assertIn('Entity not found', error_404)
        
        # Test 403 error
        mock_response.status_code = 403
        mock_response.text = 'Forbidden - read-only entity'
        
        with self.assertRaises(ValueError) as context:
            self.client.set_state('sensor.readonly', 'value')
        
        error_403 = str(context.exception)
        self.assertIn('403', error_403)
        self.assertIn('Forbidden', error_403)
        
        # Verify error messages are different
        self.assertNotEqual(error_404, error_403)
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_json_response_parsing_error(self, mock_post):
        """Test set_state handles JSON response parsing errors"""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response
        
        with self.assertRaises(json.JSONDecodeError):
            self.client.set_state('light.living_room', 'on')


class TestHassClientCallServiceMethod(TestCase):
    """Test call_service() method HTTP calls and error handling"""
    
    def setUp(self):
        self.api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        self.client = HassClient(self.api_options)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_returns_response_object(self, mock_post):
        """Test call_service returns the actual response object for successful calls"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = [{'context': {'id': 'service-call-context'}}]
        mock_post.return_value = mock_response
        
        result = self.client.call_service('light', 'turn_on', 'light.living_room')
        
        # Test that we get the actual response object back
        self.assertEqual(result, mock_response)
        self.assertEqual(result.status_code, 200)
        self.assertIn('content-type', result.headers)
        # Verify the response can be used for further processing
        response_data = result.json()
        self.assertIsInstance(response_data, list)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_merges_service_data_correctly(self, mock_post):
        """Test call_service properly merges entity_id with additional service data"""
        mock_response = Mock()
        mock_response.status_code = 201  # Test that 201 is also accepted
        mock_post.return_value = mock_response
        
        service_data = {'brightness': 255, 'color_temp': 300}
        result = self.client.call_service('light', 'turn_on', 'light.living_room', service_data)
        
        # Verify the response is returned (testing behavior, not mock calls)
        self.assertEqual(result, mock_response)
        self.assertEqual(result.status_code, 201)
        
        # Verify data merging by checking the call was made with merged data
        mock_post.assert_called_once()
        call_data = mock_post.call_args[1]['json']
        self.assertEqual(call_data['entity_id'], 'light.living_room')
        self.assertEqual(call_data['brightness'], 255)
        self.assertEqual(call_data['color_temp'], 300)
        self.assertEqual(len(call_data), 3)  # Should have exactly 3 keys
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_raises_descriptive_errors_for_invalid_requests(self, mock_post):
        """Test call_service provides meaningful error messages for invalid service calls"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Service light.invalid_service not found'
        mock_post.return_value = mock_response
        
        with self.assertRaises(ValueError) as context:
            self.client.call_service('light', 'invalid_service', 'light.living_room')
        
        error_message = str(context.exception)
        self.assertIn('Failed to call service', error_message)
        self.assertIn('400', error_message)
        self.assertIn('Service light.invalid_service not found', error_message)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_rejects_unacceptable_status_codes(self, mock_post):
        """Test call_service raises errors for status codes other than 200 and 201"""
        # Test various error status codes
        error_scenarios = [
            (404, 'Domain unknown_domain not found'),
            (403, 'Access denied for this service'),
            (500, 'Internal server error'),
            (422, 'Unprocessable entity data')
        ]
        
        for status_code, error_text in error_scenarios:
            with self.subTest(status_code=status_code):
                mock_response = Mock()
                mock_response.status_code = status_code
                mock_response.text = error_text
                mock_post.return_value = mock_response
                
                with self.assertRaises(ValueError) as context:
                    self.client.call_service('test_domain', 'test_service', 'test.entity')
                
                error_message = str(context.exception)
                self.assertIn('Failed to call service', error_message)
                self.assertIn(str(status_code), error_message)
                self.assertIn(error_text, error_message)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_accepts_multiple_success_status_codes(self, mock_post):
        """Test call_service treats both 200 and 201 as successful responses"""
        # Test 200 response
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_post.return_value = mock_response_200
        
        result1 = self.client.call_service('light', 'turn_on', 'light.living_room')
        self.assertEqual(result1, mock_response_200)
        self.assertEqual(result1.status_code, 200)
        
        # Test 201 response
        mock_response_201 = Mock()
        mock_response_201.status_code = 201
        mock_post.return_value = mock_response_201
        
        result2 = self.client.call_service('light', 'turn_off', 'light.living_room')
        self.assertEqual(result2, mock_response_201)
        self.assertEqual(result2.status_code, 201)
        
        # Both should return successfully without raising exceptions
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_handles_empty_service_data_correctly(self, mock_post):
        """Test call_service works correctly when service_data is None or empty"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test with None service_data
        result1 = self.client.call_service('switch', 'turn_off', 'switch.kitchen', None)
        self.assertEqual(result1, mock_response)
        
        # Test with empty dict service_data
        result2 = self.client.call_service('switch', 'turn_on', 'switch.kitchen', {})
        self.assertEqual(result2, mock_response)
        
        # Verify both calls were made correctly
        self.assertEqual(mock_post.call_count, 2)
        
        # Check that entity_id is present in both calls
        for call in mock_post.call_args_list:
            call_data = call[1]['json']
            self.assertIn('entity_id', call_data)
            self.assertEqual(call_data['entity_id'], 'switch.kitchen')
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_constructs_correct_service_urls(self, mock_post):
        """Test call_service builds correct URLs for different domain/service combinations"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test URL construction for different service types
        result1 = self.client.call_service('light', 'turn_on', 'light.bedroom')
        result2 = self.client.call_service('climate', 'set_temperature', 'climate.thermostat')
        
        # Verify both calls succeeded
        self.assertEqual(result1, mock_response)
        self.assertEqual(result2, mock_response)
        
        # Verify correct URLs were constructed
        call_args_list = mock_post.call_args_list
        self.assertEqual(len(call_args_list), 2)
        
        # Check first call URL
        first_url = call_args_list[0][0][0]
        self.assertEqual(first_url, 'https://test.homeassistant.io:8123/api/services/light/turn_on')
        
        # Check second call URL
        second_url = call_args_list[1][0][0]
        self.assertEqual(second_url, 'https://test.homeassistant.io:8123/api/services/climate/set_temperature')
        
        # Verify entity_id is included in request data
        first_data = call_args_list[0][1]['json']
        second_data = call_args_list[1][1]['json']
        self.assertEqual(first_data['entity_id'], 'light.bedroom')
        self.assertEqual(second_data['entity_id'], 'climate.thermostat')


class TestHassClientConstants(TestCase):
    """Test HassClient constants and class attributes"""
    
    def test_api_constants(self):
        """Test API constant values"""
        self.assertEqual(HassClient.API_BASE_URL, 'api_base_url')
        self.assertEqual(HassClient.API_TOKEN, 'api_token')
    
    def test_trace_constant_default(self):
        """Test TRACE constant default value"""
        self.assertFalse(HassClient.TRACE)
    
    def test_trace_constant_modifiable(self):
        """Test TRACE constant can be modified for debugging"""
        original_value = HassClient.TRACE
        
        try:
            HassClient.TRACE = True
            self.assertTrue(HassClient.TRACE)
            
            HassClient.TRACE = False
            self.assertFalse(HassClient.TRACE)
        finally:
            # Reset to original value
            HassClient.TRACE = original_value


class TestHassClientEdgeCases(TestCase):
    """Test edge cases and error scenarios"""
    
    def setUp(self):
        self.api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        self.client = HassClient(self.api_options)
    
    def test_trailing_slash_normalization_affects_api_calls(self):
        """Test that trailing slash normalization produces correct API endpoints"""
        # Test with trailing slash
        api_options_with_slash = {
            'api_base_url': 'https://ha.example.com/',
            'api_token': 'test_token'
        }
        client_with_slash = HassClient(api_options_with_slash)
        
        # Test without trailing slash
        api_options_without_slash = {
            'api_base_url': 'https://ha.example.com',
            'api_token': 'test_token'
        }
        client_without_slash = HassClient(api_options_without_slash)
        
        # Both should normalize to the same base URL
        self.assertEqual(client_with_slash._api_base_url, client_without_slash._api_base_url)
        self.assertEqual(client_with_slash._api_base_url, 'https://ha.example.com')
        
        # Mock an API call to verify the URL construction works correctly
        with patch('hi.services.hass.hass_client.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '[]'
            mock_get.return_value = mock_response
            
            client_with_slash.states()
            
            # Verify the URL doesn't have double slashes
            called_url = mock_get.call_args[0][0]
            self.assertEqual(called_url, 'https://ha.example.com/api/states')
            self.assertNotIn('//', called_url.replace('https://', ''))
    
    @patch('hi.services.hass.hass_client.get')
    def test_states_empty_response(self, mock_get):
        """Test states method with empty response"""
        mock_response = Mock()
        mock_response.text = '[]'
        mock_get.return_value = mock_response
        
        result = self.client.states()
        
        self.assertEqual(result, [])
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_empty_attributes(self, mock_post):
        """Test set_state with empty attributes dictionary"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        # Empty dict should not add attributes to payload
        self.client.set_state('light.test', 'on', {})
        
        expected_data = {'state': 'on'}
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json'], expected_data)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_empty_service_data(self, mock_post):
        """Test call_service with empty service data dictionary"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Empty dict should not add extra data to payload
        self.client.call_service('light', 'turn_on', 'light.test', {})
        
        expected_data = {'entity_id': 'light.test'}
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json'], expected_data)


class TestHassClientWithRealData(TestCase):
    """Test HassClient with real Home Assistant API response data"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Load real HASS API response data
        test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        with open(os.path.join(test_data_dir, 'hass-states.json'), 'r') as f:
            cls.real_hass_states_data = json.load(f)
    
    def setUp(self):
        self.api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        self.client = HassClient(self.api_options)
    
    @patch('hi.services.hass.hass_client.get')
    def test_states_integrates_with_real_hass_data_end_to_end(self, mock_get):
        """Test states() method processes real HASS data through entire pipeline"""
        # Use real HASS data without mocking the converter
        mock_response = Mock()
        mock_response.text = json.dumps(self.real_hass_states_data)
        mock_get.return_value = mock_response
        
        result = self.client.states()
        
        # Test end-to-end behavior: real data -> real converter -> real HassState objects
        self.assertEqual(len(result), len(self.real_hass_states_data))
        
        # Verify each HassState was created correctly from real data
        for i, hass_state in enumerate(result):
            original_entity = self.real_hass_states_data[i]
            
            # Test the actual HassState object properties
            self.assertIsInstance(hass_state, HassState)
            self.assertEqual(hass_state.entity_id, original_entity['entity_id'])
            self.assertEqual(hass_state.state_value, original_entity['state'])
            
            # Test domain parsing worked correctly
            expected_domain = original_entity['entity_id'].split('.')[0]
            self.assertEqual(hass_state.domain, expected_domain)
            
            # Test attribute access works
            if 'attributes' in original_entity and original_entity['attributes']:
                original_attrs = original_entity['attributes']
                if 'friendly_name' in original_attrs:
                    self.assertEqual(hass_state.friendly_name, original_attrs['friendly_name'])
                if 'device_class' in original_attrs:
                    self.assertEqual(hass_state.device_class, original_attrs['device_class'])
    
    def test_real_hass_data_diversity_validation(self):
        """Test that our real HASS data covers diverse entity types and configurations"""
        entity_ids = [entity['entity_id'] for entity in self.real_hass_states_data]
        
        # Extract domains from entity IDs
        domains = set()
        for entity_id in entity_ids:
            if '.' in entity_id:
                domain = entity_id.split('.', 1)[0]
                domains.add(domain)
        
        # Verify we have diverse entity types
        expected_domains = ['person', 'zone', 'script', 'camera', 'sensor']
        for expected_domain in expected_domains:
            self.assertIn(expected_domain, domains,
                          f"Should have {expected_domain} entities in test data")
        
        # Verify we have a good number of entities for testing
        self.assertGreaterEqual(len(entity_ids), 10, "Should have substantial test data")
        
        # Verify entity ID format consistency
        for entity_id in entity_ids:
            self.assertIn('.', entity_id, f"Entity ID should contain domain: {entity_id}")
            self.assertGreater(len(entity_id.split('.', 1)[1]), 0,
                               f"Entity name should not be empty: {entity_id}")
    
    def test_real_hass_data_structure_validation(self):
        """Test that real HASS data has expected structure for API responses"""
        for i, entity_data in enumerate(self.real_hass_states_data[:5]):  # Test first 5 entities
            with self.subTest(entity_index=i):
                # Verify required top-level fields
                required_fields = ['entity_id', 'state', 'attributes', 'context',
                                   'last_changed', 'last_reported', 'last_updated']
                for field in required_fields:
                    self.assertIn(field, entity_data,
                                  f"Entity {i} missing required field: {field}")
                
                # Verify entity_id format
                entity_id = entity_data['entity_id']
                self.assertIsInstance(entity_id, str)
                self.assertIn('.', entity_id)
                
                # Verify state field
                self.assertIn('state', entity_data)
                # State can be various types (string, number, etc.)
                
                # Verify attributes is a dictionary
                self.assertIsInstance(entity_data['attributes'], dict)
                
                # Verify context structure
                context = entity_data['context']
                self.assertIsInstance(context, dict)
                self.assertIn('id', context)
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_with_real_entity_ids(self, mock_post):
        """Test set_state() with real entity IDs from our HASS setup"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'state': 'on'}
        mock_post.return_value = mock_response
        
        # Test with various real entity types
        real_entity_samples = [
            ('camera.frontcamera', 'idle'),
            ('sensor.frontcamera_status', 'Connected'),
            ('script.play_door_chime', 'off'),
            ('zone.home', '1'),
        ]
        
        for entity_id, state_value in real_entity_samples:
            with self.subTest(entity_id=entity_id):
                mock_post.reset_mock()
                mock_response.json.reset_mock()
                mock_response.json.return_value = {'entity_id': entity_id, 'state': state_value}
                
                result = self.client.set_state(entity_id, state_value)
                
                # Verify correct URL construction
                expected_url = f'https://test.homeassistant.io:8123/api/states/{entity_id}'
                mock_post.assert_called_once()
                self.assertEqual(mock_post.call_args[0][0], expected_url)
                
                # Verify result
                self.assertEqual(result['entity_id'], entity_id)
                self.assertEqual(result['state'], state_value)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_with_real_domain_service_combinations(self, mock_post):
        """Test call_service() with realistic domain/service combinations from our setup"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test realistic service calls based on our entity types
        real_service_calls = [
            ('script', 'turn_on', 'script.play_door_chime'),
            ('script', 'turn_off', 'script.play_door_chime'),
            ('camera', 'enable_motion_detection', 'camera.frontcamera'),
            ('camera', 'disable_motion_detection', 'camera.patiocamera'),
            ('person', 'set_location', 'person.cassandra'),
        ]
        
        for domain, service, entity_id in real_service_calls:
            with self.subTest(domain=domain, service=service, entity_id=entity_id):
                mock_post.reset_mock()
                
                self.client.call_service(domain, service, entity_id)
                
                # Verify correct URL construction
                expected_url = f'https://test.homeassistant.io:8123/api/services/{domain}/{service}'
                mock_post.assert_called_once()
                self.assertEqual(mock_post.call_args[0][0], expected_url)
                
                # Verify entity_id in request data
                call_data = mock_post.call_args[1]['json']
                self.assertEqual(call_data['entity_id'], entity_id)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_with_real_camera_service_data(self, mock_post):
        """Test call_service() with realistic service data for camera entities"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Test camera-specific service calls with additional data
        camera_service_data = {
            'motion_detection': True,
            'infrared_mode': 'auto',
            'sensitivity': 85
        }
        
        self.client.call_service(
            'camera', 
            'set_motion_detection', 
            'camera.frontcamera', 
            camera_service_data
        )
        
        # Verify service data is merged correctly
        expected_data = {
            'entity_id': 'camera.frontcamera',
            'motion_detection': True,
            'infrared_mode': 'auto',
            'sensitivity': 85
        }
        
        mock_post.assert_called_once()
        call_data = mock_post.call_args[1]['json']
        self.assertEqual(call_data, expected_data)
    
    def test_real_entity_id_domain_extraction(self):
        """Test entity ID domain extraction works with real entity patterns"""
        real_entities_by_domain = {}
        
        # Group real entities by domain
        for entity_data in self.real_hass_states_data:
            entity_id = entity_data['entity_id']
            domain = entity_id.split('.', 1)[0]
            
            if domain not in real_entities_by_domain:
                real_entities_by_domain[domain] = []
            real_entities_by_domain[domain].append(entity_id)
        
        # Verify we have expected domains with multiple entities
        self.assertIn('camera', real_entities_by_domain)
        self.assertIn('sensor', real_entities_by_domain)
        
        # Verify camera entities follow expected pattern
        camera_entities = real_entities_by_domain.get('camera', [])
        self.assertGreater(len(camera_entities), 3, "Should have multiple camera entities")
        
        # Verify sensor entities follow expected pattern
        sensor_entities = real_entities_by_domain.get('sensor', [])
        self.assertGreater(len(sensor_entities), 5, "Should have multiple sensor entities")
        
        # Verify entity naming patterns match our camera setup
        camera_names = [entity.split('.', 1)[1] for entity in camera_entities]
        expected_cameras = ['frontcamera', 'patiocamera', 'sidecamera']
        for expected_camera in expected_cameras:
            self.assertIn(expected_camera, camera_names,
                          f"Should have {expected_camera} in our test data")
    
    @patch('hi.services.hass.hass_client.get')
    def test_states_json_parsing_with_real_complex_attributes(self, mock_get):
        """Test JSON parsing handles complex real attributes from HASS entities"""
        # Use subset of real data with complex attributes
        complex_entities = []
        for entity_data in self.real_hass_states_data[:3]:
            # Real entities have complex nested attributes
            if entity_data['attributes']:
                complex_entities.append(entity_data)
        
        self.assertGreater(len(complex_entities), 0, "Should have entities with complex attributes")
        
        mock_response = Mock()
        mock_response.text = json.dumps(complex_entities)
        mock_get.return_value = mock_response
        
        # Should not raise JSON parsing errors
        with patch('hi.services.hass.hass_client.HassConverter.create_hass_state') as mock_create:
            mock_create.return_value = Mock(spec=HassState)
            
            try:
                result = self.client.states()
                # If we get here, JSON parsing succeeded
                self.assertEqual(len(result), len(complex_entities))
            except json.JSONDecodeError:
                self.fail("Should handle complex real HASS JSON data without parsing errors")
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_error_scenarios_with_real_entities(self, mock_post):
        """Test error handling with realistic entity IDs that might cause issues"""
        # Mock error responses for realistic scenarios
        error_scenarios = [
            (404, 'Entity camera.nonexistent not found'),
            (400, 'Invalid state value for sensor entity'),
            (401, 'Authentication failed'),
            (403, 'Access denied for person entity')
        ]
        
        real_entity_id = 'camera.frontcamera'  # Use real entity from our data
        
        for status_code, error_message in error_scenarios:
            with self.subTest(status_code=status_code):
                mock_response = Mock()
                mock_response.status_code = status_code
                mock_response.text = error_message
                mock_post.return_value = mock_response
                
                with self.assertRaises(ValueError) as context:
                    self.client.set_state(real_entity_id, 'test_state')
                
                self.assertIn(f'Failed to set state: {status_code}', str(context.exception))
                self.assertIn(error_message, str(context.exception))
