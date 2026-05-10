import logging
from unittest.mock import patch

from django.test import TestCase

from hi.apps.control.models import Controller
from hi.apps.entity.enums import EntityStateType, EntityType
from hi.apps.entity.models import EntityState
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassApi, HassDevice, HassServiceCall
from hi.integrations.integration_converter_helper import IntegrationConverterHelper
from hi.integrations.integration_metadata_cache import IntegrationMetadataCache
from hi.units import CANONICAL_TEMPERATURE_UNIT

logging.disable(logging.CRITICAL)


def _make_climate_api_dict(
        entity_id           = 'climate.example',
        state               = 'heat',
        hvac_modes          = None,
        hvac_action         = None,
        current_temperature = None,
        temperature         = None,
        target_temp_low     = None,
        target_temp_high    = None,
        fan_modes           = None,
        fan_mode            = None,
        current_humidity    = None,
        temperature_unit    = None,
        friendly_name       = None ):
    attributes = {}
    if friendly_name:
        attributes[ 'friendly_name' ] = friendly_name
    if hvac_modes is not None:
        attributes[ 'hvac_modes' ] = hvac_modes
    if hvac_action is not None:
        attributes[ 'hvac_action' ] = hvac_action
    if current_temperature is not None:
        attributes[ 'current_temperature' ] = current_temperature
    if temperature is not None:
        attributes[ 'temperature' ] = temperature
    if target_temp_low is not None:
        attributes[ 'target_temp_low' ] = target_temp_low
    if target_temp_high is not None:
        attributes[ 'target_temp_high' ] = target_temp_high
    if fan_modes is not None:
        attributes[ 'fan_modes' ] = fan_modes
    if fan_mode is not None:
        attributes[ 'fan_mode' ] = fan_mode
    if current_humidity is not None:
        attributes[ 'current_humidity' ] = current_humidity
    if temperature_unit is not None:
        attributes[ 'temperature_unit' ] = temperature_unit
    return {
        'entity_id': entity_id,
        'state': state,
        'attributes': attributes,
        'last_changed': '2026-01-01T00:00:00+00:00',
        'last_reported': '2026-01-01T00:00:00+00:00',
        'last_updated': '2026-01-01T00:00:00+00:00',
        'context': { 'id': 'ctx', 'parent_id': None, 'user_id': None },
    }


def _make_climate_hass_state( **kwargs ):
    return HassConverter.create_hass_state( _make_climate_api_dict( **kwargs ) )


def _build_climate_device( device_id, **kwargs ):
    api_dict = _make_climate_api_dict( entity_id=f'climate.{device_id}', **kwargs )
    hass_state = HassConverter.create_hass_state( api_dict )
    device = HassDevice( device_id=device_id )
    device.add_state( hass_state )
    return device


class TestClimateSubstateSpecs(TestCase):
    """Climate domain decomposes when ``hvac_modes`` is reported.
    The spec list reflects what the live state declares — a
    heat-only thermostat skips the dual-setpoint pair, a
    thermostat without ``fan_modes`` skips the fan_mode axis,
    etc."""

    def test_no_hvac_modes_returns_empty_specs(self):
        # Minimal climate without hvac_modes falls through to
        # legacy single-state TEMPERATURE handling.
        hass_state = _make_climate_hass_state( current_temperature=70 )
        specs = HassConverter._substate_specs_for_hass_state( hass_state )
        self.assertEqual( specs, [] )

    def test_full_feature_thermostat_has_all_axes(self):
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat', 'cool', 'heat_cool', 'off' ],
            hvac_action = 'idle',
            current_temperature = 70,
            target_temp_low = 68, target_temp_high = 75,
            fan_modes = [ 'auto', 'low', 'high' ],
            current_humidity = 42,
            temperature_unit = '°F',
        )
        specs = HassConverter._substate_specs_for_hass_state( hass_state )
        suffixes = [ s.suffix for s in specs ]
        self.assertEqual( suffixes, [
            'current_temperature',
            'hvac_mode',
            'hvac_action',
            'target_temperature',
            'target_temp_low',
            'target_temp_high',
            'fan_mode',
            'current_humidity',
        ])

    def test_heat_only_thermostat_omits_dual_setpoints(self):
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat', 'off' ],
            current_temperature = 21,
            temperature = 22,
            temperature_unit = '°C',
        )
        specs = HassConverter._substate_specs_for_hass_state( hass_state )
        suffixes = [ s.suffix for s in specs ]
        self.assertIn( 'target_temperature', suffixes )
        self.assertNotIn( 'target_temp_low', suffixes )
        self.assertNotIn( 'target_temp_high', suffixes )

    def test_heat_cool_only_thermostat_omits_single_setpoint(self):
        # Pure heat_cool with no other modes: dual setpoints only.
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat_cool' ],
            current_temperature = 70,
            target_temp_low = 68, target_temp_high = 75,
        )
        specs = HassConverter._substate_specs_for_hass_state( hass_state )
        suffixes = [ s.suffix for s in specs ]
        self.assertIn( 'target_temp_low', suffixes )
        self.assertIn( 'target_temp_high', suffixes )
        self.assertNotIn( 'target_temperature', suffixes )

    def test_setpoint_value_range_is_canonical_unit(self):
        # Setpoint bounds are always in HI's canonical temperature
        # unit regardless of HA's reported ``temperature_unit``. The
        # display layer is responsible for converting bounds to the
        # user's preferred unit at render time.
        for ha_unit in ( '°F', '°C', None ):
            with self.subTest( ha_unit = ha_unit ):
                hass_state = _make_climate_hass_state(
                    hvac_modes = [ 'heat', 'off' ],
                    temperature_unit = ha_unit,
                )
                specs = HassConverter._substate_specs_for_hass_state( hass_state )
                setpoint = next( s for s in specs if s.suffix == 'target_temperature' )
                self.assertEqual(
                    setpoint.value_range,
                    {
                        'min': HassConverter._SETPOINT_MIN_CANONICAL,
                        'max': HassConverter._SETPOINT_MAX_CANONICAL,
                    },
                )

    def test_temperature_substates_carry_canonical_units(self):
        # The temperature-bearing climate substates declare HI's
        # canonical unit on the spec so it propagates to
        # EntityState.units at creation time.
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat', 'cool', 'heat_cool', 'off' ],
            current_temperature = 70,
            target_temp_low = 68, target_temp_high = 75,
            temperature_unit = '°F',
        )
        specs = HassConverter._substate_specs_for_hass_state( hass_state )
        temperature_suffixes = {
            'current_temperature', 'target_temperature',
            'target_temp_low', 'target_temp_high',
        }
        for spec in specs:
            if spec.suffix in temperature_suffixes:
                self.assertEqual(
                    spec.units,
                    CANONICAL_TEMPERATURE_UNIT,
                    f'{spec.suffix} should carry canonical units',
                )

    def test_hvac_mode_choices_from_hvac_modes(self):
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat', 'auto', 'off' ],
        )
        specs = HassConverter._substate_specs_for_hass_state( hass_state )
        hvac_mode = next( s for s in specs if s.suffix == 'hvac_mode' )
        self.assertEqual(
            hvac_mode.value_range,
            { 'heat': 'heat', 'auto': 'auto', 'off': 'off' },
        )

    def test_fan_mode_value_range_from_fan_modes(self):
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat', 'off' ],
            fan_modes = [ 'auto', 'low', 'medium', 'high' ],
        )
        specs = HassConverter._substate_specs_for_hass_state( hass_state )
        fan_mode = next( s for s in specs if s.suffix == 'fan_mode' )
        self.assertEqual(
            fan_mode.value_range,
            { 'auto': 'auto', 'low': 'low', 'medium': 'medium', 'high': 'high' },
        )

    def test_fan_mode_omitted_when_fan_modes_absent(self):
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat', 'off' ],
        )
        specs = HassConverter._substate_specs_for_hass_state( hass_state )
        suffixes = [ s.suffix for s in specs ]
        self.assertNotIn( 'fan_mode', suffixes )


def _reset_unit_cache():
    """Singleton cache state must not leak across tests."""
    cache = IntegrationMetadataCache()
    cache._cache.clear()
    cache._warmed = False


def _seed_unit_cache_for_climate(parent_entity_id, units, suffixes):
    """Pre-populate IntegrationMetadataCache for the given climate
    substates so converter tests can exercise unit-translation paths
    without first creating Sensor/Controller rows in the DB."""
    cache = IntegrationMetadataCache()
    cache._warmed = True
    for suffix in suffixes:
        key = HassConverter._substate_integration_key_for_suffix(
            parent_entity_id = parent_entity_id, suffix = suffix,
        )
        cache._cache[ key ] = { 'units': units }


class TestClimateInboundStateTranslation(TestCase):

    def setUp(self):
        _reset_unit_cache()

    def tearDown(self):
        _reset_unit_cache()

    def test_full_feature_thermostat_emits_all_substates(self):
        # Native unit matches HI's canonical so values pass through
        # unchanged — this test exercises substate emission shape.
        # Inbound conversion when native != canonical is covered
        # separately below.
        hass_state = _make_climate_hass_state(
            entity_id = 'climate.bedroom',
            state = 'heat_cool',
            hvac_modes = [ 'heat', 'cool', 'heat_cool', 'off' ],
            hvac_action = 'idle',
            current_temperature = 21.5,
            target_temp_low = 20, target_temp_high = 24,
            fan_modes = [ 'auto', 'high' ],
            fan_mode = 'auto',
            current_humidity = 42,
            temperature_unit = '°C',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        names_to_values = {
            key.integration_name: value for key, value in value_map.items()
        }
        self.assertEqual( names_to_values, {
            'climate.bedroom~current_temperature': '21.5',
            'climate.bedroom~hvac_mode': 'heat_cool',
            'climate.bedroom~hvac_action': 'idle',
            'climate.bedroom~target_temp_low': '20.0',
            'climate.bedroom~target_temp_high': '24.0',
            'climate.bedroom~fan_mode': 'auto',
            'climate.bedroom~current_humidity': '42.0',
        })

    def test_fahrenheit_native_temperatures_converted_to_canonical(self):
        # An °F-native climate state's temperatures are converted to
        # HI's canonical unit at the boundary so cached / persisted
        # values are unit-coherent across the system.
        _seed_unit_cache_for_climate(
            parent_entity_id = 'climate.bedroom',
            units = CANONICAL_TEMPERATURE_UNIT,
            suffixes = (
                'current_temperature', 'target_temp_low', 'target_temp_high',
            ),
        )
        hass_state = _make_climate_hass_state(
            entity_id = 'climate.bedroom',
            state = 'heat_cool',
            hvac_modes = [ 'heat', 'cool', 'heat_cool', 'off' ],
            hvac_action = 'idle',
            current_temperature = 71.6,
            target_temp_low = 68, target_temp_high = 75.2,
            temperature_unit = '°F',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        names_to_values = {
            key.integration_name: value for key, value in value_map.items()
        }
        self.assertAlmostEqual(
            float( names_to_values[ 'climate.bedroom~current_temperature' ] ),
            22.0, places = 2,
        )
        self.assertAlmostEqual(
            float( names_to_values[ 'climate.bedroom~target_temp_low' ] ),
            20.0, places = 2,
        )
        self.assertAlmostEqual(
            float( names_to_values[ 'climate.bedroom~target_temp_high' ] ),
            24.0, places = 2,
        )

    def test_unknown_native_unit_falls_through_unchanged(self):
        # Defensive fallback: if HA reports a unit string we don't
        # recognize, pass the value through rather than raising.
        hass_state = _make_climate_hass_state(
            entity_id = 'climate.exotic',
            hvac_modes = [ 'heat', 'off' ],
            current_temperature = 99.9,
            temperature = 100.0,
            temperature_unit = 'kelvin',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        names_to_values = {
            key.integration_name: value for key, value in value_map.items()
        }
        self.assertEqual(
            names_to_values[ 'climate.exotic~current_temperature' ],
            '99.9',
        )

    def test_single_mode_thermostat_emits_single_setpoint(self):
        hass_state = _make_climate_hass_state(
            entity_id = 'climate.heater',
            state = 'heat',
            hvac_modes = [ 'heat', 'off' ],
            hvac_action = 'heating',
            current_temperature = 21,
            temperature = 22,
            temperature_unit = '°C',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        names_to_values = {
            key.integration_name: value for key, value in value_map.items()
        }
        self.assertEqual( names_to_values[ 'climate.heater~target_temperature' ], '22.0' )
        self.assertNotIn( 'climate.heater~target_temp_low', names_to_values )
        self.assertNotIn( 'climate.heater~target_temp_high', names_to_values )

    def test_missing_attribute_drops_substate_value(self):
        # heat_cool mode but the dual-setpoint attributes aren't
        # in the live state — substates exist but emit nothing.
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat', 'cool', 'heat_cool' ],
            current_temperature = 70,
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        names_to_values = {
            key.integration_name: value for key, value in value_map.items()
        }
        self.assertNotIn( 'climate.example~target_temperature', names_to_values )
        self.assertNotIn( 'climate.example~target_temp_low', names_to_values )

    def test_non_numeric_temperature_drops_value(self):
        hass_state = _make_climate_hass_state(
            hvac_modes = [ 'heat', 'off' ],
            current_temperature = 'garbage',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        names_to_values = {
            key.integration_name: value for key, value in value_map.items()
        }
        self.assertNotIn( 'climate.example~current_temperature', names_to_values )


class TestClimateImport(TestCase):

    def setUp(self):
        _reset_unit_cache()

    def tearDown(self):
        _reset_unit_cache()

    def test_full_feature_thermostat_imports_all_substates(self):
        device = _build_climate_device(
            'bedroom', state='heat_cool',
            hvac_modes = [ 'heat', 'cool', 'heat_cool', 'off' ],
            hvac_action = 'idle',
            current_temperature = 70,
            target_temp_low = 68, target_temp_high = 75,
            fan_modes = [ 'auto', 'high' ],
            fan_mode = 'auto',
            current_humidity = 42,
            temperature_unit = '°F',
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device, add_alarm_events=False,
        )
        self.assertEqual( entity.entity_type, EntityType.THERMOSTAT )

        states = list( EntityState.objects.filter( entity=entity ) )
        self.assertEqual( len( states ), 8 )

        types_by_suffix = {
            ctrl.integration_payload.get( 'substate' ): ctrl.entity_state.entity_state_type
            for ctrl in Controller.objects.filter( entity_state__entity=entity )
        }
        # Controllable substates only (sensor-only ones don't get controllers).
        self.assertEqual( types_by_suffix[ 'hvac_mode' ], EntityStateType.DISCRETE )
        self.assertEqual( types_by_suffix[ 'target_temp_low' ], EntityStateType.TEMPERATURE )
        self.assertEqual( types_by_suffix[ 'target_temp_high' ], EntityStateType.TEMPERATURE )
        self.assertEqual( types_by_suffix[ 'target_temperature' ], EntityStateType.TEMPERATURE )
        self.assertEqual( types_by_suffix[ 'fan_mode' ], EntityStateType.DISCRETE )

    def test_temperature_substates_persist_canonical_units(self):
        device = _build_climate_device(
            'bedroom', state='heat',
            hvac_modes = [ 'heat', 'off' ],
            current_temperature = 70, temperature = 72,
            temperature_unit = '°F',
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device, add_alarm_events=False,
        )
        # Find temperature-bearing EntityStates and verify their
        # units field carries HI's canonical, regardless of HA's
        # native unit.
        temp_states = list( EntityState.objects.filter(
            entity = entity,
            entity_state_type_str = str( EntityStateType.TEMPERATURE ),
        ))
        self.assertGreater( len( temp_states ), 0 )
        for state in temp_states:
            self.assertEqual(
                state.units,
                CANONICAL_TEMPERATURE_UNIT,
            )

    def test_setpoint_controller_payload_carries_native_unit(self):
        # The HI-side unit lives only on EntityState.units (consulted
        # via the IntegrationMetadataCache); the payload only needs HA's
        # currently-reported native unit so outbound dispatch can
        # convert without fetching live HA state.
        device = _build_climate_device(
            'bedroom', state='heat',
            hvac_modes = [ 'heat', 'off' ],
            current_temperature = 70, temperature = 72,
            temperature_unit = '°F',
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device, add_alarm_events=False,
        )
        setpoint_ctrl = next(
            ctrl for ctrl in Controller.objects.filter( entity_state__entity=entity )
            if ctrl.integration_payload.get( 'substate' ) == 'target_temperature'
        )
        payload = setpoint_ctrl.integration_payload
        self.assertEqual( payload[ 'native_temperature_unit' ], '°F' )
        self.assertNotIn( 'hi_temperature_unit', payload )

    def test_heat_only_thermostat_imports_minimal_substates(self):
        device = _build_climate_device(
            'heater', state='heat',
            hvac_modes = [ 'heat', 'off' ],
            hvac_action = 'heating',
            current_temperature = 21, temperature = 22,
            temperature_unit = '°C',
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device, add_alarm_events=False,
        )
        states = list( EntityState.objects.filter( entity=entity ) )
        # current_temperature, hvac_mode, hvac_action, target_temperature
        self.assertEqual( len( states ), 4 )

        suffixes = {
            ctrl.integration_payload.get( 'substate' )
            for ctrl in Controller.objects.filter( entity_state__entity=entity )
        }
        self.assertIn( 'target_temperature', suffixes )
        self.assertIn( 'hvac_mode', suffixes )
        self.assertNotIn( 'target_temp_low', suffixes )
        self.assertNotIn( 'fan_mode', suffixes )


class TestClimateOutboundDispatch(TestCase):
    """Climate substate dispatch composes ``set_temperature`` /
    ``set_hvac_mode`` / ``set_fan_mode`` service calls. The
    target_temp_low/high pair uses companion-substate cache
    lookup like hue/saturation."""

    def setUp(self):
        _reset_unit_cache()

    def tearDown(self):
        _reset_unit_cache()

    def _payload( self, suffix, native_temperature_unit = None ):
        payload = {
            'domain': HassApi.CLIMATE_DOMAIN,
            'is_controllable': True,
            'substate': suffix,
            'parent_entity_id': 'climate.bedroom',
        }
        if native_temperature_unit is not None:
            payload[ 'native_temperature_unit' ] = native_temperature_unit
        return payload

    def test_target_temperature_routes_to_set_temperature(self):
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='climate.bedroom~target_temperature',
            hi_control_value='73',
            domain_payload=self._payload( 'target_temperature' ),
        )
        self.assertEqual( call, HassServiceCall(
            domain = HassApi.CLIMATE_DOMAIN,
            service = HassApi.SET_TEMPERATURE_SERVICE,
            hass_entity_id = 'climate.bedroom',
            service_data = { 'temperature': 73.0 },
        ))

    def test_hvac_mode_routes_to_set_hvac_mode(self):
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='climate.bedroom~hvac_mode',
            hi_control_value='cool',
            domain_payload=self._payload( 'hvac_mode' ),
        )
        self.assertEqual( call, HassServiceCall(
            domain = HassApi.CLIMATE_DOMAIN,
            service = HassApi.SET_HVAC_MODE_SERVICE,
            hass_entity_id = 'climate.bedroom',
            service_data = { 'hvac_mode': 'cool' },
        ))

    def test_fan_mode_routes_to_set_fan_mode(self):
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='climate.bedroom~fan_mode',
            hi_control_value='high',
            domain_payload=self._payload( 'fan_mode' ),
        )
        self.assertEqual( call, HassServiceCall(
            domain = HassApi.CLIMATE_DOMAIN,
            service = HassApi.SET_FAN_MODE_SERVICE,
            hass_entity_id = 'climate.bedroom',
            service_data = { 'fan_mode': 'high' },
        ))

    def test_target_temp_low_routes_to_range_with_cached_partner(self):
        partner_key = HassConverter._substate_integration_key_for_suffix(
            parent_entity_id='climate.bedroom', suffix='target_temp_high',
        )
        with patch.object(
                IntegrationConverterHelper, 'get_latest_state_values',
                return_value={ partner_key: '76' },
        ):
            call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='climate.bedroom~target_temp_low',
                hi_control_value='68',
                domain_payload=self._payload( 'target_temp_low' ),
            )
        self.assertEqual( call.service_data, {
            'target_temp_low': 68.0,
            'target_temp_high': 76.0,
        })

    def test_target_temp_high_routes_to_range_with_cached_partner(self):
        partner_key = HassConverter._substate_integration_key_for_suffix(
            parent_entity_id='climate.bedroom', suffix='target_temp_low',
        )
        with patch.object(
                IntegrationConverterHelper, 'get_latest_state_values',
                return_value={ partner_key: '67' },
        ):
            call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='climate.bedroom~target_temp_high',
                hi_control_value='80',
                domain_payload=self._payload( 'target_temp_high' ),
            )
        self.assertEqual( call.service_data, {
            'target_temp_low': 67.0,
            'target_temp_high': 80.0,
        })

    def test_target_temp_pair_no_cached_partner_falls_back(self):
        # Without a cached partner value, the changed value is
        # used for both bounds — safe ordering, no HA error.
        with patch.object(
                IntegrationConverterHelper, 'get_latest_state_values',
                return_value={},
        ):
            call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='climate.bedroom~target_temp_low',
                hi_control_value='70',
                domain_payload=self._payload( 'target_temp_low' ),
            )
        self.assertEqual( call.service_data, {
            'target_temp_low': 70.0,
            'target_temp_high': 70.0,
        })

    def test_target_temperature_converts_canonical_to_native(self):
        # HI's stored value is in canonical units; payload-tagged
        # native unit drives outbound conversion at the boundary.
        # The HI-side unit is read from the IntegrationMetadataCache.
        _seed_unit_cache_for_climate(
            parent_entity_id = 'climate.bedroom',
            units = '°C',
            suffixes = ( 'target_temperature', ),
        )
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='climate.bedroom~target_temperature',
            hi_control_value='22',
            domain_payload=self._payload(
                'target_temperature',
                native_temperature_unit = '°F',
            ),
        )
        self.assertAlmostEqual(
            call.service_data[ 'temperature' ], 71.6, places = 2,
        )

    def test_target_temp_range_converts_canonical_to_native(self):
        _seed_unit_cache_for_climate(
            parent_entity_id = 'climate.bedroom',
            units = '°C',
            suffixes = ( 'target_temp_low', 'target_temp_high' ),
        )
        partner_key = HassConverter._substate_integration_key_for_suffix(
            parent_entity_id='climate.bedroom', suffix='target_temp_high',
        )
        # Cached partner value is also in canonical units (it came
        # through the same boundary-converted translation path).
        with patch.object(
                IntegrationConverterHelper, 'get_latest_state_values',
                return_value={ partner_key: '24' },
        ):
            call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id='climate.bedroom~target_temp_low',
                hi_control_value='20',
                domain_payload=self._payload(
                    'target_temp_low',
                    native_temperature_unit = '°F',
                ),
            )
        self.assertAlmostEqual(
            call.service_data[ 'target_temp_low' ], 68.0, places = 2,
        )
        self.assertAlmostEqual(
            call.service_data[ 'target_temp_high' ], 75.2, places = 2,
        )

    def test_target_temperature_no_conversion_when_units_match(self):
        # When HI's unit matches HA's native, value passes through.
        _seed_unit_cache_for_climate(
            parent_entity_id = 'climate.bedroom',
            units = '°C',
            suffixes = ( 'target_temperature', ),
        )
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='climate.bedroom~target_temperature',
            hi_control_value='22',
            domain_payload=self._payload(
                'target_temperature',
                native_temperature_unit = '°C',
            ),
        )
        self.assertEqual( call.service_data, { 'temperature': 22.0 } )
