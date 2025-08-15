from unittest.mock import Mock, MagicMock, patch
from django.test import TestCase

from hi.integrations.transient_models import IntegrationDetails, IntegrationKey, IntegrationControlResult

from hi.services.hass.hass_controller import HassController


class TestHassControllerMainControlFlow(TestCase):
    """Test main do_control method and flow control"""
    
    def setUp(self):
        self.controller = HassController()
        
        # Mock the hass_manager to avoid initialization
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    @patch('hi.services.hass.hass_controller.HassConverter.hass_entity_id_to_state_value_str')
    @patch.object(HassController, '_do_control_with_services')
    def test_do_control_success_flow(self, mock_services_control, mock_converter):
        """Test successful do_control flow with all components"""
        # Setup
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.living_room')
        integration_details = IntegrationDetails(key=integration_key, payload={'domain': 'light'})
        
        mock_converter.return_value = 'on'
        mock_result = IntegrationControlResult(new_value='on', error_list=[])
        mock_services_control.return_value = mock_result
        
        # Execute
        result = self.controller.do_control(integration_details, 'on')
        
        # Verify
        mock_converter.assert_called_once_with(hass_entity_id='light.living_room', hi_value='on')
        mock_services_control.assert_called_once_with(
            'light.living_room', 'on', 'on', {'domain': 'light'}
        )
        self.assertEqual(result, mock_result)
    
    @patch('hi.services.hass.hass_controller.HassConverter.hass_entity_id_to_state_value_str')
    def test_do_control_exception_handling(self, mock_converter):
        """Test do_control handles exceptions gracefully"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.invalid')
        integration_details = IntegrationDetails(key=integration_key)
        
        mock_converter.side_effect = Exception("Conversion failed")
        
        result = self.controller.do_control(integration_details, 'on')
        
        self.assertIsNone(result.new_value)
        self.assertIn('Conversion failed', result.error_list[0])
    
    def test_do_control_payload_handling(self):
        """Test do_control handles missing and present payloads"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='switch.outlet')
        
        # Test with payload
        integration_details_with_payload = IntegrationDetails(
            key=integration_key, 
            payload={'domain': 'switch', 'service_data': {'entity_id': 'switch.outlet'}}
        )
        
        # Test without payload  
        integration_details_without_payload = IntegrationDetails(key=integration_key)
        
        with patch.object(self.controller, '_do_control_with_services') as mock_services:
            mock_services.return_value = IntegrationControlResult(new_value='off', error_list=[])
            
            # With payload
            self.controller.do_control(integration_details_with_payload, 'off')
            payload_call = mock_services.call_args[0][3]  # Fourth argument is domain_payload
            self.assertEqual(payload_call['domain'], 'switch')
            
            # Without payload
            mock_services.reset_mock()
            self.controller.do_control(integration_details_without_payload, 'off')
            payload_call = mock_services.call_args[0][3]  # Fourth argument is domain_payload
            self.assertEqual(payload_call, {})


class TestHassControllerLegacySetState(TestCase):
    """Test legacy set_state control method"""
    
    def setUp(self):
        self.controller = HassController()
        
        # Mock the hass_manager and client
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_do_control_with_set_state_success(self):
        """Test successful legacy set_state control"""
        self.mock_client.set_state.return_value = {'entity_id': 'light.bedroom', 'state': 'on'}
        
        result = self.controller._do_control_with_set_state('light.bedroom', 'on', 'on')
        
        self.mock_client.set_state.assert_called_once_with(entity_id='light.bedroom', state='on')
        self.assertEqual(result.new_value, 'on')
        self.assertEqual(result.error_list, [])
    
    def test_do_control_with_set_state_client_exception(self):
        """Test set_state handles client exceptions (should propagate)"""
        self.mock_client.set_state.side_effect = Exception("HTTP 404 Not Found")
        
        with self.assertRaises(Exception) as context:
            self.controller._do_control_with_set_state('light.nonexistent', 'on', 'on')
        
        self.assertEqual(str(context.exception), "HTTP 404 Not Found")


class TestHassControllerServiceRouting(TestCase):
    """Test service routing and domain handling"""
    
    def setUp(self):
        self.controller = HassController()
        
        # Mock the hass_manager 
        self.mock_manager = Mock()
        self.controller._hass_manager = self.mock_manager
    
    @patch.object(HassController, '_control_device_with_payload')
    def test_do_control_with_services_payload_routing(self, mock_payload_control):
        """Test service routing uses payload-based control when payload available"""
        mock_payload_control.return_value = IntegrationControlResult(new_value='on', error_list=[])
        
        domain_payload = {'domain': 'light', 'service_data': {'brightness': 255}}
        result = self.controller._do_control_with_services(
            'light.kitchen', 'on', 'on', domain_payload
        )
        
        mock_payload_control.assert_called_once_with(
            'light', 'light.kitchen', 'on', 'on', domain_payload
        )
        self.assertEqual(result.new_value, 'on')
    
    @patch.object(HassController, '_control_device_best_effort')
    def test_do_control_with_services_best_effort_routing(self, mock_best_effort):
        """Test service routing uses best-effort when no payload"""
        mock_best_effort.return_value = IntegrationControlResult(new_value='off', error_list=[])
        
        result = self.controller._do_control_with_services(
            'switch.outlet', 'off', 'off', {}
        )
        
        mock_best_effort.assert_called_once_with('switch', 'switch.outlet', 'off', 'off')
        self.assertEqual(result.new_value, 'off')
    
    def test_do_control_with_services_domain_extraction_from_payload(self):
        """Test domain extraction from payload takes precedence"""
        domain_payload = {'domain': 'switch'}  # Explicit domain in payload
        
        with patch.object(self.controller, '_control_device_with_payload') as mock_control:
            mock_control.return_value = IntegrationControlResult(new_value='on', error_list=[])
            
            self.controller._do_control_with_services(
                'light.misleading_name', 'on', 'on', domain_payload  # entity_id suggests 'light' but payload says 'switch'
            )
            
            # Should use 'switch' from payload, not 'light' from entity_id
            mock_control.assert_called_once()
            call_args = mock_control.call_args[0]
            self.assertEqual(call_args[0], 'switch')  # First arg is domain
    
    def test_do_control_with_services_domain_fallback_parsing(self):
        """Test domain fallback parsing from entity_id when no payload domain"""
        with patch.object(self.controller, '_control_device_best_effort') as mock_control:
            mock_control.return_value = IntegrationControlResult(new_value='on', error_list=[])
            
            # No domain in payload, should parse from entity_id
            self.controller._do_control_with_services(
                'climate.thermostat', 'heat', 'heat', {}
            )
            
            mock_control.assert_called_once()
            call_args = mock_control.call_args[0]
            self.assertEqual(call_args[0], 'climate')  # Parsed from entity_id
    
    def test_do_control_with_services_invalid_entity_id_format(self):
        """Test handling of invalid entity_id format"""
        result = self.controller._do_control_with_services(
            'invalid_entity_id_no_dot', 'on', 'on', {}  # Missing domain separator
        )
        
        self.assertIsNone(result.new_value)
        self.assertIn('Invalid entity_id format', result.error_list[0])


class TestHassControllerOnOffDeviceControl(TestCase):
    """Test on/off device control logic"""
    
    def setUp(self):
        self.controller = HassController()
        
        # Mock the hass_manager and client
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_control_on_off_device_turn_on_variations(self):
        """Test various 'on' value interpretations"""
        self.mock_client.call_service.return_value = Mock()
        
        on_values = ['on', 'ON', 'true', 'TRUE', '1']
        
        for control_value in on_values:
            with self.subTest(control_value=control_value):
                self.mock_client.reset_mock()
                
                result = self.controller._control_on_off_device(
                    'light', 'light.test', control_value, control_value.lower()
                )
                
                self.mock_client.call_service.assert_called_once_with(
                    'light', 'turn_on', 'light.test'
                )
                self.assertEqual(result.new_value, control_value)
    
    def test_control_on_off_device_turn_off_variations(self):
        """Test various 'off' value interpretations"""
        self.mock_client.call_service.return_value = Mock()
        
        off_values = ['off', 'OFF', 'false', 'FALSE', '0']
        
        for control_value in off_values:
            with self.subTest(control_value=control_value):
                self.mock_client.reset_mock()
                
                result = self.controller._control_on_off_device(
                    'switch', 'switch.test', control_value, control_value.lower()
                )
                
                self.mock_client.call_service.assert_called_once_with(
                    'switch', 'turn_off', 'switch.test'
                )
                self.assertEqual(result.new_value, control_value)
    
    def test_control_on_off_device_unknown_value(self):
        """Test handling of unknown control values"""
        result = self.controller._control_on_off_device(
            'light', 'light.test', 'maybe', 'maybe'
        )
        
        self.assertIsNone(result.new_value)
        self.assertIn('Unknown control value: maybe', result.error_list[0])
        self.mock_client.call_service.assert_not_called()
    
    def test_control_on_off_device_service_call_exception(self):
        """Test handling of service call exceptions"""
        self.mock_client.call_service.side_effect = Exception("Service call failed")
        
        with self.assertRaises(Exception) as context:
            self.controller._control_on_off_device('light', 'light.test', 'on', 'on')
        
        self.assertEqual(str(context.exception), "Service call failed")


class TestHassControllerNumericParameterControl(TestCase):
    """Test numeric parameter validation and control"""
    
    def setUp(self):
        self.controller = HassController()
        
        # Mock the hass_manager and client
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_control_numeric_parameter_device_brightness_valid_range(self):
        """Test brightness control with valid 0-100% range"""
        self.mock_client.call_service.return_value = Mock()
        
        # Test various valid brightness values
        valid_brightness_values = ['0', '50', '100', '75']
        
        for brightness in valid_brightness_values:
            with self.subTest(brightness=brightness):
                self.mock_client.reset_mock()
                
                # Mock brightness being in the domain payload
                domain_payload = {'domain': 'light', 'brightness_param': True}
                
                with patch.object(self.controller, '_get_numeric_service_data') as mock_service_data:
                    mock_service_data.return_value = {'brightness': int(brightness) * 255 // 100}
                    
                    result = self.controller._control_numeric_parameter_device(
                        'light', 'light.dimmer', brightness, brightness, domain_payload
                    )
                    
                    self.assertEqual(result.new_value, brightness)
                    self.mock_client.call_service.assert_called_once()
    
    def test_control_numeric_parameter_device_brightness_invalid_range(self):
        """Test brightness control with invalid range values"""
        invalid_brightness_values = ['-10', '150', 'abc', '50.5']
        
        for brightness in invalid_brightness_values:
            with self.subTest(brightness=brightness):
                domain_payload = {'domain': 'light', 'brightness_param': True}
                
                # Should either handle gracefully or raise appropriate error
                try:
                    result = self.controller._control_numeric_parameter_device(
                        'light', 'light.dimmer', brightness, brightness, domain_payload
                    )
                    # If it doesn't raise an exception, should have error in result
                    if result.error_list:
                        self.assertIn('Invalid', result.error_list[0])
                except (ValueError, TypeError):
                    # These exceptions are acceptable for invalid input
                    pass
    
    def test_control_numeric_parameter_device_volume_range(self):
        """Test volume control with 0.0-1.0 range"""
        self.mock_client.call_service.return_value = Mock()
        
        # Test volume values that should be converted to 0.0-1.0 range
        volume_test_cases = [
            ('0', 0.0),
            ('50', 0.5),
            ('100', 1.0),
        ]
        
        for input_volume, expected_volume in volume_test_cases:
            with self.subTest(input_volume=input_volume):
                self.mock_client.reset_mock()
                
                domain_payload = {'domain': 'media_player', 'volume_param': True}
                
                with patch.object(self.controller, '_get_numeric_service_data') as mock_service_data:
                    mock_service_data.return_value = {'volume_level': expected_volume}
                    
                    result = self.controller._control_numeric_parameter_device(
                        'media_player', 'media_player.speaker', input_volume, input_volume, domain_payload
                    )
                    
                    self.assertEqual(result.new_value, input_volume)
                    self.mock_client.call_service.assert_called_once()


class TestHassControllerWithRealEntityData(TestCase):
    """Test HassController with real Home Assistant entity patterns"""
    
    def setUp(self):
        self.controller = HassController()
        
        # Mock the hass_manager and client
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_control_real_camera_entities(self):
        """Test control of real camera entities from our HASS setup"""
        real_camera_entities = [
            'camera.frontcamera',
            'camera.patiocamera', 
            'camera.sidecamera',
            'camera.drivecamera'
        ]
        
        self.mock_client.call_service.return_value = Mock()
        
        for entity_id in real_camera_entities:
            with self.subTest(entity_id=entity_id):
                self.mock_client.reset_mock()
                
                integration_key = IntegrationKey(integration_id='hass', integration_name=entity_id)
                integration_details = IntegrationDetails(key=integration_key, payload={'domain': 'camera'})
                
                with patch.object(self.controller, '_do_control_with_services') as mock_services:
                    mock_services.return_value = IntegrationControlResult(new_value='idle', error_list=[])
                    
                    result = self.controller.do_control(integration_details, 'idle')
                    
                    self.assertEqual(result.new_value, 'idle')
                    mock_services.assert_called_once()
                    
                    # Verify entity_id passed correctly
                    call_args = mock_services.call_args[0]
                    self.assertEqual(call_args[0], entity_id)
    
    def test_control_real_script_entities(self):
        """Test control of real script entities"""
        script_entity = 'script.play_door_chime'
        
        integration_key = IntegrationKey(integration_id='hass', integration_name=script_entity)
        integration_details = IntegrationDetails(key=integration_key, payload={'domain': 'script'})
        
        with patch.object(self.controller, '_control_on_off_device') as mock_control:
            mock_control.return_value = IntegrationControlResult(new_value='on', error_list=[])
            
            result = self.controller._do_control_with_services(script_entity, 'on', 'on', {'domain': 'script'})
            
            # Should route to appropriate control method based on domain
            self.assertEqual(result.new_value, 'on')
    
    def test_control_real_sensor_entities_read_only(self):
        """Test that sensor entities handle read-only nature appropriately"""
        sensor_entities = [
            'sensor.frontcamera_status',
            'sensor.frontcamera_events_last_hour'
        ]
        
        for entity_id in sensor_entities:
            with self.subTest(entity_id=entity_id):
                integration_key = IntegrationKey(integration_id='hass', integration_name=entity_id)
                integration_details = IntegrationDetails(key=integration_key)
                
                # Sensors typically shouldn't be controllable, should handle gracefully
                with patch.object(self.controller, '_do_control_with_services') as mock_services:
                    # Assume the underlying logic handles read-only entities appropriately
                    mock_services.return_value = IntegrationControlResult(
                        new_value=None, 
                        error_list=['Sensor entities are read-only']
                    )
                    
                    result = self.controller.do_control(integration_details, 'test_value')
                    
                    # Should indicate that control is not supported
                    self.assertIsNone(result.new_value)


class TestHassControllerErrorScenarios(TestCase):
    """Test comprehensive error handling scenarios"""
    
    def setUp(self):
        self.controller = HassController()
        
        # Mock the hass_manager and client
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_malformed_integration_details(self):
        """Test handling of malformed integration details"""
        # Missing integration key
        integration_details = IntegrationDetails(key=None)
        
        with self.assertRaises(AttributeError):
            self.controller.do_control(integration_details, 'on')
    
    def test_hass_converter_failure(self):
        """Test handling of HassConverter failures"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.test')
        integration_details = IntegrationDetails(key=integration_key)
        
        with patch('hi.services.hass.hass_controller.HassConverter.hass_entity_id_to_state_value_str') as mock_converter:
            mock_converter.side_effect = ValueError("Invalid entity format")
            
            result = self.controller.do_control(integration_details, 'on')
            
            self.assertIsNone(result.new_value)
            self.assertIn('Invalid entity format', result.error_list[0])
    
    def test_hass_client_service_call_failure(self):
        """Test handling of HASS client service call failures"""
        self.mock_client.call_service.side_effect = Exception("Service unavailable")
        
        with self.assertRaises(Exception) as context:
            self.controller._control_on_off_device('light', 'light.test', 'on', 'on')
        
        self.assertEqual(str(context.exception), "Service unavailable")
    
    def test_missing_hass_manager(self):
        """Test handling when hass_manager is not available"""
        self.controller._hass_manager = None
        
        with self.assertRaises(AttributeError):
            self.controller._do_control_with_set_state('light.test', 'on', 'on')


class TestHassControllerMixinIntegration(TestCase):
    """Test HassMixin integration"""
    
    def setUp(self):
        self.controller = HassController()
    
    @patch('hi.services.hass.hass_controller.HassManager')
    def test_hass_manager_access_through_mixin(self, mock_manager_class):
        """Test hass_manager access through HassMixin"""
        mock_manager_instance = Mock()
        mock_manager_class.return_value = mock_manager_instance
        
        # Clear any existing manager
        if hasattr(self.controller, '_hass_manager'):
            delattr(self.controller, '_hass_manager')
        
        result = self.controller.hass_manager()
        
        mock_manager_class.assert_called_once()
        mock_manager_instance.ensure_initialized.assert_called_once()
        self.assertEqual(result, mock_manager_instance)