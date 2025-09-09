import logging
from django.test import TestCase
from unittest.mock import Mock

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityState
from hi.apps.control.models import Controller
from hi.apps.sense.models import Sensor
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassDevice

logging.disable(logging.CRITICAL)


class TestDuplicateControllerFix(TestCase):
    """
    Test for GitHub Issue #153: Duplicate controllers after Home Assistant import
    
    This test specifically targets the bug in _create_hass_sensors_and_controllers
    where Insteon light switches with both 'switch' and 'light' domains
    result in duplicate controllers.
    """

    def setUp(self):
        self.test_entity = Entity.objects.create(
            name="Test Insteon Switch",
            entity_type=EntityType.LIGHT
        )

    def test_insteon_switch_deduplication_switch_first(self):
        """
        Test that Insteon switch with both switch and light domains creates only one controller.
        Test case: switch domain appears first in the list
        """
        # Create mock HassStates for an Insteon switch that has both domains
        switch_api_dict = {
            'entity_id': 'switch.insteon_switch_01',
            'state': 'off',
            'attributes': {
                'friendly_name': 'Kitchen Switch',
                'device_class': None,
            }
        }
        
        light_api_dict = {
            'entity_id': 'light.insteon_switch_01', 
            'state': 'off',
            'attributes': {
                'friendly_name': 'Kitchen Switch',
                'device_class': None,
                'color_mode': 'onoff',  # Non-dimmer light
            }
        }

        switch_state = HassConverter.create_hass_state(switch_api_dict)
        light_state = HassConverter.create_hass_state(light_api_dict)
        
        # Create mock HassDevice
        hass_device = Mock(spec=HassDevice)
        hass_device.device_id = 'insteon_switch_01'
        
        # Set up the states to have the same entity_name_sans_suffix to trigger device grouping
        switch_state.entity_name_sans_suffix = 'insteon_switch_01'
        light_state.entity_name_sans_suffix = 'insteon_switch_01'
        
        # Test the method that has the bug - light first, then switch to trigger the bug
        hass_state_list = [light_state, switch_state]
        
        HassConverter._create_hass_sensors_and_controllers(
            entity=self.test_entity,
            hass_device=hass_device,
            hass_state_list=hass_state_list,
            add_alarm_events=False,
        )
        
        # Verify only one controller and one sensor were created
        controllers = Controller.objects.filter(entity_state__entity=self.test_entity)
        sensors = Sensor.objects.filter(entity_state__entity=self.test_entity)
        entity_states = EntityState.objects.filter(entity=self.test_entity)
        
        self.assertEqual(controllers.count(), 1, 
                         "Should create only one controller for dual-domain Insteon switch")
        self.assertEqual(sensors.count(), 1,
                         "Controller creation should auto-create exactly one sensor")
        self.assertEqual(entity_states.count(), 1,
                         "Should create only one entity state")
        
        # Verify the controller is for the switch domain (preferred)
        controller = controllers.first()
        self.assertIn('switch', controller.integration_name,
                      "Should prefer switch domain over light domain")

    def test_insteon_switch_deduplication_light_first(self):
        """
        Test that Insteon switch with both switch and light domains creates only one controller.
        Test case: light domain appears first in the list
        """
        # Create the same states but in reverse order
        switch_api_dict = {
            'entity_id': 'switch.insteon_switch_02',
            'state': 'off',
            'attributes': {
                'friendly_name': 'Living Room Switch',
                'device_class': None,
            }
        }
        
        light_api_dict = {
            'entity_id': 'light.insteon_switch_02',
            'state': 'off', 
            'attributes': {
                'friendly_name': 'Living Room Switch',
                'device_class': None,
                'color_mode': 'onoff',
            }
        }

        switch_state = HassConverter.create_hass_state(switch_api_dict)
        light_state = HassConverter.create_hass_state(light_api_dict)
        
        # Create mock HassDevice
        hass_device = Mock(spec=HassDevice) 
        hass_device.device_id = 'insteon_switch_02'
        
        # Test with light first, then switch
        hass_state_list = [light_state, switch_state]
        
        HassConverter._create_hass_sensors_and_controllers(
            entity=self.test_entity,
            hass_device=hass_device,
            hass_state_list=hass_state_list,
            add_alarm_events=False,
        )
        
        # Verify only one controller and one sensor were created
        controllers = Controller.objects.filter(entity_state__entity=self.test_entity)
        sensors = Sensor.objects.filter(entity_state__entity=self.test_entity)
        entity_states = EntityState.objects.filter(entity=self.test_entity)
        
        self.assertEqual(controllers.count(), 1,
                         "Should create only one controller regardless of domain order")
        self.assertEqual(sensors.count(), 1,
                         "Controller creation should auto-create exactly one sensor")
        self.assertEqual(entity_states.count(), 1,
                         "Should create only one entity state")

    def test_regular_switch_no_deduplication(self):
        """
        Test that a regular switch (only switch domain) works correctly.
        This ensures our fix doesn't break single-domain devices.
        """
        switch_api_dict = {
            'entity_id': 'switch.regular_switch',
            'state': 'off',
            'attributes': {
                'friendly_name': 'Regular Switch',
                'device_class': None,
            }
        }

        switch_state = HassConverter.create_hass_state(switch_api_dict)
        
        # Create mock HassDevice
        hass_device = Mock(spec=HassDevice)
        hass_device.device_id = 'regular_switch'
        
        # Single domain - no deduplication needed
        hass_state_list = [switch_state]
        
        HassConverter._create_hass_sensors_and_controllers(
            entity=self.test_entity,
            hass_device=hass_device, 
            hass_state_list=hass_state_list,
            add_alarm_events=False,
        )
        
        # Verify one controller and one sensor were created
        controllers = Controller.objects.filter(entity_state__entity=self.test_entity)
        sensors = Sensor.objects.filter(entity_state__entity=self.test_entity)
        
        self.assertEqual(controllers.count(), 1,
                         "Regular switch should create one controller")
        self.assertEqual(sensors.count(), 1,
                         "Regular switch should create one sensor")

    def test_dimmer_light_no_deduplication(self):
        """
        Test that a dimmer light (only light domain) works correctly.
        This ensures our fix doesn't break single-domain devices.
        """
        light_api_dict = {
            'entity_id': 'light.dimmer_switch',
            'state': 'off',
            'attributes': {
                'friendly_name': 'Dimmer Switch',
                'device_class': None,
                'brightness': 128,  # Has brightness - should be LIGHT_DIMMER
                'color_mode': 'brightness',
            }
        }

        light_state = HassConverter.create_hass_state(light_api_dict)
        
        # Create mock HassDevice
        hass_device = Mock(spec=HassDevice)
        hass_device.device_id = 'dimmer_switch'
        
        # Single domain - no deduplication needed
        hass_state_list = [light_state]
        
        HassConverter._create_hass_sensors_and_controllers(
            entity=self.test_entity,
            hass_device=hass_device,
            hass_state_list=hass_state_list,
            add_alarm_events=False,
        )
        
        # Verify one controller and one sensor were created
        controllers = Controller.objects.filter(entity_state__entity=self.test_entity)
        sensors = Sensor.objects.filter(entity_state__entity=self.test_entity)
        
        self.assertEqual(controllers.count(), 1,
                         "Dimmer light should create one controller")
        self.assertEqual(sensors.count(), 1,
                         "Dimmer light should create one sensor")

    def test_multiple_domains_beyond_switch_light(self):
        """
        Test that devices with multiple domains beyond switch/light work correctly.
        This ensures our fix is specific to switch/light deduplication.
        """
        # Create states for a complex device with multiple domains
        sensor_api_dict = {
            'entity_id': 'sensor.complex_device_temp',
            'state': '72.5',
            'attributes': {
                'friendly_name': 'Complex Device Temperature',
                'device_class': 'temperature',
                'unit_of_measurement': '°F',
            }
        }
        
        switch_api_dict = {
            'entity_id': 'switch.complex_device',
            'state': 'off',
            'attributes': {
                'friendly_name': 'Complex Device Switch',
                'device_class': None,
            }
        }

        sensor_state = HassConverter.create_hass_state(sensor_api_dict)
        switch_state = HassConverter.create_hass_state(switch_api_dict)
        
        # Create mock HassDevice
        hass_device = Mock(spec=HassDevice)
        hass_device.device_id = 'complex_device'
        
        # Multiple domains but not switch/light combination
        hass_state_list = [sensor_state, switch_state]
        
        HassConverter._create_hass_sensors_and_controllers(
            entity=self.test_entity,
            hass_device=hass_device,
            hass_state_list=hass_state_list,
            add_alarm_events=False,
        )
        
        # Should create separate sensors/controllers for different domains
        controllers = Controller.objects.filter(entity_state__entity=self.test_entity)
        sensors = Sensor.objects.filter(entity_state__entity=self.test_entity)
        entity_states = EntityState.objects.filter(entity=self.test_entity)
        
        # Switch is controllable, sensor is not
        self.assertEqual(controllers.count(), 1,
                         "Should create one controller for the switch")
        self.assertEqual(sensors.count(), 2,
                         "Should create two sensors: one for temperature sensor, one auto-created for switch controller")
        self.assertEqual(entity_states.count(), 2,
                         "Should create two entity states for different domains")
