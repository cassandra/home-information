import json
import os
from django.test import TestCase
from unittest.mock import patch, MagicMock

from hi.apps.entity.enums import EntityStateType
from hi.apps.entity.models import Entity
from hi.integrations.transient_models import IntegrationKey
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassApi


class TestHassConverterMapping(TestCase):
    """
    Test the new mapping-based converter methods using real HA API data
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Load the real HA states data
        test_data_path = os.path.join(os.path.dirname(__file__), 'data', 'hass-states.json')
        with open(test_data_path, 'r') as f:
            cls.real_ha_states_data = json.load(f)

    def setUp(self):
        # Create a mock entity for testing
        self.mock_entity = MagicMock(spec=Entity)
        self.mock_entity.name = "Test Entity"
        
    def test_determine_entity_state_type_from_mapping_light_dimmer(self):
        """Test that dimmer lights are correctly identified"""
        
        # Find a real dimmer light from the test data
        dimmer_data = None
        for state_data in self.real_ha_states_data:
            if ( state_data.get('entity_id', '').startswith('light.switchlinc_dimmer')
                 or state_data.get('entity_id', '').startswith('light.keypadlinc_dimmer') ):
                dimmer_data = state_data
                break
        
        self.assertIsNotNone(dimmer_data, "Should find a dimmer light in test data")
        
        # Create HassState from real data
        hass_state = HassConverter.create_hass_state(dimmer_data)
        
        # Test the mapping
        entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
        
        # Should be LIGHT_DIMMER if it has brightness capability
        if 'brightness' in dimmer_data.get('attributes', {}):
            self.assertEqual(entity_state_type, EntityStateType.LIGHT_DIMMER)
        else:
            # Fallback to ON_OFF if no brightness detected
            self.assertEqual(entity_state_type, EntityStateType.ON_OFF)

    def test_determine_entity_state_type_from_mapping_light_onoff(self):
        """Test that regular (non-dimmer) lights are correctly identified"""
        
        # Find a regular relay light from the test data
        relay_data = None
        for state_data in self.real_ha_states_data:
            if ( state_data.get('entity_id', '').startswith('light.switchlinc_relay')
                 and state_data.get('attributes', {}).get('color_mode') == 'onoff' ):
                relay_data = state_data
                break
        
        self.assertIsNotNone(relay_data, "Should find a relay light in test data")
        
        # Create HassState from real data
        hass_state = HassConverter.create_hass_state(relay_data)
        
        # Test the mapping
        entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
        
        # Should be ON_OFF for relay lights
        self.assertEqual(entity_state_type, EntityStateType.ON_OFF)

    def test_determine_entity_state_type_from_mapping_switch(self):
        """Test that switches are correctly identified"""
        
        # Find a switch from the test data
        switch_data = None
        for state_data in self.real_ha_states_data:
            if state_data.get('entity_id', '').startswith('switch.'):
                switch_data = state_data
                break
        
        self.assertIsNotNone(switch_data, "Should find a switch in test data")
        
        # Create HassState from real data
        hass_state = HassConverter.create_hass_state(switch_data)
        
        # Test the mapping
        entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
        
        # Should be ON_OFF for switches
        self.assertEqual(entity_state_type, EntityStateType.ON_OFF)

    def test_determine_entity_state_type_from_mapping_binary_sensor(self):
        """Test that binary sensors are correctly identified"""
        
        # Find a binary sensor from the test data
        binary_sensor_data = None
        for state_data in self.real_ha_states_data:
            if state_data.get('entity_id', '').startswith('binary_sensor.'):
                binary_sensor_data = state_data
                break
        
        self.assertIsNotNone(binary_sensor_data, "Should find a binary sensor in test data")
        
        # Create HassState from real data
        hass_state = HassConverter.create_hass_state(binary_sensor_data)
        
        # Test the mapping
        entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
        
        # Should be appropriate sensor type based on device class
        device_class = hass_state.device_class
        if device_class == HassApi.MOTION_DEVICE_CLASS:
            self.assertEqual(entity_state_type, EntityStateType.MOVEMENT)
        elif device_class == HassApi.CONNECTIVITY_DEVICE_CLASS:
            self.assertEqual(entity_state_type, EntityStateType.CONNECTIVITY)
        else:
            # Default for binary sensors
            self.assertEqual(entity_state_type, EntityStateType.ON_OFF)

    def test_has_brightness_capability(self):
        """Test brightness detection for lights"""
        
        # Test with a known dimmer light
        dimmer_data = None
        for state_data in self.real_ha_states_data:
            if ( state_data.get('entity_id', '').startswith('light.')
                 and 'brightness' in state_data.get('attributes', {}) ):
                dimmer_data = state_data
                break
        
        if dimmer_data:
            hass_state = HassConverter.create_hass_state(dimmer_data)
            has_brightness = HassConverter._has_brightness_capability(hass_state)
            self.assertTrue(has_brightness, "Should detect brightness capability")
        
        # Test with a regular light
        relay_data = None
        for state_data in self.real_ha_states_data:
            if ( state_data.get('entity_id', '').startswith('light.')
                 and state_data.get('attributes', {}).get('color_mode') == 'onoff' ):
                relay_data = state_data
                break
        
        if relay_data:
            hass_state = HassConverter.create_hass_state(relay_data)
            has_brightness = HassConverter._has_brightness_capability(hass_state)
            self.assertFalse(has_brightness, "Should not detect brightness capability for relay lights")

    def test_is_controllable_domain_and_type(self):
        """Test controllability detection"""
        
        # Test controllable combinations
        self.assertTrue(
            HassConverter._is_controllable_domain_and_type( HassApi.LIGHT_DOMAIN,
                                                            EntityStateType.ON_OFF )
        )
        self.assertTrue(
            HassConverter._is_controllable_domain_and_type( HassApi.LIGHT_DOMAIN,
                                                            EntityStateType.LIGHT_DIMMER )
        )
        self.assertTrue(
            HassConverter._is_controllable_domain_and_type( HassApi.SWITCH_DOMAIN,
                                                            EntityStateType.ON_OFF )
        )
        
        # Test non-controllable combinations
        self.assertFalse(
            HassConverter._is_controllable_domain_and_type( HassApi.SENSOR_DOMAIN,
                                                            EntityStateType.TEMPERATURE )
        )
        self.assertFalse(
            HassConverter._is_controllable_domain_and_type( HassApi.BINARY_SENSOR_DOMAIN,
                                                            EntityStateType.MOVEMENT )
        )

    @patch('hi.apps.model_helper.HiModelHelper.create_on_off_controller')
    @patch('hi.apps.model_helper.HiModelHelper.create_light_dimmer_controller')
    @patch('hi.apps.model_helper.HiModelHelper.create_blob_sensor')
    def test_create_hass_state_with_mapping_integration( self, 
                                                         mock_blob_sensor,
                                                         mock_light_dimmer_controller,
                                                         mock_on_off_controller ):
        """Test the complete integration of the new mapping method"""
        
        # Mock the return values
        mock_controller = MagicMock()
        mock_controller.integration_metadata = {}
        mock_controller.entity_state = MagicMock()
        mock_on_off_controller.return_value = mock_controller
        mock_light_dimmer_controller.return_value = mock_controller
        
        mock_sensor = MagicMock()
        mock_sensor.integration_metadata = {}
        mock_sensor.entity_state = MagicMock()
        mock_blob_sensor.return_value = mock_sensor
        
        # Test with a controllable light
        light_data = None
        for state_data in self.real_ha_states_data:
            if state_data.get('entity_id', '').startswith('light.'):
                light_data = state_data
                break
        
        if light_data:
            hass_state = HassConverter.create_hass_state(light_data)
            integration_key = IntegrationKey(
                integration_id='hass',
                integration_name=hass_state.entity_id
            )
            
            # Call the new method
            entity_state = HassConverter._create_hass_state_with_mapping(
                hass_device=MagicMock(),
                hass_state=hass_state,
                entity=self.mock_entity,
                integration_key=integration_key,
                add_alarm_events=False
            )
            
            # Should have created a controller and stored metadata
            self.assertIsNotNone(entity_state)
            
            # Check that metadata was stored (either controller or sensor should have been called)
            metadata_stored = (mock_controller.integration_metadata or mock_sensor.integration_metadata)
            self.assertIsNotNone(metadata_stored)
            
            # Metadata should contain domain info
            if mock_controller.integration_metadata:
                self.assertIn('domain', mock_controller.integration_metadata)
                self.assertEqual(mock_controller.integration_metadata['domain'], HassApi.LIGHT_DOMAIN)

    def test_domain_parsing_consistency(self):
        """Test that domain parsing is consistent across all real entities"""
        
        for state_data in self.real_ha_states_data[:10]:  # Test first 10 entities
            entity_id = state_data.get('entity_id', '')
            if '.' in entity_id:
                expected_domain = entity_id.split('.', 1)[0]
                
                # Create HassState and check domain
                hass_state = HassConverter.create_hass_state(state_data)
                
                self.assertEqual(hass_state.domain, expected_domain,
                                 f"Domain parsing failed for {entity_id}")
                
                # Should also have a mapping for this domain (or fallback to BLOB)
                entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
                self.assertIsNotNone(entity_state_type,
                                     f"Should have EntityStateType mapping for domain {expected_domain}")

    def test_service_mapping_completeness(self):
        """Test that all controllable domains have service mappings"""
        
        controllable_domains = HassConverter.ALL_CONTROLLABLE_DOMAINS
        
        for domain in controllable_domains:
            # Each controllable domain should have at least one service mapping
            has_mapping = any(
                key[0] == domain 
                for key in HassConverter.CONTROL_SERVICE_MAPPING.keys()
            )
            self.assertTrue(has_mapping, f"Domain {domain} should have service mappings")
