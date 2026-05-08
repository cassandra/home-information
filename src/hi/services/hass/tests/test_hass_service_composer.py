import logging

from django.test import TestCase

from hi.services.hass.hass_models import HassServiceCall
from hi.services.hass.hass_service_composer import HassServiceComposer

logging.disable(logging.CRITICAL)


class TestForOnOffBestEffort(TestCase):

    def test_on_intent_maps_to_turn_on(self):
        result = HassServiceComposer.for_on_off_best_effort(
            domain='switch', hass_substate_id='switch.x', intent='on',
        )
        self.assertEqual(result, HassServiceCall(
            domain='switch', service='turn_on', hass_entity_id='switch.x',
        ))

    def test_off_intent_maps_to_turn_off(self):
        result = HassServiceComposer.for_on_off_best_effort(
            domain='light', hass_substate_id='light.x', intent='off',
        )
        self.assertEqual(result.service, 'turn_off')

    def test_open_on_cover_maps_to_open_cover(self):
        result = HassServiceComposer.for_on_off_best_effort(
            domain='cover', hass_substate_id='cover.x', intent='open',
        )
        self.assertEqual(result.service, 'open_cover')

    def test_close_on_cover_maps_to_close_cover(self):
        result = HassServiceComposer.for_on_off_best_effort(
            domain='cover', hass_substate_id='cover.x', intent='close',
        )
        self.assertEqual(result.service, 'close_cover')

    def test_open_on_lock_maps_to_unlock(self):
        result = HassServiceComposer.for_on_off_best_effort(
            domain='lock', hass_substate_id='lock.x', intent='open',
        )
        self.assertEqual(result.service, 'unlock')

    def test_close_on_lock_maps_to_lock(self):
        result = HassServiceComposer.for_on_off_best_effort(
            domain='lock', hass_substate_id='lock.x', intent='close',
        )
        self.assertEqual(result.service, 'lock')

    def test_open_on_other_domain_falls_back_to_turn_on(self):
        result = HassServiceComposer.for_on_off_best_effort(
            domain='light', hass_substate_id='light.x', intent='open',
        )
        self.assertEqual(result.service, 'turn_on')

    def test_close_on_other_domain_falls_back_to_turn_off(self):
        result = HassServiceComposer.for_on_off_best_effort(
            domain='light', hass_substate_id='light.x', intent='close',
        )
        self.assertEqual(result.service, 'turn_off')

    def test_unknown_intent_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_on_off_best_effort(
                domain='light', hass_substate_id='light.x', intent='maybe',
            )


class TestForNumericBestEffort(TestCase):

    def test_light_zero_brightness_turns_off(self):
        result = HassServiceComposer.for_numeric_best_effort(
            domain='light', hass_substate_id='light.x', numeric_value=0,
        )
        self.assertEqual(result.service, 'turn_off')
        self.assertIsNone(result.service_data)

    def test_light_partial_brightness_turns_on_with_pct(self):
        result = HassServiceComposer.for_numeric_best_effort(
            domain='light', hass_substate_id='light.x', numeric_value=50,
        )
        self.assertEqual(result.service, 'turn_on')
        self.assertEqual(result.service_data, {'brightness_pct': 50})

    def test_light_full_brightness_turns_on_with_pct(self):
        result = HassServiceComposer.for_numeric_best_effort(
            domain='light', hass_substate_id='light.x', numeric_value=100,
        )
        self.assertEqual(result.service_data, {'brightness_pct': 100})

    def test_light_invalid_brightness_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_numeric_best_effort(
                domain='light', hass_substate_id='light.x', numeric_value=150,
            )

    def test_climate_temperature_call(self):
        result = HassServiceComposer.for_numeric_best_effort(
            domain='climate', hass_substate_id='climate.x', numeric_value=72.5,
        )
        self.assertEqual(result.service, 'set_temperature')
        self.assertEqual(result.service_data, {'temperature': 72.5})

    def test_cover_valid_position(self):
        result = HassServiceComposer.for_numeric_best_effort(
            domain='cover', hass_substate_id='cover.x', numeric_value=50,
        )
        self.assertEqual(result.service, 'set_cover_position')
        self.assertEqual(result.service_data, {'position': 50})

    def test_cover_invalid_position_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_numeric_best_effort(
                domain='cover', hass_substate_id='cover.x', numeric_value=120,
            )

    def test_media_player_valid_volume(self):
        result = HassServiceComposer.for_numeric_best_effort(
            domain='media_player', hass_substate_id='mp.x', numeric_value=0.5,
        )
        self.assertEqual(result.service, 'volume_set')
        self.assertEqual(result.service_data, {'volume_level': 0.5})

    def test_media_player_invalid_volume_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_numeric_best_effort(
                domain='media_player', hass_substate_id='mp.x', numeric_value=1.5,
            )

    def test_unknown_domain_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_numeric_best_effort(
                domain='switch', hass_substate_id='switch.x', numeric_value=42,
            )


class TestForBrightness(TestCase):

    def test_zero_uses_off_service(self):
        result = HassServiceComposer.for_brightness(
            domain='light', hass_substate_id='light.x', brightness=0,
            domain_payload={'on_service': 'turn_on', 'off_service': 'turn_off'},
        )
        self.assertEqual(result.service, 'turn_off')
        self.assertIsNone(result.service_data)

    def test_partial_uses_on_service_with_pct(self):
        result = HassServiceComposer.for_brightness(
            domain='light', hass_substate_id='light.x', brightness=75,
            domain_payload={'on_service': 'turn_on', 'off_service': 'turn_off'},
        )
        self.assertEqual(result.service, 'turn_on')
        self.assertEqual(result.service_data, {'brightness_pct': 75})

    def test_missing_on_service_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_brightness(
                domain='light', hass_substate_id='light.x', brightness=50,
                domain_payload={'off_service': 'turn_off'},
            )

    def test_invalid_range_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_brightness(
                domain='light', hass_substate_id='light.x', brightness=150,
                domain_payload={'on_service': 'turn_on'},
            )


class TestForTemperatureVolumePosition(TestCase):

    def test_temperature_uses_set_service(self):
        result = HassServiceComposer.for_temperature(
            domain='climate', hass_substate_id='climate.x', temperature=68.0,
            domain_payload={'set_service': 'set_temperature'},
        )
        self.assertEqual(result.service, 'set_temperature')
        self.assertEqual(result.service_data, {'temperature': 68.0})

    def test_temperature_missing_set_service_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_temperature(
                domain='climate', hass_substate_id='climate.x', temperature=68.0,
                domain_payload={},
            )

    def test_volume_default_service_is_volume_set(self):
        result = HassServiceComposer.for_volume(
            domain='media_player', hass_substate_id='mp.x', volume=0.6,
            domain_payload={},
        )
        self.assertEqual(result.service, 'volume_set')
        self.assertEqual(result.service_data, {'volume_level': 0.6})

    def test_volume_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_volume(
                domain='media_player', hass_substate_id='mp.x', volume=2.0,
                domain_payload={},
            )

    def test_position_default_service_is_set_cover_position(self):
        result = HassServiceComposer.for_position(
            domain='cover', hass_substate_id='cover.x', position=42,
            domain_payload={},
        )
        self.assertEqual(result.service, 'set_cover_position')
        self.assertEqual(result.service_data, {'position': 42})

    def test_position_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_position(
                domain='cover', hass_substate_id='cover.x', position=200,
                domain_payload={},
            )


class TestForNumericParameter(TestCase):

    def test_supports_brightness_flag_routes_to_brightness(self):
        result = HassServiceComposer.for_numeric_parameter(
            domain='light', hass_substate_id='light.x', numeric_value=50,
            domain_payload={
                'supports_brightness': True,
                'on_service': 'turn_on', 'off_service': 'turn_off',
            },
        )
        self.assertEqual(result.service_data, {'brightness_pct': 50})

    def test_temperature_parameter_routes_to_temperature(self):
        result = HassServiceComposer.for_numeric_parameter(
            domain='climate', hass_substate_id='climate.x', numeric_value=70,
            domain_payload={
                'parameters': {'temperature': True},
                'set_service': 'set_temperature',
            },
        )
        self.assertEqual(result.service, 'set_temperature')
        self.assertEqual(result.service_data, {'temperature': 70})

    def test_volume_level_parameter_routes_to_volume(self):
        result = HassServiceComposer.for_numeric_parameter(
            domain='media_player', hass_substate_id='mp.x', numeric_value=0.4,
            domain_payload={'parameters': {'volume_level': True}},
        )
        self.assertEqual(result.service_data, {'volume_level': 0.4})

    def test_position_parameter_routes_to_position(self):
        result = HassServiceComposer.for_numeric_parameter(
            domain='cover', hass_substate_id='cover.x', numeric_value=30,
            domain_payload={'parameters': {'position': True}},
        )
        self.assertEqual(result.service_data, {'position': 30})

    def test_set_service_only_falls_back_to_generic_call(self):
        result = HassServiceComposer.for_numeric_parameter(
            domain='climate', hass_substate_id='climate.x', numeric_value=21,
            domain_payload={'set_service': 'set_value'},
        )
        self.assertEqual(result.service, 'set_value')
        # Generic fallback uses domain.rstrip('s') as key
        self.assertEqual(result.service_data, {'climate': 21})

    def test_empty_payload_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_numeric_parameter(
                domain='light', hass_substate_id='light.x', numeric_value=50,
                domain_payload={},
            )


class TestForPayloadIntent(TestCase):

    def test_intent_with_matching_service_returns_call(self):
        result = HassServiceComposer.for_payload_intent(
            domain='light', hass_substate_id='light.x', intent='on',
            domain_payload={'on_service': 'turn_on'},
        )
        self.assertEqual(result, HassServiceCall(
            domain='light', service='turn_on', hass_entity_id='light.x',
        ))

    def test_intent_without_matching_service_returns_none(self):
        result = HassServiceComposer.for_payload_intent(
            domain='light', hass_substate_id='light.x', intent='on',
            domain_payload={'off_service': 'turn_off'},  # only off
        )
        self.assertIsNone(result)

    def test_unknown_intent_raises(self):
        with self.assertRaises(ValueError):
            HassServiceComposer.for_payload_intent(
                domain='light', hass_substate_id='light.x', intent='maybe',
                domain_payload={'on_service': 'turn_on'},
            )


class TestForColor(TestCase):

    def test_for_color_temp_composes_kelvin_call(self):
        result = HassServiceComposer.for_color_temp(
            domain='light', parent_entity_id='light.x', kelvin=4000,
        )
        self.assertEqual(result, HassServiceCall(
            domain='light',
            service='turn_on',
            hass_entity_id='light.x',
            service_data={'color_temp_kelvin': 4000},
        ))

    def test_for_hs_color_composes_hs_color_list(self):
        result = HassServiceComposer.for_hs_color(
            domain='light', parent_entity_id='light.x',
            hue=180.0, saturation=75.0,
        )
        self.assertEqual(result.service_data, {'hs_color': [180.0, 75.0]})
        self.assertEqual(result.service, 'turn_on')
        self.assertEqual(result.hass_entity_id, 'light.x')
