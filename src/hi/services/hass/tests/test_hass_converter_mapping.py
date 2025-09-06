import json
import logging
import os
from django.test import TestCase
from unittest.mock import Mock

from hi.apps.entity.enums import EntityStateType, EntityType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.control.models import Controller
from hi.apps.sense.models import Sensor
from hi.integrations.transient_models import IntegrationKey
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassApi, HassDevice

logging.disable(logging.CRITICAL)


class TestHassConverterMapping(TestCase):
    """
    Test the mapping-based converter methods using real HA API data.
    Focus on testing actual behavior rather than mocking internals.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Load the real HA states data
        test_data_path = os.path.join(os.path.dirname(__file__), 'data', 'hass-states.json')
        with open(test_data_path, 'r') as f:
            cls.real_ha_states_data = json.load(f)

    def setUp(self):
        # Create a real entity for testing instead of a mock
        self.test_entity = Entity.objects.create(
            name="Test Entity",
            entity_type=EntityType.OTHER
        )
        
    def test_determine_entity_state_type_from_mapping_light_dimmer(self):
        """Test that dimmer lights are correctly identified with comprehensive checks"""
        
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
        
        # Verify HassState properties are correctly parsed
        self.assertEqual(hass_state.domain, HassApi.LIGHT_DOMAIN)
        self.assertIsNotNone(hass_state.entity_id)
        self.assertIn('light.', hass_state.entity_id)
        
        # Test the mapping
        entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
        
        # Check brightness capability detection
        has_brightness = HassConverter._has_brightness_capability(hass_state)
        
        # Should be LIGHT_DIMMER if it has brightness capability
        if has_brightness:
            self.assertEqual(entity_state_type, EntityStateType.LIGHT_DIMMER)
            self.assertTrue( 'brightness' in dimmer_data.get('attributes', {})
                             or 'brightness_pct' in dimmer_data.get('attributes', {}) )
        else:
            # Fallback to ON_OFF if no brightness detected
            self.assertEqual(entity_state_type, EntityStateType.ON_OFF)
        
        # Verify this is controllable
        is_controllable = HassConverter._is_controllable_domain_and_type(
            hass_state.domain, entity_state_type
        )
        self.assertTrue(is_controllable, "Dimmer lights should be controllable")

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
        """Test that binary sensors are correctly identified with all device classes"""
        
        # Test multiple binary sensor types for comprehensive coverage
        tested_device_classes = set()
        
        for state_data in self.real_ha_states_data:
            if not state_data.get('entity_id', '').startswith('binary_sensor.'):
                continue
                
            # Create HassState from real data
            hass_state = HassConverter.create_hass_state(state_data)
            
            # Verify basic properties
            self.assertEqual(hass_state.domain, HassApi.BINARY_SENSOR_DOMAIN)
            
            # Test the mapping
            entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
            
            # Verify we get a valid EntityStateType
            self.assertIsInstance(entity_state_type, EntityStateType)
            
            # Track device classes we've tested
            device_class = hass_state.device_class
            if device_class:
                tested_device_classes.add(device_class)
            
            # Verify mapping correctness based on device class
            expected_mappings = {
                HassApi.MOTION_DEVICE_CLASS: EntityStateType.MOVEMENT,
                HassApi.CONNECTIVITY_DEVICE_CLASS: EntityStateType.CONNECTIVITY,
                HassApi.BATTERY_DEVICE_CLASS: EntityStateType.HIGH_LOW,
                HassApi.DOOR_DEVICE_CLASS: EntityStateType.OPEN_CLOSE,
                HassApi.GARAGE_DOOR_DEVICE_CLASS: EntityStateType.OPEN_CLOSE,
                HassApi.WINDOW_DEVICE_CLASS: EntityStateType.OPEN_CLOSE,
            }
            
            if device_class in expected_mappings:
                self.assertEqual(
                    entity_state_type, 
                    expected_mappings[device_class],
                    f"Device class {device_class} should map to {expected_mappings[device_class]}"
                )
            else:
                # Default for unknown device classes
                self.assertEqual(
                    entity_state_type, 
                    EntityStateType.ON_OFF,
                    f"Unknown device class {device_class} should default to ON_OFF"
                )
            
            # Binary sensors should not be controllable
            is_controllable = HassConverter._is_controllable_domain_and_type(
                hass_state.domain, entity_state_type
            )
            self.assertFalse(is_controllable, "Binary sensors should not be controllable")
        
        # Ensure we tested at least one binary sensor
        self.assertGreater(len(tested_device_classes), 0, "Should test at least one binary sensor")

    def test_has_brightness_capability(self):
        """Test brightness detection for lights with edge cases"""
        
        # Track what we've tested
        tested_dimmer = False
        tested_relay = False
        
        for state_data in self.real_ha_states_data:
            if not state_data.get('entity_id', '').startswith('light.'):
                continue
                
            hass_state = HassConverter.create_hass_state(state_data)
            has_brightness = HassConverter._has_brightness_capability(hass_state)
            
            attributes = state_data.get('attributes', {})
            
            # Test dimmer lights (with brightness attribute)
            if 'brightness' in attributes:
                tested_dimmer = True
                self.assertTrue(
                    has_brightness, 
                    f"Light {hass_state.entity_id} has brightness attribute but capability not detected"
                )
                
                # Verify the entity state type mapping
                entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
                self.assertEqual(
                    entity_state_type, EntityStateType.LIGHT_DIMMER,
                    f"Light with brightness should be LIGHT_DIMMER, got {entity_state_type}"
                )
            
            # Test lights with brightness_pct
            elif 'brightness_pct' in attributes:
                self.assertTrue(
                    has_brightness,
                    f"Light {hass_state.entity_id} has brightness_pct but capability not detected"
                )
            
            # Test relay lights (color_mode = 'onoff')
            elif attributes.get('color_mode') == 'onoff':
                tested_relay = True
                self.assertFalse(
                    has_brightness,
                    f"Relay light {hass_state.entity_id} should not have brightness capability"
                )
                
                # Verify the entity state type mapping
                entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
                self.assertEqual(
                    entity_state_type, EntityStateType.ON_OFF,
                    f"Relay light should be ON_OFF, got {entity_state_type}"
                )
        
        # Test non-light domains should always return False
        for state_data in self.real_ha_states_data[:5]:
            if state_data.get('entity_id', '').startswith('light.'):
                continue
            
            hass_state = HassConverter.create_hass_state(state_data)
            has_brightness = HassConverter._has_brightness_capability(hass_state)
            self.assertFalse(
                has_brightness,
                f"Non-light domain {hass_state.domain} should not have brightness capability"
            )
        
        # Verify we tested the main scenarios
        if not tested_dimmer:
            self.skipTest("No dimmer lights found in test data")
        if not tested_relay:
            self.skipTest("No relay lights found in test data")

    def test_is_controllable_domain_and_type(self):
        """Test controllability detection with comprehensive coverage"""
        
        # Test all controllable combinations from CONTROL_SERVICE_MAPPING
        for (domain, entity_type) in HassConverter.CONTROL_SERVICE_MAPPING.keys():
            is_controllable = HassConverter._is_controllable_domain_and_type(domain, entity_type)
            self.assertTrue(
                is_controllable,
                f"Mapping exists for {domain}/{entity_type}, should be controllable"
            )
        
        # Test known non-controllable combinations
        non_controllable_cases = [
            (HassApi.SENSOR_DOMAIN, EntityStateType.TEMPERATURE),
            (HassApi.SENSOR_DOMAIN, EntityStateType.HUMIDITY),
            (HassApi.SENSOR_DOMAIN, EntityStateType.BLOB),
            (HassApi.BINARY_SENSOR_DOMAIN, EntityStateType.MOVEMENT),
            (HassApi.BINARY_SENSOR_DOMAIN, EntityStateType.CONNECTIVITY),
            (HassApi.BINARY_SENSOR_DOMAIN, EntityStateType.ON_OFF),
            (HassApi.SUN_DOMAIN, EntityStateType.MULTVALUED),
            (HassApi.WEATHER_DOMAIN, EntityStateType.MULTVALUED),
        ]
        
        for domain, entity_type in non_controllable_cases:
            is_controllable = HassConverter._is_controllable_domain_and_type(domain, entity_type)
            self.assertFalse(is_controllable,
                             f"{domain}/{entity_type} should not be controllable")
        
        # Test that sensor-only domains are never controllable
        for domain in HassConverter.SENSOR_ONLY_DOMAINS:
            # Test with various entity types
            for entity_type in [EntityStateType.ON_OFF, EntityStateType.TEMPERATURE, 
                                EntityStateType.BLOB, EntityStateType.MOVEMENT]:
                is_controllable = HassConverter._is_controllable_domain_and_type(domain, entity_type)
                self.assertFalse(is_controllable,
                                 f"Sensor-only domain {domain} should never be controllable")

    def test_create_hass_state_with_mapping_integration(self):
        """Test the complete integration of the mapping method with real models"""
        
        # Test controllable light
        light_data = None
        for state_data in self.real_ha_states_data:
            if state_data.get('entity_id', '').startswith('light.'):
                light_data = state_data
                break
        
        self.assertIsNotNone(light_data, "Should find a light in test data")
        
        hass_state = HassConverter.create_hass_state(light_data)
        integration_key = IntegrationKey(
            integration_id='hass',
            integration_name=hass_state.entity_id
        )
        
        # Create a mock HassDevice
        hass_device = Mock(spec=HassDevice)
        hass_device.device_id = 'test_device_id'
        
        # Call the mapping method
        entity_state = HassConverter._create_hass_state_with_mapping(
            hass_device=hass_device,
            hass_state=hass_state,
            entity=self.test_entity,
            integration_key=integration_key,
            add_alarm_events=False
        )
        
        # Verify EntityState was created
        self.assertIsNotNone(entity_state)
        self.assertIsInstance(entity_state, EntityState)
        self.assertEqual(entity_state.entity, self.test_entity)
        
        # Check if controller was created for controllable domain
        controller = Controller.objects.filter(entity_state=entity_state).first()
        sensor = Sensor.objects.filter(entity_state=entity_state).first()
        
        # Light should have a controller
        if hass_state.domain in HassConverter.ALL_CONTROLLABLE_DOMAINS:
            self.assertIsNotNone(controller,
                                 f"Controllable domain {hass_state.domain} should have controller")
            
            # Verify integration payload was stored
            self.assertIsNotNone(controller.integration_payload)
            self.assertIn('domain', controller.integration_payload)
            self.assertEqual(controller.integration_payload['domain'], hass_state.domain)
            self.assertIn('has_brightness', controller.integration_payload)
            
            # Verify service mapping exists
            entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
            service_key = (hass_state.domain, entity_state_type)
            if service_key in HassConverter.CONTROL_SERVICE_MAPPING:
                service_info = HassConverter.CONTROL_SERVICE_MAPPING[service_key]
                # The service info should be available for the controller to use
                self.assertIn('on_service', service_info)
                self.assertIn('off_service', service_info)
        else:
            # Non-controllable should only have sensor
            self.assertIsNone(controller,
                              f"Non-controllable domain {hass_state.domain} should not have controller")
            self.assertIsNotNone(sensor,
                                 f"Non-controllable domain {hass_state.domain} should have sensor")
            
            # Verify integration payload was stored on sensor
            self.assertIsNotNone(sensor.integration_payload)
            self.assertIn('domain', sensor.integration_payload)

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

    def test_unmapped_domain_falls_back_to_blob(self):
        """Test that unmapped domains fall back to BLOB EntityStateType"""
        
        # Create a state with an unmapped domain
        unmapped_data = {
            'entity_id': 'unknown_domain.test_entity',
            'state': 'active',
            'attributes': {
                'friendly_name': 'Test Unknown Entity'
            }
        }
        
        hass_state = HassConverter.create_hass_state(unmapped_data)
        
        # Should parse domain correctly
        self.assertEqual(hass_state.domain, 'unknown_domain')
        
        # Should fall back to BLOB type
        entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
        self.assertEqual(entity_state_type, EntityStateType.BLOB,
                         "Unmapped domains should fall back to BLOB")
        
        # Should not be controllable
        is_controllable = HassConverter._is_controllable_domain_and_type(
            hass_state.domain, entity_state_type
        )
        self.assertFalse(is_controllable, "Unmapped domains should not be controllable")
    
    def test_service_payload_creation(self):
        """Test that service payloads are created correctly for different domains"""
        
        test_cases = [
            # (entity_id_prefix, expected_has_brightness, expected_services)
            ('light.test_dimmer', True, ['on_service', 'off_service', 'set_service']),
            ('switch.test_switch', False, ['on_service', 'off_service']),
            ('cover.test_blind', False, ['on_service', 'off_service']),
            ('climate.test_thermostat', False, ['set_service']),
        ]
        
        for entity_id_prefix, should_have_brightness, expected_services in test_cases:
            # Find or create test data
            test_data = None
            for state_data in self.real_ha_states_data:
                if state_data.get('entity_id', '').startswith(entity_id_prefix.split('.')[0] + '.'):
                    test_data = state_data
                    break
            
            if not test_data:
                # Create synthetic test data if not found
                test_data = {
                    'entity_id': entity_id_prefix,
                    'state': 'on',
                    'attributes': {
                        'friendly_name': 'Test Device'
                    }
                }
                if should_have_brightness:
                    test_data['attributes']['brightness'] = 128
            
            hass_state = HassConverter.create_hass_state(test_data)
            entity_state_type = HassConverter._determine_entity_state_type_from_mapping(hass_state)
            
            # Check service mapping exists
            service_key = (hass_state.domain, entity_state_type)
            if service_key in HassConverter.CONTROL_SERVICE_MAPPING:
                service_info = HassConverter.CONTROL_SERVICE_MAPPING[service_key]
                
                # Verify expected services based on actual entity state type
                if entity_state_type == EntityStateType.LIGHT_DIMMER:
                    # Dimmer lights should have set_service
                    self.assertIn('set_service', service_info,
                                  "LIGHT_DIMMER should have set_service")
                    self.assertIn('on_service', service_info)
                    self.assertIn('off_service', service_info)
                elif entity_state_type == EntityStateType.ON_OFF and hass_state.domain == 'light':
                    # Regular lights should not have set_service
                    self.assertNotIn('set_service', service_info,
                                     "ON_OFF light should not have set_service")
                    self.assertIn('on_service', service_info)
                    self.assertIn('off_service', service_info)
                elif entity_state_type == EntityStateType.TEMPERATURE:
                    # Climate controls should have set_service but not on/off
                    self.assertIn('set_service', service_info)
                    self.assertNotIn('on_service', service_info,
                                     "Climate should not have on_service")
                else:
                    # Check that basic on/off services exist for other controllable types
                    if hass_state.domain in ['switch', 'cover', 'fan', 'lock', 'media_player']:
                        self.assertIn('on_service', service_info)
                        self.assertIn('off_service', service_info)
    
    def test_service_mapping_completeness(self):
        """Test that all controllable domains have complete and valid service mappings"""
        
        controllable_domains = HassConverter.ALL_CONTROLLABLE_DOMAINS
        
        for domain in controllable_domains:
            # Each controllable domain should have at least one service mapping
            domain_mappings = [
                (key, value) for key, value in HassConverter.CONTROL_SERVICE_MAPPING.items()
                if key[0] == domain
            ]
            
            self.assertGreater(len(domain_mappings), 0, 
                               f"Domain {domain} should have at least one service mapping")
            
            # Verify each mapping has required fields
            for (mapping_domain, entity_type), service_info in domain_mappings:
                self.assertIsInstance(service_info, dict, 
                                      f"Service info for {mapping_domain}/{entity_type} should be a dict")
                
                # Check required service fields based on domain
                if mapping_domain in HassConverter.ON_OFF_CONTROLLABLE_DOMAINS:
                    self.assertIn('on_service', service_info, 
                                  f"{mapping_domain} should have on_service")
                    self.assertIn('off_service', service_info,
                                  f"{mapping_domain} should have off_service")
                    
                    # Verify service names are valid
                    self.assertIsNotNone(service_info.get('on_service'))
                    self.assertIsNotNone(service_info.get('off_service'))
                
                # Check for parameters field
                self.assertIn('parameters', service_info,
                              f"{mapping_domain}/{entity_type} should have parameters field")
                self.assertIsInstance(service_info['parameters'], dict,
                                      f"Parameters should be a dict for {mapping_domain}/{entity_type}")
                
                # Special checks for specific domains
                if mapping_domain == HassApi.LIGHT_DOMAIN and entity_type == EntityStateType.LIGHT_DIMMER:
                    self.assertIn('set_service', service_info,
                                  "Dimmer lights should have set_service for brightness")
                    self.assertIn('brightness_pct', service_info['parameters'],
                                  "Dimmer lights should have brightness_pct parameter")
                
                if mapping_domain == HassApi.CLIMATE_DOMAIN:
                    self.assertIn('set_service', service_info,
                                  "Climate should have set_service for temperature")
                    self.assertIn('temperature', service_info['parameters'],
                                  "Climate should have temperature parameter")
    
    def test_sensor_creation_for_non_controllable_domains(self):
        """Test that sensors are created correctly for non-controllable domains"""
        
        # Find a binary sensor (non-controllable)
        sensor_data = None
        for state_data in self.real_ha_states_data:
            if state_data.get('entity_id', '').startswith('binary_sensor.'):
                sensor_data = state_data
                break
        
        self.assertIsNotNone(sensor_data, "Should find a binary sensor in test data")
        
        hass_state = HassConverter.create_hass_state(sensor_data)
        integration_key = IntegrationKey(
            integration_id='hass',
            integration_name=hass_state.entity_id
        )
        
        # Create mock HassDevice
        hass_device = Mock(spec=HassDevice)
        hass_device.device_id = 'test_sensor_device'
        
        # Call the mapping method
        entity_state = HassConverter._create_hass_state_with_mapping(
            hass_device=hass_device,
            hass_state=hass_state,
            entity=self.test_entity,
            integration_key=integration_key,
            add_alarm_events=False
        )
        
        # Verify EntityState was created
        self.assertIsNotNone(entity_state)
        self.assertIsInstance(entity_state, EntityState)
        
        # Should have sensor but no controller
        controller = Controller.objects.filter(entity_state=entity_state).first()
        sensor = Sensor.objects.filter(entity_state=entity_state).first()
        
        self.assertIsNone(controller, "Binary sensors should not have controllers")
        self.assertIsNotNone(sensor, "Binary sensors should have sensors")
        
        # Verify sensor has correct integration payload
        self.assertIsNotNone(sensor.integration_payload)
        self.assertEqual(sensor.integration_payload['domain'], HassApi.BINARY_SENSOR_DOMAIN)
        self.assertIn('device_class', sensor.integration_payload)
        
        # Verify sensor properties
        self.assertEqual(sensor.entity_state, entity_state)
        self.assertEqual(sensor.integration_id, integration_key.integration_id)
        self.assertEqual(sensor.integration_name, integration_key.integration_name)
    
    def test_edge_cases_in_entity_id_parsing(self):
        """Test edge cases in entity_id parsing"""
        
        edge_cases = [
            # (entity_id, expected_domain, expected_full_name)
            ('light.living_room', 'light', 'living_room'),
            ('switch.outlet_1', 'switch', 'outlet_1'),
            ('sensor.temperature_sensor', 'sensor', 'temperature_sensor'),
            ('malformed_entity', 'malformed_entity', 'malformed_entity'),  # No dot
            ('', '', ''),  # Empty string
            # These edge cases test regex behavior: r'^([^\.]+)\.(.+)$' 
            ('domain.', 'domain.', 'domain.'),  # Domain with empty name - no match, fallback
            ('.name', '.name', '.name'),  # Empty domain - no match, fallback
        ]
        
        for entity_id, expected_domain, expected_full_name in edge_cases:
            test_data = {
                'entity_id': entity_id,
                'state': 'unknown',
                'attributes': {}
            }
            
            hass_state = HassConverter.create_hass_state(test_data)
            
            self.assertEqual(hass_state.entity_id, entity_id)
            self.assertEqual(hass_state.domain, expected_domain,
                             f"Domain parsing failed for entity_id: {entity_id}")
            self.assertEqual(hass_state.entity_name_sans_prefix, expected_full_name,
                             f"Name parsing failed for entity_id: {entity_id}")
