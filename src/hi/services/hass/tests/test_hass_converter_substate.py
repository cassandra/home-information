import logging
from unittest.mock import patch

from django.test import TestCase

from hi.apps.control.models import Controller
from hi.apps.entity.enums import EntityStateValue
from hi.apps.sense.models import Sensor
from hi.integrations.integration_converter_helper import IntegrationConverterHelper
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassDevice, HassState

logging.disable(logging.CRITICAL)


def _build_color_light_device(
        device_id='color_bulb', supported_color_modes=None,
        state='on', brightness=255,
):
    supported_color_modes = supported_color_modes or ['hs', 'color_temp']
    api_dict = {
        'entity_id': f'light.{device_id}',
        'state': state,
        'attributes': {
            'friendly_name': device_id.replace('_', ' ').title(),
            'supported_color_modes': supported_color_modes,
            'color_mode': supported_color_modes[0],
            'brightness': brightness,
        },
        'last_changed': '2026-01-01T00:00:00+00:00',
        'last_reported': '2026-01-01T00:00:00+00:00',
        'last_updated': '2026-01-01T00:00:00+00:00',
        'context': {'id': 'ctx', 'parent_id': None, 'user_id': None},
    }
    hass_state = HassConverter.create_hass_state(api_dict)
    device = HassDevice(device_id=device_id)
    device.add_state(hass_state)
    return device


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
                IntegrationConverterHelper, 'get_latest_state_values',
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
        with patch.object(IntegrationConverterHelper, "get_latest_state_values") as mock_lookup:
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
                IntegrationConverterHelper, 'get_latest_state_values',
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
        with patch.object(IntegrationConverterHelper, "get_latest_state_values") as mock_lookup:
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


class TestSubstateControllerCreationIdempotency(TestCase):
    """Verify ``_create_substate_controllers`` is idempotent and
    that ``update_models_for_hass_device`` symmetrically adds
    newly-implied substate controllers without duplicating
    existing ones."""

    def _count_substate_controllers(self, entity):
        return Controller.objects.filter(
            entity_state__entity=entity,
        ).exclude(
            integration_name=f'light.{entity.integration_name}',
        ).filter(
            integration_name__contains='~',
        ).count()

    def test_initial_create_produces_three_substate_controllers(self):
        device = _build_color_light_device(
            device_id='c1',
            supported_color_modes=['hs', 'color_temp'],
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )
        substate_controllers = Controller.objects.filter(
            entity_state__entity=entity,
            integration_name__contains='~',
        )
        suffixes = sorted(
            c.integration_name.split('~', 1)[1] for c in substate_controllers
        )
        self.assertEqual(suffixes, ['color_temp', 'hue', 'saturation'])

    def test_resync_does_not_duplicate_existing_substate_controllers(self):
        device = _build_color_light_device(
            device_id='c2',
            supported_color_modes=['hs', 'color_temp'],
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device, add_alarm_events=False,
        )
        before = Controller.objects.filter(
            entity_state__entity=entity,
            integration_name__contains='~',
        ).count()
        self.assertEqual(before, 3)

        # Re-sync the same device shape — should be a no-op for
        # substate controller creation.
        HassConverter.update_models_for_hass_device(
            entity=entity, hass_device=device,
        )
        after = Controller.objects.filter(
            entity_state__entity=entity,
            integration_name__contains='~',
        ).count()
        self.assertEqual(after, 3)

    def test_resync_creates_newly_implied_substate_controllers(self):
        # Initial import: brightness-only bulb (no color substates).
        device = _build_color_light_device(
            device_id='c3',
            supported_color_modes=['brightness'],
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device, add_alarm_events=False,
        )
        self.assertEqual(
            Controller.objects.filter(
                entity_state__entity=entity,
                integration_name__contains='~',
            ).count(),
            0,
        )

        # Bulb gains color modes (firmware update, etc.); re-sync.
        upgraded_device = _build_color_light_device(
            device_id='c3',
            supported_color_modes=['hs', 'color_temp'],
        )
        HassConverter.update_models_for_hass_device(
            entity=entity, hass_device=upgraded_device,
        )
        suffixes = sorted(
            c.integration_name.split('~', 1)[1]
            for c in Controller.objects.filter(
                entity_state__entity=entity,
                integration_name__contains='~',
            )
        )
        self.assertEqual(suffixes, ['color_temp', 'hue', 'saturation'])


class TestColorModeSubstate(TestCase):
    """Behavior specific to the COLOR_MODE substate (sensor-only,
    discrete-valued, mapped from HA's ``color_mode`` attribute)."""

    def test_color_mode_value_translation(self):
        """HA's color_mode strings translate to HI EntityStateValue
        members; null and 'unknown' both map to UNKNOWN."""
        cases = [
            ('hs', EntityStateValue.COLOR_MODE_HS),
            ('color_temp', EntityStateValue.COLOR_MODE_COLOR_TEMP),
            ('rgb', EntityStateValue.COLOR_MODE_RGB),
            ('onoff', EntityStateValue.COLOR_MODE_ONOFF),
            ('brightness', EntityStateValue.COLOR_MODE_BRIGHTNESS),
            ('white', EntityStateValue.COLOR_MODE_WHITE),
            (None, EntityStateValue.COLOR_MODE_UNKNOWN),
            ('unknown', EntityStateValue.COLOR_MODE_UNKNOWN),
        ]
        for ha_value, expected_hi_value in cases:
            with self.subTest(ha_value=ha_value):
                hass_state = _build_color_light_device(
                    device_id='cm',
                    supported_color_modes=['hs', 'color_temp'],
                ).hass_state_list[0]
                hass_state.api_dict['attributes']['color_mode'] = ha_value
                value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
                color_mode_key = next(
                    k for k in value_map if k.integration_name.endswith('~color_mode')
                )
                self.assertEqual(value_map[color_mode_key], str(expected_hi_value))

    def test_color_mode_attribute_absent_skipped_from_value_map(self):
        """When HA omits the ``color_mode`` attribute key entirely,
        the substate is skipped from the value map (last-known
        retained), consistent with hue/saturation behavior."""
        hass_state = _build_color_light_device(
            device_id='cm2',
            supported_color_modes=['hs', 'color_temp'],
        ).hass_state_list[0]
        # Strip color_mode; the fixture builder sets it by default.
        del hass_state.api_dict['attributes']['color_mode']
        value_map = HassConverter.hass_state_to_sensor_value_map(hass_state)
        color_mode_keys = [
            k for k in value_map if k.integration_name.endswith('~color_mode')
        ]
        self.assertEqual(color_mode_keys, [])

    def test_color_mode_substate_creates_sensor_not_controller(self):
        """COLOR_MODE is sensor-only — operator can't directly set
        the mode (HA derives it from whichever attribute was
        most-recently written)."""
        device = _build_color_light_device(
            device_id='cm3',
            supported_color_modes=['hs', 'color_temp'],
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device, add_alarm_events=False,
        )
        # COLOR_MODE substate should exist as a Sensor.
        self.assertTrue(
            Sensor.objects.filter(
                entity_state__entity=entity,
                integration_name__endswith='~color_mode',
            ).exists()
        )
        # COLOR_MODE substate should NOT exist as a Controller.
        self.assertFalse(
            Controller.objects.filter(
                entity_state__entity=entity,
                integration_name__endswith='~color_mode',
            ).exists()
        )

    def test_resync_does_not_duplicate_color_mode_sensor(self):
        device = _build_color_light_device(
            device_id='cm4',
            supported_color_modes=['hs', 'color_temp'],
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device, add_alarm_events=False,
        )
        before = Sensor.objects.filter(
            entity_state__entity=entity,
            integration_name__endswith='~color_mode',
        ).count()
        self.assertEqual(before, 1)

        HassConverter.update_models_for_hass_device(
            entity=entity, hass_device=device,
        )
        after = Sensor.objects.filter(
            entity_state__entity=entity,
            integration_name__endswith='~color_mode',
        ).count()
        self.assertEqual(after, 1)
