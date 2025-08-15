import json
import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase

from hi.services.hass.hass_client import HassClient
from hi.services.hass.hass_models import HassState


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
    """Test states() method HTTP calls and JSON parsing"""
    
    def setUp(self):
        self.api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        self.client = HassClient(self.api_options)
    
    @patch('hi.services.hass.hass_client.get')
    @patch('hi.services.hass.hass_client.HassConverter.create_hass_state')
    def test_states_success(self, mock_create_hass_state, mock_get):
        """Test successful states API call and JSON parsing"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.text = json.dumps([
            {'entity_id': 'light.living_room', 'state': 'on'},
            {'entity_id': 'switch.kitchen', 'state': 'off'}
        ])
        mock_get.return_value = mock_response
        
        # Mock HassState creation
        mock_state1 = Mock(spec=HassState)
        mock_state2 = Mock(spec=HassState)
        mock_create_hass_state.side_effect = [mock_state1, mock_state2]
        
        result = self.client.states()
        
        # Verify HTTP call
        expected_url = 'https://test.homeassistant.io:8123/api/states'
        expected_headers = {
            'Authorization': 'Bearer test_token_123456',
            'content-type': 'application/json'
        }
        mock_get.assert_called_once_with(expected_url, headers=expected_headers)
        
        # Verify HassState creation
        self.assertEqual(mock_create_hass_state.call_count, 2)
        
        # Verify result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], mock_state1)
        self.assertEqual(result[1], mock_state2)
    
    @patch('hi.services.hass.hass_client.get')
    def test_states_json_parsing_error(self, mock_get):
        """Test states method handles JSON parsing errors"""
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.text = 'invalid json response'
        mock_get.return_value = mock_response
        
        with self.assertRaises(json.JSONDecodeError):
            self.client.states()
    
    @patch('hi.services.hass.hass_client.get')
    @patch('hi.services.hass.hass_client.logger')
    def test_states_trace_logging(self, mock_logger, mock_get):
        """Test TRACE logging functionality"""
        # Enable trace logging
        HassClient.TRACE = True
        
        mock_response = Mock()
        mock_response.text = '[]'
        mock_get.return_value = mock_response
        
        try:
            self.client.states()
            mock_logger.debug.assert_called_once_with('HAss Response = []')
        finally:
            # Reset trace logging
            HassClient.TRACE = False
    
    @patch('hi.services.hass.hass_client.get')
    def test_states_http_request_exception(self, mock_get):
        """Test states method handles HTTP request exceptions"""
        mock_get.side_effect = Exception("Connection error")
        
        with self.assertRaises(Exception) as context:
            self.client.states()
        
        self.assertEqual(str(context.exception), "Connection error")


class TestHassClientSetStateMethod(TestCase):
    """Test set_state() method HTTP calls and error handling"""
    
    def setUp(self):
        self.api_options = {
            'api_base_url': 'https://test.homeassistant.io:8123',
            'api_token': 'test_token_123456'
        }
        self.client = HassClient(self.api_options)
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_success_without_attributes(self, mock_post):
        """Test successful set_state call without attributes"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'entity_id': 'light.living_room', 'state': 'on'}
        mock_post.return_value = mock_response
        
        result = self.client.set_state('light.living_room', 'on')
        
        # Verify HTTP call
        expected_url = 'https://test.homeassistant.io:8123/api/states/light.living_room'
        expected_data = {'state': 'on'}
        expected_headers = {
            'Authorization': 'Bearer test_token_123456',
            'content-type': 'application/json'
        }
        mock_post.assert_called_once_with(expected_url, json=expected_data, headers=expected_headers)
        
        # Verify result
        self.assertEqual(result, {'entity_id': 'light.living_room', 'state': 'on'})
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_success_with_attributes(self, mock_post):
        """Test successful set_state call with attributes"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'entity_id': 'light.living_room', 'state': 'on'}
        mock_post.return_value = mock_response
        
        attributes = {'brightness': 255, 'color_temp': 300}
        result = self.client.set_state('light.living_room', 'on', attributes)
        
        # Verify HTTP call includes attributes
        expected_data = {
            'state': 'on',
            'attributes': {'brightness': 255, 'color_temp': 300}
        }
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json'], expected_data)
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_http_error_400(self, mock_post):
        """Test set_state handles HTTP 400 error"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        with self.assertRaises(ValueError) as context:
            self.client.set_state('light.invalid', 'on')
        
        self.assertIn('Failed to set state: 400 Bad Request', str(context.exception))
    
    @patch('hi.services.hass.hass_client.post')
    def test_set_state_http_error_404(self, mock_post):
        """Test set_state handles HTTP 404 error"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Entity not found'
        mock_post.return_value = mock_response
        
        with self.assertRaises(ValueError) as context:
            self.client.set_state('light.nonexistent', 'on')
        
        self.assertIn('Failed to set state: 404 Entity not found', str(context.exception))
    
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
    def test_call_service_success_without_service_data(self, mock_post):
        """Test successful call_service without additional service data"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = self.client.call_service('light', 'turn_on', 'light.living_room')
        
        # Verify HTTP call
        expected_url = 'https://test.homeassistant.io:8123/api/services/light/turn_on'
        expected_data = {'entity_id': 'light.living_room'}
        expected_headers = {
            'Authorization': 'Bearer test_token_123456',
            'content-type': 'application/json'
        }
        mock_post.assert_called_once_with(expected_url, json=expected_data, headers=expected_headers)
        
        # Verify result
        self.assertEqual(result, mock_response)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_success_with_service_data(self, mock_post):
        """Test successful call_service with additional service data"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 201  # Also valid for service calls
        mock_post.return_value = mock_response
        
        service_data = {'brightness': 255, 'color_temp': 300}
        result = self.client.call_service('light', 'turn_on', 'light.living_room', service_data)
        
        # Verify HTTP call includes service data
        expected_data = {
            'entity_id': 'light.living_room',
            'brightness': 255,
            'color_temp': 300
        }
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json'], expected_data)
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_http_error_400(self, mock_post):
        """Test call_service handles HTTP 400 error"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid service data'
        mock_post.return_value = mock_response
        
        with self.assertRaises(ValueError) as context:
            self.client.call_service('light', 'invalid_service', 'light.living_room')
        
        self.assertIn('Failed to call service: 400 Invalid service data', str(context.exception))
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_http_error_404(self, mock_post):
        """Test call_service handles HTTP 404 error for unknown service"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Service not found'
        mock_post.return_value = mock_response
        
        with self.assertRaises(ValueError) as context:
            self.client.call_service('unknown_domain', 'turn_on', 'light.living_room')
        
        self.assertIn('Failed to call service: 404 Service not found', str(context.exception))
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_accepts_status_200_and_201(self, mock_post):
        """Test call_service accepts both 200 and 201 status codes as success"""
        # Test with 200
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_post.return_value = mock_response_200
        
        result = self.client.call_service('light', 'turn_on', 'light.living_room')
        self.assertEqual(result, mock_response_200)
        
        # Test with 201
        mock_response_201 = Mock()
        mock_response_201.status_code = 201
        mock_post.return_value = mock_response_201
        
        result = self.client.call_service('light', 'turn_off', 'light.living_room')
        self.assertEqual(result, mock_response_201)
    
    @patch('hi.services.hass.hass_client.post')
    @patch('hi.services.hass.hass_client.logger')
    def test_call_service_debug_logging(self, mock_logger, mock_post):
        """Test call_service logs debug information"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        self.client.call_service('switch', 'turn_off', 'switch.kitchen')
        
        # Verify debug logging
        mock_logger.debug.assert_called_once_with(
            'HAss call_service: switch.turn_off for switch.kitchen, response=200'
        )
    
    @patch('hi.services.hass.hass_client.post')
    def test_call_service_various_domains_and_services(self, mock_post):
        """Test call_service with various domain/service combinations"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        test_cases = [
            ('light', 'turn_on', 'light.bedroom'),
            ('switch', 'turn_off', 'switch.outlet'),
            ('climate', 'set_temperature', 'climate.thermostat'),
            ('media_player', 'play_media', 'media_player.living_room'),
            ('cover', 'open_cover', 'cover.garage_door')
        ]
        
        for domain, service, entity_id in test_cases:
            with self.subTest(domain=domain, service=service):
                mock_post.reset_mock()
                
                self.client.call_service(domain, service, entity_id)
                
                expected_url = f'https://test.homeassistant.io:8123/api/services/{domain}/{service}'
                mock_post.assert_called_once()
                self.assertEqual(mock_post.call_args[0][0], expected_url)


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
    
    def test_url_construction_with_various_base_urls(self):
        """Test URL construction handles various base URL formats"""
        # Test different URL formats
        test_cases = [
            ('http://localhost:8123', 'http://localhost:8123'),
            ('https://ha.example.com', 'https://ha.example.com'),
            ('https://ha.example.com/', 'https://ha.example.com'),  # Trailing slash removed
            ('http://192.168.1.100:8123/', 'http://192.168.1.100:8123')
        ]
        
        for input_url, expected_url in test_cases:
            with self.subTest(input_url=input_url):
                api_options = {
                    'api_base_url': input_url,
                    'api_token': 'test_token'
                }
                client = HassClient(api_options)
                self.assertEqual(client._api_base_url, expected_url)
    
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
    @patch('hi.services.hass.hass_client.HassConverter.create_hass_state')
    def test_states_with_real_hass_response_data(self, mock_create_hass_state, mock_get):
        """Test states() method with real HASS API response structure"""
        # Use real HASS data as HTTP response
        mock_response = Mock()
        mock_response.text = json.dumps(self.real_hass_states_data)
        mock_get.return_value = mock_response
        
        # Mock HassState creation for each real entity
        mock_states = []
        for i in range(len(self.real_hass_states_data)):
            mock_state = Mock(spec=HassState)
            mock_state.entity_id = self.real_hass_states_data[i]['entity_id']
            mock_states.append(mock_state)
        
        mock_create_hass_state.side_effect = mock_states
        
        result = self.client.states()
        
        # Verify HTTP call made correctly
        expected_url = 'https://test.homeassistant.io:8123/api/states'
        mock_get.assert_called_once_with(expected_url, headers=self.client._headers)
        
        # Verify HassConverter called for each real entity
        self.assertEqual(mock_create_hass_state.call_count, len(self.real_hass_states_data))
        
        # Verify all real entity data was processed
        for i, real_entity_data in enumerate(self.real_hass_states_data):
            mock_create_hass_state.assert_any_call(real_entity_data)
        
        # Verify result contains all entities
        self.assertEqual(len(result), len(self.real_hass_states_data))
    
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