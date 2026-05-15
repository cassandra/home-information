import logging

from django.test import TestCase

from hi.apps.control.models import Controller
from hi.apps.entity.enums import EntityStateType, EntityStateValue, EntityType
from hi.apps.entity.models import EntityState
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassApi, HassDevice, HassServiceCall

logging.disable(logging.CRITICAL)


def _make_fan_api_dict(
        entity_id        = 'fan.example',
        state            = 'on',
        percentage       = None,
        percentage_step  = None,
        oscillating      = None,
        direction        = None,
        preset_mode      = None,
        preset_modes     = None,
        friendly_name    = None ):
    attributes = {}
    if friendly_name:
        attributes[ 'friendly_name' ] = friendly_name
    if percentage is not None:
        attributes[ 'percentage' ] = percentage
    if percentage_step is not None:
        attributes[ 'percentage_step' ] = percentage_step
    if oscillating is not None:
        attributes[ 'oscillating' ] = oscillating
    if direction is not None:
        attributes[ 'direction' ] = direction
    if preset_mode is not None:
        attributes[ 'preset_mode' ] = preset_mode
    if preset_modes is not None:
        attributes[ 'preset_modes' ] = preset_modes
    return {
        'entity_id': entity_id,
        'state': state,
        'attributes': attributes,
        'last_changed': '2026-01-01T00:00:00+00:00',
        'last_reported': '2026-01-01T00:00:00+00:00',
        'last_updated': '2026-01-01T00:00:00+00:00',
        'context': { 'id': 'ctx', 'parent_id': None, 'user_id': None },
    }


def _make_fan_hass_state( **kwargs ):
    return HassConverter.create_hass_state( _make_fan_api_dict( **kwargs ) )


def _build_fan_device( device_id, **kwargs ):
    api_dict = _make_fan_api_dict( entity_id=f'fan.{device_id}', **kwargs )
    hass_state = HassConverter.create_hass_state( api_dict )
    device = HassDevice( device_id=device_id )
    device.add_state( hass_state )
    return device


class TestFanEntityStateTypeMapping(TestCase):
    """The fan domain has three EntityStateType destinations
    depending on what the live state reports: ON_OFF (no
    percentage), POWER_LEVEL (percentage-only single state), or
    substate decomposition (percentage + any of oscillating /
    direction / preset_modes)."""

    def test_no_percentage_routes_to_on_off(self):
        hass_state = _make_fan_hass_state()
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.ON_OFF )

    def test_percentage_only_routes_to_power_level(self):
        hass_state = _make_fan_hass_state( percentage=50, percentage_step=25 )
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.POWER_LEVEL )

    def test_oscillating_attribute_disables_power_level(self):
        # Multi-feature fans go through substate decomposition,
        # not the single-state POWER_LEVEL path. The mapping
        # function returns ON_OFF (the table fallback); the
        # substate-creation flow takes over before that mapping
        # gets used as a primary state type.
        hass_state = _make_fan_hass_state(
            percentage=50, oscillating=False,
        )
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.ON_OFF )

    def test_direction_attribute_disables_power_level(self):
        hass_state = _make_fan_hass_state(
            percentage=50, direction='forward',
        )
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.ON_OFF )

    def test_preset_modes_attribute_disables_power_level(self):
        hass_state = _make_fan_hass_state(
            percentage=50, preset_modes=[ 'auto', 'sleep' ],
        )
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.ON_OFF )


class TestFanSubstateSpecs(TestCase):
    """Multi-feature fans decompose into peer substates. The
    spec list reflects what the live state reports — a fan
    without ``direction`` doesn't get a direction substate."""

    def test_single_state_fan_has_no_substates(self):
        # Speed-only fan stays single-state at the bare key.
        hass_state = _make_fan_hass_state( percentage=50 )
        specs = HassConverter._state_specs_for_hass_state( hass_state )
        self.assertEqual( specs, [] )

    def test_full_multi_feature_fan_has_four_substates(self):
        hass_state = _make_fan_hass_state(
            percentage=50, oscillating=True,
            direction='forward', preset_modes=[ 'auto', 'sleep' ],
        )
        specs = HassConverter._state_specs_for_hass_state( hass_state )
        suffixes = [ s.suffix for s in specs ]
        self.assertEqual( suffixes, [ 'speed', 'oscillating', 'direction', 'preset_mode' ] )

    def test_oscillating_only_fan_has_oscillating_substate_no_speed(self):
        # Fan declares oscillating but no percentage — only
        # oscillating substate (no speed peer to add).
        hass_state = _make_fan_hass_state( oscillating=False )
        specs = HassConverter._state_specs_for_hass_state( hass_state )
        suffixes = [ s.suffix for s in specs ]
        self.assertEqual( suffixes, [ 'oscillating' ] )

    def test_speed_substate_has_power_level_type_and_speed_label(self):
        hass_state = _make_fan_hass_state(
            percentage=50, oscillating=True,
        )
        specs = HassConverter._state_specs_for_hass_state( hass_state )
        speed = next( s for s in specs if s.suffix == 'speed' )
        self.assertEqual( speed.entity_state_type, EntityStateType.POWER_LEVEL )
        self.assertEqual( speed.display_label, 'Speed' )
        self.assertTrue( speed.is_controllable )

    def test_preset_substate_value_range_from_preset_modes(self):
        hass_state = _make_fan_hass_state(
            preset_modes=[ 'auto', 'sleep', 'eco' ],
        )
        specs = HassConverter._state_specs_for_hass_state( hass_state )
        preset = next( s for s in specs if s.suffix == 'preset_mode' )
        self.assertEqual(
            preset.value_range,
            { 'auto': 'auto', 'sleep': 'sleep', 'eco': 'eco' },
        )


class TestFanInboundStateTranslation(TestCase):

    def test_speed_only_fan_emits_numeric_percentage_at_bare_key(self):
        hass_state = _make_fan_hass_state( percentage=42 )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        self.assertEqual( len( value_map ), 1 )
        key, value = next( iter( value_map.items() ) )
        self.assertEqual( key.integration_name, hass_state.entity_id )
        self.assertEqual( value, '42' )

    def test_no_percentage_fan_passes_state_through(self):
        hass_state = _make_fan_hass_state( state='on' )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        self.assertEqual( list( value_map.values() )[ 0 ], 'on' )

    def test_multi_feature_fan_decomposes_into_suffixed_keys(self):
        hass_state = _make_fan_hass_state(
            entity_id='fan.living_room',
            percentage=60, oscillating=True,
            direction='reverse', preset_modes=[ 'auto', 'sleep', 'eco' ],
            preset_mode='sleep',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        names_to_values = {
            key.integration_name: value for key, value in value_map.items()
        }
        self.assertEqual( names_to_values, {
            'fan.living_room~speed': '60',
            'fan.living_room~oscillating': str( EntityStateValue.ON ),
            'fan.living_room~direction': 'reverse',
            'fan.living_room~preset_mode': 'sleep',
        } )

    def test_oscillating_false_emits_canonical_off(self):
        hass_state = _make_fan_hass_state(
            percentage=50, oscillating=False,
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        names_to_values = {
            key.integration_name: value for key, value in value_map.items()
        }
        self.assertEqual(
            names_to_values[ 'fan.example~oscillating' ],
            str( EntityStateValue.OFF ),
        )

    def test_non_numeric_percentage_returns_empty(self):
        hass_state = _make_fan_hass_state( percentage='garbage' )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        self.assertEqual( value_map, {} )


class TestFanImport(TestCase):
    """End-to-end import of fan devices: the right
    EntityStateType(s), controller(s), and outbound payloads
    land on the imported models."""

    def test_speed_only_fan_imports_with_single_power_level_state(self):
        device = _build_fan_device(
            'speedy', percentage=40, percentage_step=25,
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )
        self.assertEqual( entity.entity_type, EntityType.CEILING_FAN )

        states = list( EntityState.objects.filter( entity=entity ) )
        self.assertEqual( len( states ), 1 )
        self.assertEqual( states[ 0 ].entity_state_type, EntityStateType.POWER_LEVEL )

        controllers = list( Controller.objects.filter( entity_state=states[ 0 ] ) )
        self.assertEqual( len( controllers ), 1 )
        self.assertEqual(
            controllers[ 0 ].integration_payload.get( 'set_service' ),
            HassApi.SET_PERCENTAGE_SERVICE,
        )

    def test_multi_feature_fan_imports_with_four_substates(self):
        device = _build_fan_device(
            'smart_fan',
            percentage=60, oscillating=True,
            direction='forward',
            preset_modes=[ 'auto', 'sleep', 'eco' ],
            preset_mode='auto',
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )
        self.assertEqual( entity.entity_type, EntityType.CEILING_FAN )

        states = list( EntityState.objects.filter( entity=entity ) )
        self.assertEqual( len( states ), 4 )

        controllers_by_suffix = {}
        for ctrl in Controller.objects.filter( entity_state__entity=entity ):
            payload = ctrl.integration_payload
            controllers_by_suffix[ payload.get( 'substate' ) ] = ctrl

        self.assertEqual(
            set( controllers_by_suffix.keys() ),
            { 'speed', 'oscillating', 'direction', 'preset_mode' },
        )
        # Each substate's payload carries domain + parent_entity_id
        # so the outbound dispatcher can compose the right service call.
        for suffix, ctrl in controllers_by_suffix.items():
            payload = ctrl.integration_payload
            self.assertEqual( payload.get( 'domain' ), HassApi.FAN_DOMAIN )
            self.assertEqual( payload.get( 'parent_entity_id' ), 'fan.smart_fan' )

    def test_multi_feature_fan_substate_state_types(self):
        device = _build_fan_device(
            'fan_b', percentage=50, oscillating=True,
            direction='reverse',
            preset_modes=[ 'auto' ],
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )
        # Index by the integration-payload's substate suffix (the
        # stable contract) rather than by parsing the EntityState's
        # display label, which is presentational and could change.
        types_by_suffix = {
            ctrl.integration_payload.get( 'substate' ): ctrl.entity_state.entity_state_type
            for ctrl in Controller.objects.filter( entity_state__entity=entity )
        }
        self.assertEqual( types_by_suffix[ 'speed' ], EntityStateType.POWER_LEVEL )
        self.assertEqual( types_by_suffix[ 'oscillating' ], EntityStateType.ON_OFF )
        self.assertEqual( types_by_suffix[ 'direction' ], EntityStateType.DISCRETE )
        self.assertEqual( types_by_suffix[ 'preset_mode' ], EntityStateType.DISCRETE )


class TestFanOutboundDispatchSpeedOnly(TestCase):
    """Single-state speed-only fans take a different outbound
    path than multi-feature fans: their domain_payload has no
    ``substate`` field, so dispatch flows through
    ``_payload_driven_service_call`` to the
    ``HassServiceComposer.for_numeric_parameter`` percentage
    branch. This is distinct from the substate-dispatch path
    exercised by ``TestFanOutboundDispatch``."""

    def test_numeric_routes_to_set_percentage(self):
        payload = {
            'domain': HassApi.FAN_DOMAIN,
            'is_controllable': True,
            'on_service': HassApi.TURN_ON_SERVICE,
            'off_service': HassApi.TURN_OFF_SERVICE,
            'set_service': HassApi.SET_PERCENTAGE_SERVICE,
            'parameters': { 'percentage': 'percentage' },
        }
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='fan.zoo_fan',
            hi_control_value='42',
            domain_payload=payload,
        )
        self.assertEqual( call, HassServiceCall(
            domain=HassApi.FAN_DOMAIN,
            service=HassApi.SET_PERCENTAGE_SERVICE,
            hass_entity_id='fan.zoo_fan',
            service_data={ 'percentage': 42 },
        ))


class TestFanOutboundDispatch(TestCase):
    """Each fan substate routes to the matching HA service via
    ``hi_value_to_hass_service_call``."""

    def _substate_payload( self, suffix ):
        return {
            'domain': HassApi.FAN_DOMAIN,
            'is_controllable': True,
            'substate': suffix,
            'parent_entity_id': 'fan.smart_fan',
        }

    def test_speed_routes_to_set_percentage(self):
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='fan.smart_fan~speed',
            hi_control_value='75',
            domain_payload=self._substate_payload( 'speed' ),
        )
        self.assertEqual( call, HassServiceCall(
            domain=HassApi.FAN_DOMAIN,
            service=HassApi.SET_PERCENTAGE_SERVICE,
            hass_entity_id='fan.smart_fan',
            service_data={ 'percentage': 75 },
        ))

    def test_oscillating_on_routes_to_oscillate_true(self):
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='fan.smart_fan~oscillating',
            hi_control_value='on',
            domain_payload=self._substate_payload( 'oscillating' ),
        )
        self.assertEqual( call, HassServiceCall(
            domain=HassApi.FAN_DOMAIN,
            service=HassApi.OSCILLATE_SERVICE,
            hass_entity_id='fan.smart_fan',
            service_data={ 'oscillating': True },
        ))

    def test_oscillating_off_routes_to_oscillate_false(self):
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='fan.smart_fan~oscillating',
            hi_control_value='off',
            domain_payload=self._substate_payload( 'oscillating' ),
        )
        self.assertEqual( call.service_data, { 'oscillating': False } )

    def test_direction_routes_to_set_direction(self):
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='fan.smart_fan~direction',
            hi_control_value='reverse',
            domain_payload=self._substate_payload( 'direction' ),
        )
        self.assertEqual( call, HassServiceCall(
            domain=HassApi.FAN_DOMAIN,
            service=HassApi.SET_DIRECTION_SERVICE,
            hass_entity_id='fan.smart_fan',
            service_data={ 'direction': 'reverse' },
        ))

    def test_preset_routes_to_set_preset_mode(self):
        call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='fan.smart_fan~preset_mode',
            hi_control_value='sleep',
            domain_payload=self._substate_payload( 'preset_mode' ),
        )
        self.assertEqual( call, HassServiceCall(
            domain=HassApi.FAN_DOMAIN,
            service=HassApi.SET_PRESET_MODE_SERVICE,
            hass_entity_id='fan.smart_fan',
            service_data={ 'preset_mode': 'sleep' },
        ))
