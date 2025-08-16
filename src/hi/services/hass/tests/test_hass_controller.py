from unittest.mock import Mock, patch
from django.test import TestCase

from hi.integrations.transient_models import IntegrationDetails, IntegrationKey, IntegrationControlResult

from hi.services.hass.hass_controller import HassController


class TestHassControllerBehaviorVerification(TestCase):
    """Test HassController focusing on behavior verification rather than mock validation"""
    
    def setUp(self):
        self.controller = HassController()
        
        # Mock only at system boundary - the HTTP client
        self.mock_client = Mock()
        
        # Mock hass_manager but let it provide real client reference
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        
        # Inject the manager (singleton pattern allows this)
        self.controller._hass_manager = self.mock_manager
    
    def test_do_control_light_on_returns_correct_result(self):
        """Test that light control returns the expected IntegrationControlResult with proper state"""
        # Setup - Light entity with on/off control and is_controllable flag
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.living_room')
        integration_details = IntegrationDetails(
            key=integration_key, 
            payload={
                'domain': 'light',
                'is_controllable': True,
                'on_service': 'turn_on',
                'off_service': 'turn_off'
            }
        )
        
        # Mock successful HTTP response
        self.mock_client.call_service.return_value = {'context': {'id': 'abc123'}}
        
        # Execute the actual control flow
        result = self.controller.do_control(integration_details, 'on')
        
        # Verify behavior: check the actual result object content
        self.assertIsInstance(result, IntegrationControlResult)
        self.assertEqual(result.new_value, 'on')
        self.assertEqual(result.error_list, [])
        
        # Verify the service call was made correctly (system boundary)
        self.mock_client.call_service.assert_called_once_with(
            domain='light', service='turn_on', hass_state_id='light.living_room'
        )
    
    def test_do_control_brightness_numeric_conversion_and_service_call(self):
        """Test brightness control handles numeric conversion and calls appropriate service"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.dining_room')
        integration_details = IntegrationDetails(
            key=integration_key, 
            payload={
                'domain': 'light',
                'is_controllable': True,
                'supports_brightness': True,
                'on_service': 'turn_on',
                'off_service': 'turn_off'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'brightness123'}}
        
        # Test brightness = 75 (should call turn_on with brightness_pct)
        result = self.controller.do_control(integration_details, '75')
        
        # Verify numeric conversion and result
        self.assertEqual(result.new_value, '75')
        self.assertEqual(result.error_list, [])
        
        # Verify correct service call with brightness parameter
        self.mock_client.call_service.assert_called_once_with(
            domain='light',
            service='turn_on', 
            hass_state_id='light.dining_room',
            service_data={'brightness_pct': 75}
        )
    
    def test_do_control_brightness_zero_turns_off_light(self):
        """Test that brightness = 0 correctly calls turn_off service instead of turn_on"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.bedroom')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'light',
                'is_controllable': True,
                'supports_brightness': True,
                'on_service': 'turn_on',
                'off_service': 'turn_off'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'off123'}}
        
        result = self.controller.do_control(integration_details, '0')
        
        # Verify 0 brightness correctly maps to 'off' behavior
        self.assertEqual(result.new_value, '0')
        self.assertEqual(result.error_list, [])
        
        # Verify turn_off was called, not turn_on
        self.mock_client.call_service.assert_called_once_with(
            domain='light',
            service='turn_off',
            hass_state_id='light.bedroom',
            service_data=None
        )

    def test_do_control_volume_validation_and_service_call(self):
        """Test volume control validates range and makes correct service call"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='media_player.living_room')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'media_player',
                'is_controllable': True,
                'parameters': {'volume_level': True},
                'set_service': 'volume_set'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'vol123'}}
        
        # Test valid volume (0.7)
        result = self.controller.do_control(integration_details, '0.7')
        
        self.assertEqual(result.new_value, '0.7')
        self.assertEqual(result.error_list, [])
        
        self.mock_client.call_service.assert_called_once_with(
            domain='media_player',
            service='volume_set',
            hass_state_id='media_player.living_room',
            service_data={'volume_level': 0.7}
        )
    
    def test_do_control_invalid_volume_returns_error(self):
        """Test that invalid volume values return appropriate errors without service calls"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='media_player.bedroom')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'media_player',
                'is_controllable': True,
                'parameters': {'volume_level': True},
                'set_service': 'volume_set'
            }
        )
        
        # Test invalid volume (1.5 > 1.0)
        result = self.controller.do_control(integration_details, '1.5')
        
        # Should return error without making service call
        self.assertIsNone(result.new_value)
        self.assertTrue(len(result.error_list) > 0)
        self.assertIn('Invalid volume value', result.error_list[0])
        
        # Verify no service call was made
        self.mock_client.call_service.assert_not_called()


class TestHassControllerErrorHandlingBehavior(TestCase):
    """Test comprehensive error handling behavior and recovery"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_exception_during_conversion_returns_error_result(self):
        """Test that conversion exceptions are caught and returned as error results"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.invalid')
        integration_details = IntegrationDetails(key=integration_key)
        
        # Patch the converter to raise an exception
        with patch('hi.services.hass.hass_controller.HassConverter.hass_entity_id_to_state_value_str') as mock_converter:
            mock_converter.side_effect = ValueError("Invalid entity format")
            
            result = self.controller.do_control(integration_details, 'on')
            
            # Verify exception is caught and returned as error
            self.assertIsNone(result.new_value)
            self.assertEqual(len(result.error_list), 1)
            self.assertIn('Invalid entity format', result.error_list[0])
            
            # Verify no service call was attempted
            self.mock_client.call_service.assert_not_called()
    
    def test_malformed_integration_details_handled_gracefully(self):
        """Test handling of malformed integration details returns proper error"""
        # Integration details with None key
        integration_details = IntegrationDetails(key=None)
        
        result = self.controller.do_control(integration_details, 'on')
        
        # Should handle gracefully and return error
        self.assertIsNone(result.new_value)
        self.assertTrue(len(result.error_list) > 0)
        self.assertIn("'NoneType' object has no attribute 'integration_name'", result.error_list[0])
        
        # No service calls should be made
        self.mock_client.call_service.assert_not_called()


class TestHassControllerDomainRoutingBehavior(TestCase):
    """Test domain routing and payload vs best-effort decisions"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_payload_based_routing_with_explicit_services(self):
        """Test that payload with explicit services uses payload-based control path"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='cover.garage_door')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'cover',
                'is_controllable': True,
                'open_service': 'open_cover',
                'close_service': 'close_cover'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'cover123'}}
        
        # Test 'open' command uses payload service definition
        result = self.controller.do_control(integration_details, 'open')
        
        self.assertEqual(result.new_value, 'open')
        self.assertEqual(result.error_list, [])
        
        # Should use the explicit service from payload
        self.mock_client.call_service.assert_called_once_with(
            domain='cover',
            service='open_cover',
            hass_state_id='cover.garage_door'
        )
    
    def test_best_effort_routing_without_payload(self):
        """Test that missing payload triggers best-effort control with domain parsing"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='switch.outlet')
        integration_details = IntegrationDetails(key=integration_key)  # No payload
        
        self.mock_client.call_service.return_value = {'context': {'id': 'switch123'}}
        
        result = self.controller.do_control(integration_details, 'off')
        
        # Should succeed using best-effort patterns
        self.assertEqual(result.new_value, 'off')
        self.assertEqual(result.error_list, [])
        
        # Should use standard turn_off service for switch domain
        self.mock_client.call_service.assert_called_once_with(
            domain='switch',
            service='turn_off',
            hass_state_id='switch.outlet'
        )
    
    def test_payload_domain_overrides_entity_id_domain(self):
        """Test that explicit domain in payload overrides domain parsed from entity_id"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.misleading_name')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'switch',  # Override: this is actually a switch, not a light
                'is_controllable': True,
                'on_service': 'turn_on',
                'off_service': 'turn_off'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'switch123'}}
        
        result = self.controller.do_control(integration_details, 'on')
        
        self.assertEqual(result.new_value, 'on')
        self.assertEqual(result.error_list, [])
        
        # Should use 'switch' domain from payload, not 'light' from entity_id
        self.mock_client.call_service.assert_called_once_with(
            domain='switch',  # From payload, not entity_id
            service='turn_on',
            hass_state_id='light.misleading_name'
        )
    
    def test_climate_temperature_control_with_best_effort(self):
        """Test climate domain numeric temperature control via best-effort routing"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='climate.thermostat')
        integration_details = IntegrationDetails(key=integration_key)  # No payload - triggers best-effort
        
        self.mock_client.call_service.return_value = {'context': {'id': 'climate123'}}
        
        result = self.controller.do_control(integration_details, '72.5')
        
        # Should parse domain and handle numeric temperature
        self.assertEqual(result.new_value, '72.5')
        self.assertEqual(result.error_list, [])
        
        # Should use climate-specific service
        self.mock_client.call_service.assert_called_once_with(
            domain='climate',
            service='set_temperature',
            hass_state_id='climate.thermostat',
            service_data={'temperature': 72.5}
        )
    
    def test_invalid_entity_id_format_returns_error(self):
        """Test that malformed entity_id returns error without attempting service calls"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='invalid_entity_id_no_dot')
        integration_details = IntegrationDetails(key=integration_key)  # No payload
        
        result = self.controller.do_control(integration_details, 'on')
        
        # Should return error for malformed entity_id
        self.assertIsNone(result.new_value)
        self.assertTrue(len(result.error_list) > 0)
        self.assertIn('Invalid entity_id format', result.error_list[0])
        
        # No service calls should be attempted
        self.mock_client.call_service.assert_not_called()


class TestHassControllerValueTransformationBehavior(TestCase):
    """Test value transformation and service mapping behavior"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_on_value_variations_all_map_to_turn_on(self):
        """Test that various 'on' representations all result in turn_on service call"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.test')
        
        # Note: '1' is treated as numeric brightness, not boolean 'on'
        on_values = ['on', 'ON', 'true', 'TRUE']
        
        for control_value in on_values:
            with self.subTest(control_value=control_value):
                self.mock_client.reset_mock()
                
                integration_details = IntegrationDetails(key=integration_key)
                self.mock_client.call_service.return_value = {'context': {'id': f'test_{control_value}'}}
                
                result = self.controller.do_control(integration_details, control_value)
                
                # Verify behavior: all variations should result in 'turn_on' service
                self.assertEqual(result.new_value, control_value)
                self.assertEqual(result.error_list, [])
                
                self.mock_client.call_service.assert_called_once_with(
                    domain='light', service='turn_on', hass_state_id='light.test'
                )
    
    def test_numeric_one_treated_as_brightness_not_boolean(self):
        """Test that '1' is treated as brightness=1%, not boolean on"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.test')
        integration_details = IntegrationDetails(key=integration_key)
        
        self.mock_client.call_service.return_value = {'context': {'id': 'test_1'}}
        
        result = self.controller.do_control(integration_details, '1')
        
        # '1' should be treated as brightness 1% (best-effort numeric control)
        self.assertEqual(result.new_value, '1')
        self.assertEqual(result.error_list, [])
        
        # Should call turn_on with brightness_pct=1
        self.mock_client.call_service.assert_called_once_with(
            domain='light',
            service='turn_on',
            hass_state_id='light.test',
            service_data={'brightness_pct': 1}
        )
    
    def test_off_value_variations_all_map_to_turn_off(self):
        """Test that various 'off' representations all result in turn_off service call"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='switch.test')
        
        # Note: '0' is treated differently for switches (no brightness support)
        off_values = ['off', 'OFF', 'false', 'FALSE']
        
        for control_value in off_values:
            with self.subTest(control_value=control_value):
                self.mock_client.reset_mock()
                
                integration_details = IntegrationDetails(key=integration_key)
                self.mock_client.call_service.return_value = {'context': {'id': f'test_{control_value}'}}
                
                result = self.controller.do_control(integration_details, control_value)
                
                # Verify behavior: all variations should result in 'turn_off' service
                self.assertEqual(result.new_value, control_value)
                self.assertEqual(result.error_list, [])
                
                self.mock_client.call_service.assert_called_once_with(
                    domain='switch', service='turn_off', hass_state_id='switch.test'
                )
    
    def test_numeric_zero_on_switch_returns_error(self):
        """Test that '0' on a switch (no brightness) returns error"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='switch.test')
        integration_details = IntegrationDetails(key=integration_key)
        
        result = self.controller.do_control(integration_details, '0')
        
        # '0' is numeric, switches don't support numeric control in best-effort mode
        self.assertIsNone(result.new_value)
        self.assertTrue(len(result.error_list) > 0)
        self.assertIn('No numeric control pattern', result.error_list[0])
    
    def test_unknown_control_value_returns_error_without_service_call(self):
        """Test that unrecognized control values return errors without attempting service calls"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.test')
        integration_details = IntegrationDetails(key=integration_key)
        
        result = self.controller.do_control(integration_details, 'maybe')
        
        # Should return error without making any service calls
        self.assertIsNone(result.new_value)
        self.assertTrue(len(result.error_list) > 0)
        self.assertIn('Unknown control value: maybe', result.error_list[0])
        
        self.mock_client.call_service.assert_not_called()
    
    def test_cover_domain_uses_specific_services_for_open_close(self):
        """Test that cover domain maps open/close to cover-specific services"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='cover.garage')
        integration_details = IntegrationDetails(key=integration_key)
        
        self.mock_client.call_service.return_value = {'context': {'id': 'cover123'}}
        
        # Test 'open' maps to open_cover
        result_open = self.controller.do_control(integration_details, 'open')
        
        self.assertEqual(result_open.new_value, 'open')
        self.assertEqual(result_open.error_list, [])
        
        self.mock_client.call_service.assert_called_with(
            domain='cover', service='open_cover', hass_state_id='cover.garage'
        )
        
        # Reset and test 'close' maps to close_cover
        self.mock_client.reset_mock()
        result_close = self.controller.do_control(integration_details, 'close')
        
        self.assertEqual(result_close.new_value, 'close')
        self.assertEqual(result_close.error_list, [])
        
        self.mock_client.call_service.assert_called_with(
            domain='cover', service='close_cover', hass_state_id='cover.garage'
        )


class TestHassControllerHttpExceptionHandling(TestCase):
    """Test HTTP exception handling and propagation behavior"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_http_service_call_exception_not_caught_in_best_effort(self):
        """Test that HTTP exceptions in best-effort control are caught and returned as errors"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.test')
        integration_details = IntegrationDetails(key=integration_key)  # No payload - triggers best-effort
        
        # Simulate HTTP failure
        self.mock_client.call_service.side_effect = Exception("HTTP 503 Service Unavailable")
        
        # In best-effort mode, exceptions are caught and returned as errors
        result = self.controller.do_control(integration_details, 'on')
        
        # Should return error result, not propagate exception
        self.assertIsNone(result.new_value)
        self.assertTrue(len(result.error_list) > 0)
        self.assertIn('Best-effort control failed', result.error_list[0])
        self.assertIn('HTTP 503 Service Unavailable', result.error_list[0])
    
    def test_set_state_http_exception_propagates(self):
        """Test that set_state HTTP exceptions propagate correctly"""
        self.mock_client.set_state.side_effect = Exception("HTTP 404 Not Found")
        
        with self.assertRaises(Exception) as context:
            self.controller._do_control_with_set_state('light.nonexistent', 'on', 'on')
        
        self.assertEqual(str(context.exception), "HTTP 404 Not Found")


class TestHassControllerNumericValidationBehavior(TestCase):
    """Test numeric parameter validation and boundary behavior"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_brightness_boundary_values_handled_correctly(self):
        """Test brightness boundary values (0, 100) are handled correctly"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.dimmer')
        
        # Test brightness = 0 (should turn off)
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'light',
                'is_controllable': True,
                'supports_brightness': True,
                'on_service': 'turn_on',
                'off_service': 'turn_off'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'bright0'}}
        
        result = self.controller.do_control(integration_details, '0')
        
        # Brightness 0 should call turn_off, not turn_on
        self.assertEqual(result.new_value, '0')
        self.assertEqual(result.error_list, [])
        
        self.mock_client.call_service.assert_called_once_with(
            domain='light',
            service='turn_off',
            hass_state_id='light.dimmer',
            service_data=None
        )
        
        # Test brightness = 100 (should turn on with full brightness)
        self.mock_client.reset_mock()
        
        result = self.controller.do_control(integration_details, '100')
        
        self.assertEqual(result.new_value, '100')
        self.assertEqual(result.error_list, [])
        
        self.mock_client.call_service.assert_called_once_with(
            domain='light',
            service='turn_on',
            hass_state_id='light.dimmer',
            service_data={'brightness_pct': 100}
        )
    
    def test_brightness_invalid_values_return_errors(self):
        """Test that invalid brightness values return errors without service calls"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.dimmer')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'light',
                'is_controllable': True,
                'supports_brightness': True,
                'on_service': 'turn_on',
                'off_service': 'turn_off'
            }
        )
        
        invalid_brightness_values = ['-10', '150', 'abc']
        
        for brightness in invalid_brightness_values:
            with self.subTest(brightness=brightness):
                self.mock_client.reset_mock()
                
                result = self.controller.do_control(integration_details, brightness)
                
                # Should return error without service call
                if brightness == 'abc':
                    # Non-numeric values should be caught early
                    self.assertIsNone(result.new_value)
                    self.assertTrue(len(result.error_list) > 0)
                else:
                    # Numeric but out-of-range values
                    self.assertIsNone(result.new_value)
                    self.assertTrue(len(result.error_list) > 0)
                    self.assertIn('Invalid brightness value', result.error_list[0])
                
                # No service calls should be made for invalid values
                self.mock_client.call_service.assert_not_called()
    
    def test_volume_boundary_validation_enforced(self):
        """Test that volume boundary validation (0.0-1.0) is properly enforced"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='media_player.speaker')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'media_player',
                'is_controllable': True,
                'parameters': {'volume_level': True},
                'set_service': 'volume_set'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'vol123'}}
        
        # Test valid boundary values
        valid_volumes = ['0.0', '0.5', '1.0']
        
        for volume in valid_volumes:
            with self.subTest(volume=volume):
                self.mock_client.reset_mock()
                
                result = self.controller.do_control(integration_details, volume)
                
                self.assertEqual(result.new_value, volume)
                self.assertEqual(result.error_list, [])
                
                self.mock_client.call_service.assert_called_once_with(
                    domain='media_player',
                    service='volume_set',
                    hass_state_id='media_player.speaker',
                    service_data={'volume_level': float(volume)}
                )
        
        # Test invalid values (outside 0.0-1.0 range)
        invalid_volumes = ['-0.1', '1.1', '2.0']
        
        for volume in invalid_volumes:
            with self.subTest(volume=volume):
                self.mock_client.reset_mock()
                
                result = self.controller.do_control(integration_details, volume)
                
                # Should return error
                self.assertIsNone(result.new_value)
                self.assertTrue(len(result.error_list) > 0)
                self.assertIn('Invalid volume value', result.error_list[0])
                
                # No service call should be made
                self.mock_client.call_service.assert_not_called()


class TestHassControllerCoverPositionBehavior(TestCase):
    """Test cover position control behavior and validation"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_cover_position_percentage_control(self):
        """Test cover position control with percentage values"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='cover.blinds')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'cover',
                'is_controllable': True,
                'parameters': {'position': True},
                'set_service': 'set_cover_position'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'pos123'}}
        
        # Test 50% position
        result = self.controller.do_control(integration_details, '50')
        
        self.assertEqual(result.new_value, '50')
        self.assertEqual(result.error_list, [])
        
        self.mock_client.call_service.assert_called_once_with(
            domain='cover',
            service='set_cover_position',
            hass_state_id='cover.blinds',
            service_data={'position': 50}
        )


class TestHassControllerRealWorldEntityBehavior(TestCase):
    """Test behavior with real-world entity patterns from Home Assistant"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_camera_entities_handle_non_controllable_gracefully(self):
        """Test that camera entities (typically non-controllable) are handled appropriately"""
        real_camera_entities = [
            'camera.frontcamera',
            'camera.patiocamera', 
            'camera.sidecamera',
            'camera.drivecamera'
        ]
        
        for entity_id in real_camera_entities:
            with self.subTest(entity_id=entity_id):
                self.mock_client.reset_mock()
                
                integration_key = IntegrationKey(integration_id='hass', integration_name=entity_id)
                # Camera without is_controllable flag should fallback to best-effort
                integration_details = IntegrationDetails(
                    key=integration_key, 
                    payload={'domain': 'camera'}  # No is_controllable or services defined
                )
                
                result = self.controller.do_control(integration_details, 'idle')
                
                # Should attempt best-effort control or return error
                # Since 'idle' is not a standard on/off value, should return error
                self.assertIsNone(result.new_value)
                self.assertTrue(len(result.error_list) > 0)
                self.assertIn('Unknown control value', result.error_list[0])
    
    def test_script_entities_execute_with_turn_on_service(self):
        """Test that script entities execute using turn_on service"""
        script_entity = 'script.play_door_chime'
        
        integration_key = IntegrationKey(integration_id='hass', integration_name=script_entity)
        integration_details = IntegrationDetails(
            key=integration_key, 
            payload={'domain': 'script'}  # Scripts use turn_on to execute
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'script123'}}
        
        result = self.controller.do_control(integration_details, 'on')
        
        # Scripts should execute with turn_on service
        self.assertEqual(result.new_value, 'on')
        self.assertEqual(result.error_list, [])
        
        self.mock_client.call_service.assert_called_once_with(
            domain='script',
            service='turn_on',
            hass_state_id=script_entity
        )
    
    def test_sensor_entities_return_error_for_control_attempts(self):
        """Test that sensor entities (read-only) return appropriate errors"""
        sensor_entities = [
            'sensor.frontcamera_status',
            'sensor.frontcamera_events_last_hour'
        ]
        
        for entity_id in sensor_entities:
            with self.subTest(entity_id=entity_id):
                self.mock_client.reset_mock()
                
                integration_key = IntegrationKey(integration_id='hass', integration_name=entity_id)
                integration_details = IntegrationDetails(key=integration_key)  # No payload
                
                result = self.controller.do_control(integration_details, 'test_value')
                
                # Sensors are not controllable - should return error
                self.assertIsNone(result.new_value)
                self.assertTrue(len(result.error_list) > 0)
                
                # Should not attempt any service calls for sensors
                self.mock_client.call_service.assert_not_called()


class TestHassControllerLegacySetStateBehavior(TestCase):
    """Test legacy set_state method behavior and error handling"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_set_state_returns_control_value_on_success(self):
        """Test that set_state returns the control value (not HA response) on success"""
        # Mock successful HTTP response from HA
        self.mock_client.set_state.return_value = {
            'entity_id': 'light.bedroom',
            'state': 'on',
            'attributes': {'brightness': 255}
        }
        
        result = self.controller._do_control_with_set_state('light.bedroom', 'bright', 'on')
        
        # Should return the original control value, not the HA state
        self.assertEqual(result.new_value, 'bright')  # Not 'on' from HA response
        self.assertEqual(result.error_list, [])
        
        # Verify correct HA API call
        self.mock_client.set_state.assert_called_once_with(
            entity_id='light.bedroom',
            state='on'  # Converted HA state value
        )
    
    def test_set_state_propagates_http_exceptions(self):
        """Test that set_state propagates HTTP exceptions without catching them"""
        self.mock_client.set_state.side_effect = Exception("HTTP 401 Unauthorized")
        
        with self.assertRaises(Exception) as context:
            self.controller._do_control_with_set_state('light.test', 'on', 'on')
        
        self.assertEqual(str(context.exception), "HTTP 401 Unauthorized")


class TestHassControllerIntegrationBehavior(TestCase):
    """Test integration behavior between components"""
    
    def setUp(self):
        self.controller = HassController()
        self.mock_client = Mock()
        self.mock_manager = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.controller._hass_manager = self.mock_manager
    
    def test_multiple_sequential_controls_maintain_state(self):
        """Test that multiple sequential control operations work correctly"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='light.living_room')
        integration_details = IntegrationDetails(
            key=integration_key,
            payload={
                'domain': 'light',
                'is_controllable': True,
                'supports_brightness': True,
                'on_service': 'turn_on',
                'off_service': 'turn_off'
            }
        )
        
        self.mock_client.call_service.return_value = {'context': {'id': 'seq123'}}
        
        # Sequence: off -> on -> brightness 50 -> off
        control_sequence = [
            ('off', 'turn_off', None),
            ('on', 'turn_on', None),
            ('50', 'turn_on', {'brightness_pct': 50}),
            ('off', 'turn_off', None)
        ]
        
        for control_value, expected_service, expected_data in control_sequence:
            with self.subTest(control_value=control_value):
                self.mock_client.reset_mock()
                
                result = self.controller.do_control(integration_details, control_value)
                
                self.assertEqual(result.new_value, control_value)
                self.assertEqual(result.error_list, [])
                
                # Verify the correct service was called
                self.mock_client.call_service.assert_called_once_with(
                    domain='light',
                    service=expected_service,
                    hass_state_id='light.living_room',
                    **(dict(service_data=expected_data) if expected_data else {})
                )
    
    def test_lock_domain_uses_lock_unlock_services(self):
        """Test that lock domain correctly maps open/close to unlock/lock"""
        integration_key = IntegrationKey(integration_id='hass', integration_name='lock.front_door')
        integration_details = IntegrationDetails(key=integration_key)  # No payload - best effort
        
        self.mock_client.call_service.return_value = {'context': {'id': 'lock123'}}
        
        # Test 'open' maps to 'unlock' for locks
        result = self.controller.do_control(integration_details, 'open')
        
        self.assertEqual(result.new_value, 'open')
        self.assertEqual(result.error_list, [])
        
        self.mock_client.call_service.assert_called_once_with(
            domain='lock',
            service='unlock',  # 'open' -> 'unlock' for locks
            hass_state_id='lock.front_door'
        )
        
        # Test 'close' maps to 'lock' for locks
        self.mock_client.reset_mock()
        
        result = self.controller.do_control(integration_details, 'close')
        
        self.assertEqual(result.new_value, 'close')
        self.assertEqual(result.error_list, [])
        
        self.mock_client.call_service.assert_called_once_with(
            domain='lock',
            service='lock',  # 'close' -> 'lock' for locks  
            hass_state_id='lock.front_door'
        )
    
    @patch('hi.services.hass.hass_mixins.HassManager')
    def test_hass_manager_singleton_behavior(self, mock_manager_class):
        """Test that HassManager maintains singleton behavior through mixin"""
        mock_manager_instance = Mock()
        mock_manager_class.return_value = mock_manager_instance
        
        # Clear any existing manager
        if hasattr(self.controller, '_hass_manager'):
            delattr(self.controller, '_hass_manager')
        
        # First access
        manager1 = self.controller.hass_manager()
        
        # Second access should return cached instance
        manager2 = self.controller.hass_manager()
        
        # Should be same instance (singleton)
        self.assertIs(manager1, manager2)
        
        # Manager class should only be instantiated once
        mock_manager_class.assert_called_once()
        
        # ensure_initialized called only on first access (singleton already initialized)
        mock_manager_instance.ensure_initialized.assert_called_once()
