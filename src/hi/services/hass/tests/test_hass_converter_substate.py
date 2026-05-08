import logging
from unittest.mock import patch

from django.test import TestCase

from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassState

logging.disable(logging.CRITICAL)


def _make_light_hass_state(api_dict, entity_id='light.x'):
    return HassState(
        api_dict=api_dict,
        entity_id=entity_id,
        domain='light',
        entity_name_sans_prefix=entity_id.split('.', 1)[1],
        entity_name_sans_suffix=entity_id.split('.', 1)[1],
    )


class TestSubstateInboundDecomposition(TestCase):
    """Verify ``hass_state_to_sensor_value_map`` decomposes one
    HA light state into the right set of HI integration_keys."""

    def test_dimmer_without_color_modes_returns_only_brightness(self):
        hass_state = _make_light_hass_state({
            'entity_id': 'light.bedroom',
            'state': 'on',
            'attributes': {
                'brightness': 128,
                'supported_color_modes': ['brightness'],
            },
        }, entity_id='light.bedroom')
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        keys = [k.integration_name for k in value_map.keys()]
        self.assertEqual(keys, ['light.bedroom'])
        self.assertEqual(list(value_map.values())[0], '50')  # 128/255 ≈ 50%

    def test_color_bulb_with_hs_returns_brightness_plus_hue_saturation(self):
        hass_state = _make_light_hass_state({
            'entity_id': 'light.c',
            'state': 'on',
            'attributes': {
                'brightness': 255,
                'hs_color': [180, 75],
                'supported_color_modes': ['hs'],
            },
        }, entity_id='light.c')
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        keys = sorted(k.integration_name for k in value_map.keys())
        self.assertEqual(keys, ['light.c', 'light.c~hue', 'light.c~saturation'])

    def test_color_bulb_with_color_temp_returns_brightness_plus_kelvin(self):
        hass_state = _make_light_hass_state({
            'entity_id': 'light.c',
            'state': 'on',
            'attributes': {
                'brightness': 200,
                'color_temp_kelvin': 4500,
                'supported_color_modes': ['color_temp'],
            },
        }, entity_id='light.c')
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        keys = sorted(k.integration_name for k in value_map.keys())
        self.assertEqual(keys, ['light.c', 'light.c~color_temp'])

    def test_color_bulb_with_both_modes_returns_all_substates(self):
        hass_state = _make_light_hass_state({
            'entity_id': 'light.c',
            'state': 'on',
            'attributes': {
                'brightness': 200,
                'hs_color': [240, 60],
                'color_temp_kelvin': 4500,
                'supported_color_modes': ['hs', 'color_temp'],
            },
        }, entity_id='light.c')
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        keys = sorted(k.integration_name for k in value_map.keys())
        self.assertEqual(
            keys,
            ['light.c', 'light.c~color_temp', 'light.c~hue', 'light.c~saturation'],
        )

    def test_off_state_color_bulb_returns_brightness_zero_and_skips_color(self):
        # HA omits color attributes when the light is off; substates
        # whose attribute is absent return None and are skipped from
        # the value map.
        hass_state = _make_light_hass_state({
            'entity_id': 'light.c',
            'state': 'off',
            'attributes': {
                'supported_color_modes': ['hs', 'color_temp'],
            },
        }, entity_id='light.c')
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        keys = [k.integration_name for k in value_map.keys()]
        self.assertEqual(keys, ['light.c'])
        self.assertEqual(list(value_map.values())[0], '0')


class TestSubstateOutboundDispatch(TestCase):
    """Verify ``hi_value_to_hass_service_call`` routes substate
    payloads to the right HA service call."""

    def test_color_temp_substate_composes_color_temp_kelvin_call(self):
        service_call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='light.c~color_temp',
            hi_control_value='4500',
            domain_payload={
                'domain': 'light',
                'is_controllable': True,
                'substate': 'color_temp',
                'parent_entity_id': 'light.c',
            },
        )
        self.assertEqual(service_call.domain, 'light')
        self.assertEqual(service_call.service, 'turn_on')
        self.assertEqual(service_call.hass_entity_id, 'light.c')
        self.assertEqual(service_call.service_data, {'color_temp_kelvin': 4500})

    def test_hue_with_cached_saturation_uses_partner_value(self):
        with patch.object(
            HassConverter, 'get_latest_state_values',
            return_value={
                # The integration_key in the result dict is the same
                # IntegrationKey object the caller passed in; using
                # any-value match here is simpler than reconstructing.
            },
        ) as mock_lookup:
            # Build a real return value keyed by whatever key
            # HassConverter constructs internally.
            captured = {}

            def side_effect(integration_keys):
                captured['keys'] = integration_keys
                return {integration_keys[0]: '60'}
            mock_lookup.side_effect = side_effect

            service_call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='light.c~hue',
                hi_control_value='180',
                domain_payload={
                    'domain': 'light',
                    'is_controllable': True,
                    'substate': 'hue',
                    'parent_entity_id': 'light.c',
                },
            )

        partner_key = captured['keys'][0]
        self.assertEqual(partner_key.integration_name, 'light.c~saturation')
        self.assertEqual(service_call.service_data, {'hs_color': [180.0, 60.0]})

    def test_saturation_with_cached_hue_uses_partner_value(self):
        with patch.object(HassConverter, 'get_latest_state_values') as mock_lookup:
            def side_effect(integration_keys):
                return {integration_keys[0]: '210'}
            mock_lookup.side_effect = side_effect

            service_call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='light.c~saturation',
                hi_control_value='75',
                domain_payload={
                    'domain': 'light',
                    'is_controllable': True,
                    'substate': 'saturation',
                    'parent_entity_id': 'light.c',
                },
            )

        self.assertEqual(service_call.service_data, {'hs_color': [210.0, 75.0]})

    def test_hue_without_cached_partner_defaults_saturation_to_full(self):
        with patch.object(
            HassConverter, 'get_latest_state_values',
            return_value={},
        ) as mock_lookup:
            mock_lookup.side_effect = lambda integration_keys: {integration_keys[0]: None}
            service_call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='light.c~hue',
                hi_control_value='90',
                domain_payload={
                    'domain': 'light',
                    'is_controllable': True,
                    'substate': 'hue',
                    'parent_entity_id': 'light.c',
                },
            )
        self.assertEqual(service_call.service_data, {'hs_color': [90.0, 100.0]})

    def test_saturation_without_cached_partner_defaults_hue_to_zero(self):
        with patch.object(HassConverter, 'get_latest_state_values') as mock_lookup:
            mock_lookup.side_effect = lambda integration_keys: {integration_keys[0]: None}
            service_call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='light.c~saturation',
                hi_control_value='80',
                domain_payload={
                    'domain': 'light',
                    'is_controllable': True,
                    'substate': 'saturation',
                    'parent_entity_id': 'light.c',
                },
            )
        self.assertEqual(service_call.service_data, {'hs_color': [0.0, 80.0]})

    def test_invalid_color_temp_value_raises(self):
        with self.assertRaises(ValueError):
            HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='light.c~color_temp',
                hi_control_value='not-a-number',
                domain_payload={
                    'domain': 'light',
                    'is_controllable': True,
                    'substate': 'color_temp',
                    'parent_entity_id': 'light.c',
                },
            )

    def test_unknown_substate_kind_raises(self):
        with self.assertRaises(ValueError):
            HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='light.c~unknown',
                hi_control_value='42',
                domain_payload={
                    'domain': 'light',
                    'is_controllable': True,
                    'substate': 'mystery',
                    'parent_entity_id': 'light.c',
                },
            )


class TestBoundaryHelpers(TestCase):
    """Verify the namespace-marker helpers used by the bridge methods."""

    def test_to_ha_numeric_parameter_value_parses_string(self):
        self.assertEqual(HassConverter.to_ha_numeric_parameter_value('50'), 50.0)
        self.assertEqual(HassConverter.to_ha_numeric_parameter_value('0.7'), 0.7)

    def test_to_ha_numeric_parameter_value_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            HassConverter.to_ha_numeric_parameter_value('abc')

    def test_to_ha_on_off_intent_canonicalizes_on_variants(self):
        for value in ['on', 'ON', 'true', 'TRUE', '1']:
            self.assertEqual(HassConverter.to_ha_on_off_intent(value), 'on')

    def test_to_ha_on_off_intent_canonicalizes_off_variants(self):
        for value in ['off', 'OFF', 'false', 'FALSE', '0']:
            self.assertEqual(HassConverter.to_ha_on_off_intent(value), 'off')

    def test_to_ha_on_off_intent_passes_through_open_close(self):
        self.assertEqual(HassConverter.to_ha_on_off_intent('open'), 'open')
        self.assertEqual(HassConverter.to_ha_on_off_intent('close'), 'close')

    def test_to_ha_on_off_intent_rejects_unknown(self):
        with self.assertRaises(ValueError):
            HassConverter.to_ha_on_off_intent('maybe')
