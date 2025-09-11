import logging
from django.test import TestCase

from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassState

logging.disable(logging.CRITICAL)


class TestDimmerStateConversion(TestCase):
    """Test the dimmer state conversion logic in hass_state_to_sensor_value_str"""

    def test_dimmer_light_off_returns_zero(self):
        """Test that dimmer light in 'off' state returns '0'"""
        api_dict = {
            'entity_id': 'light.dimmer_switch',
            'state': 'off',
            'attributes': {
                'brightness': 100,
                'supported_features': 127,
                'friendly_name': 'Dimmer Switch'
            }
        }
        hass_state = HassState(
            api_dict=api_dict,
            entity_id='light.dimmer_switch',
            domain='light',
            entity_name_sans_prefix='dimmer_switch',
            entity_name_sans_suffix='dimmer_switch'
        )
        
        result = HassConverter.hass_state_to_sensor_value_str(hass_state)
        self.assertEqual(result, "0")

    def test_dimmer_light_on_with_brightness_converts_correctly(self):
        """Test that dimmer light converts HA brightness (1-255) to percentage (0-100)"""
        test_cases = [
            (255, "100"),  # Full brightness
            (128, "50"),   # Half brightness (rounded)
            (127, "50"),   # Half brightness (rounded down) 
            (25, "10"),    # Low brightness (rounded)
            (1, "0"),      # Minimum HA brightness maps to 0%
        ]
        
        for ha_brightness, expected_pct in test_cases:
            with self.subTest(brightness=ha_brightness):
                api_dict = {
                    'entity_id': 'light.dimmer_switch',
                    'state': 'on',
                    'attributes': {
                        'brightness': ha_brightness,
                        'supported_features': 127,
                        'friendly_name': 'Dimmer Switch'
                    }
                }
                hass_state = HassState(
                    api_dict=api_dict,
                    entity_id='light.dimmer_switch',
                    domain='light',
                    entity_name_sans_prefix='dimmer_switch',
                    entity_name_sans_suffix='dimmer_switch'
                )
                
                result = HassConverter.hass_state_to_sensor_value_str(hass_state)
                self.assertEqual(result, expected_pct)

    def test_dimmer_light_on_without_brightness_defaults_to_full(self):
        """Test that dimmer light 'on' with brightness attribute but None value defaults to 100"""
        api_dict = {
            'entity_id': 'light.dimmer_switch',
            'state': 'on',
            'attributes': {
                'brightness': None,  # Brightness attribute present but None
                'supported_features': 127,
                'friendly_name': 'Dimmer Switch'
            }
        }
        hass_state = HassState(
            api_dict=api_dict,
            entity_id='light.dimmer_switch',
            domain='light',
            entity_name_sans_prefix='dimmer_switch',
            entity_name_sans_suffix='dimmer_switch'
        )
        
        result = HassConverter.hass_state_to_sensor_value_str(hass_state)
        self.assertEqual(result, "100")

    def test_regular_light_on_off_returns_entity_state_values(self):
        """Test that regular (non-dimmer) lights return EntityStateValue strings"""
        # Test ON state (no brightness attribute = not a dimmer)
        api_dict_on = {
            'entity_id': 'light.regular_switch',
            'state': 'on',
            'attributes': {
                'supported_features': 1,  # No brightness-related attributes
                'friendly_name': 'Regular Switch'
            }
        }
        hass_state_on = HassState(
            api_dict=api_dict_on,
            entity_id='light.regular_switch',
            domain='light',
            entity_name_sans_prefix='regular_switch',
            entity_name_sans_suffix='regular_switch'
        )
        
        result_on = HassConverter.hass_state_to_sensor_value_str(hass_state_on)
        self.assertEqual(result_on, "on")  # EntityStateValue.ON (lowercase string representation)
        
        # Test OFF state (no brightness attribute = not a dimmer)
        api_dict_off = {
            'entity_id': 'light.regular_switch',
            'state': 'off',
            'attributes': {
                'supported_features': 1,  # No brightness-related attributes
                'friendly_name': 'Regular Switch'
            }
        }
        hass_state_off = HassState(
            api_dict=api_dict_off,
            entity_id='light.regular_switch',
            domain='light',
            entity_name_sans_prefix='regular_switch',
            entity_name_sans_suffix='regular_switch'
        )
        
        result_off = HassConverter.hass_state_to_sensor_value_str(hass_state_off)
        self.assertEqual(result_off, "off")  # EntityStateValue.OFF (lowercase string representation)

    def test_invalid_brightness_defaults_to_full(self):
        """Test that invalid brightness values default to full brightness"""
        api_dict = {
            'entity_id': 'light.dimmer_switch',
            'state': 'on',
            'attributes': {
                'brightness': 'invalid',
                'supported_features': 127,
                'friendly_name': 'Dimmer Switch'
            }
        }
        hass_state = HassState(
            api_dict=api_dict,
            entity_id='light.dimmer_switch',
            domain='light',
            entity_name_sans_prefix='dimmer_switch',
            entity_name_sans_suffix='dimmer_switch'
        )
        
        result = HassConverter.hass_state_to_sensor_value_str(hass_state)
        self.assertEqual(result, "100")
        
