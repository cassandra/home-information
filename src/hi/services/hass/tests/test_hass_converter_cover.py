import logging

from django.test import TestCase

from hi.apps.control.models import Controller
from hi.apps.entity.enums import EntityStateType, EntityType
from hi.apps.entity.models import EntityState
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassApi, HassDevice, HassServiceCall

logging.disable(logging.CRITICAL)


def _make_cover_api_dict(
        entity_id='cover.example',
        state='closed',
        device_class=None,
        current_position=None,
        friendly_name=None ):
    attributes = {}
    if friendly_name:
        attributes[ 'friendly_name' ] = friendly_name
    if device_class is not None:
        attributes[ 'device_class' ] = device_class
    if current_position is not None:
        attributes[ 'current_position' ] = current_position
    return {
        'entity_id': entity_id,
        'state': state,
        'attributes': attributes,
        'last_changed': '2026-01-01T00:00:00+00:00',
        'last_reported': '2026-01-01T00:00:00+00:00',
        'last_updated': '2026-01-01T00:00:00+00:00',
        'context': { 'id': 'ctx', 'parent_id': None, 'user_id': None },
    }


def _make_cover_hass_state( **kwargs ):
    return HassConverter.create_hass_state( _make_cover_api_dict( **kwargs ) )


def _build_cover_device( device_id, **kwargs ):
    api_dict = _make_cover_api_dict( entity_id=f'cover.{device_id}', **kwargs )
    hass_state = HassConverter.create_hass_state( api_dict )
    device = HassDevice( device_id=device_id )
    device.add_state( hass_state )
    return device


class TestCoverEntityStateTypeMapping(TestCase):
    """``_determine_entity_state_type_from_mapping`` must split
    covers into the discrete OPEN_CLOSE family and the continuous
    OPEN_CLOSE_POSITION family based on whether the HA state
    reports ``current_position``."""

    def test_garage_without_position_is_open_close(self):
        hass_state = _make_cover_hass_state( device_class='garage' )
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.OPEN_CLOSE )

    def test_blind_with_position_is_open_close_position(self):
        hass_state = _make_cover_hass_state(
            device_class='blind', current_position=42, state='open',
        )
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.OPEN_CLOSE_POSITION )

    def test_no_device_class_no_position_falls_through_to_open_close(self):
        hass_state = _make_cover_hass_state()
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.OPEN_CLOSE )

    def test_position_override_beats_device_class_specialization(self):
        # A garage cover that *does* report current_position is
        # routed to OPEN_CLOSE_POSITION even though the device-class
        # mapping table would otherwise pick OPEN_CLOSE.
        hass_state = _make_cover_hass_state(
            device_class='garage', current_position=80, state='open',
        )
        result = HassConverter._determine_entity_state_type_from_mapping( hass_state )
        self.assertEqual( result, EntityStateType.OPEN_CLOSE_POSITION )


class TestCoverInboundStateTranslation(TestCase):
    """``_cover_to_sensor_value_map`` must emit numeric position
    when present and otherwise pass HA's discrete state through
    unchanged (including transitional ``opening`` / ``closing``)."""

    def test_position_is_emitted_as_numeric_string(self):
        hass_state = _make_cover_hass_state(
            device_class='blind', current_position=42, state='open',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        self.assertEqual( list( value_map.values() )[ 0 ], '42' )

    def test_position_zero_is_emitted_not_dropped(self):
        # str('0') is non-empty so monitors.py's truthiness check
        # passes through; the regression risk is treating '0' as
        # falsy upstream and skipping the commit.
        hass_state = _make_cover_hass_state(
            device_class='blind', current_position=0, state='closed',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        self.assertEqual( list( value_map.values() )[ 0 ], '0' )

    def test_discrete_state_passes_through_when_no_position(self):
        for state in ( 'open', 'closed', 'opening', 'closing' ):
            with self.subTest( state=state ):
                hass_state = _make_cover_hass_state(
                    device_class='garage', state=state,
                )
                value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
                self.assertEqual( list( value_map.values() )[ 0 ], state )

    def test_non_numeric_position_returns_empty(self):
        # Defensive: HA shouldn't produce non-numeric positions,
        # but we don't want to crash the poll loop if it does.
        hass_state = _make_cover_hass_state(
            device_class='blind', current_position='garbage', state='open',
        )
        value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
        self.assertEqual( value_map, {} )


class TestCoverEntityTypeRouting(TestCase):
    """``hass_device_to_entity_type`` routes garage covers to the
    specialized GARAGE_DOOR_OPENER and every other cover device
    class to the generic OPEN_CLOSE_ACTUATOR."""

    def test_garage_routes_to_garage_door_opener(self):
        device = _build_cover_device( 'main_garage', device_class='garage' )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.GARAGE_DOOR_OPENER,
        )

    def test_blind_routes_to_open_close_actuator(self):
        device = _build_cover_device( 'living_room_blind', device_class='blind' )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.OPEN_CLOSE_ACTUATOR,
        )

    def test_no_device_class_routes_to_open_close_actuator(self):
        device = _build_cover_device( 'unspecified_cover' )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.OPEN_CLOSE_ACTUATOR,
        )


class TestCoverImport(TestCase):
    """End-to-end import of cover devices: the right
    EntityStateType, controller type, and outbound payload land
    on the imported models."""

    def test_garage_imports_with_open_close_state(self):
        device = _build_cover_device( 'garage_a', device_class='garage' )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )
        states = list( EntityState.objects.filter( entity=entity ) )
        self.assertEqual( len( states ), 1 )
        self.assertEqual( states[ 0 ].entity_state_type, EntityStateType.OPEN_CLOSE )

        controllers = list( Controller.objects.filter( entity_state=states[ 0 ] ) )
        self.assertEqual( len( controllers ), 1 )
        payload = controllers[ 0 ].integration_payload
        self.assertEqual( payload.get( 'on_service' ), HassApi.OPEN_COVER_SERVICE )
        self.assertEqual( payload.get( 'off_service' ), HassApi.CLOSE_COVER_SERVICE )

    def test_blind_with_position_imports_with_open_close_position_state(self):
        device = _build_cover_device(
            'blind_a', device_class='blind',
            current_position=50, state='open',
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device=device,
            add_alarm_events=False,
        )
        states = list( EntityState.objects.filter( entity=entity ) )
        self.assertEqual( len( states ), 1 )
        self.assertEqual(
            states[ 0 ].entity_state_type, EntityStateType.OPEN_CLOSE_POSITION,
        )

        controllers = list( Controller.objects.filter( entity_state=states[ 0 ] ) )
        self.assertEqual( len( controllers ), 1 )
        payload = controllers[ 0 ].integration_payload
        self.assertEqual(
            payload.get( 'set_service' ), HassApi.SET_COVER_POSITION_SERVICE,
        )


class TestCoverOutboundDispatch(TestCase):
    """``hi_value_to_hass_service_call`` for cover-domain payloads:
    string ``open`` / ``closed`` route to the discrete open/close
    services; numeric values route to set_cover_position."""

    def _payload(self, *, with_set_service=True):
        payload = {
            'domain': 'cover',
            'is_controllable': True,
            'on_service': HassApi.OPEN_COVER_SERVICE,
            'off_service': HassApi.CLOSE_COVER_SERVICE,
            'parameters': { 'position': 'percentage' },
        }
        if with_set_service:
            payload[ 'set_service' ] = HassApi.SET_COVER_POSITION_SERVICE
        return payload

    def test_open_routes_to_open_cover_service(self):
        service_call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='cover.front',
            hi_control_value='open',
            domain_payload=self._payload( with_set_service=False ),
        )
        self.assertEqual( service_call, HassServiceCall(
            domain='cover',
            service=HassApi.OPEN_COVER_SERVICE,
            hass_entity_id='cover.front',
        ))

    def test_closed_routes_to_close_cover_service(self):
        service_call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='cover.front',
            hi_control_value='closed',
            domain_payload=self._payload( with_set_service=False ),
        )
        self.assertEqual( service_call, HassServiceCall(
            domain='cover',
            service=HassApi.CLOSE_COVER_SERVICE,
            hass_entity_id='cover.front',
        ))

    def test_numeric_routes_to_set_cover_position(self):
        service_call = HassConverter.hi_value_to_hass_service_call(
            hass_substate_id='cover.blind',
            hi_control_value='42',
            domain_payload=self._payload(),
        )
        self.assertEqual( service_call, HassServiceCall(
            domain='cover',
            service=HassApi.SET_COVER_POSITION_SERVICE,
            hass_entity_id='cover.blind',
            service_data={ 'position': 42 },
        ))
