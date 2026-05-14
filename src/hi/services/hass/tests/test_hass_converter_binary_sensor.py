import logging

from django.test import TestCase

from hi.apps.entity.enums import (
    EntityStateType, EntityStateValue, EntityType,
)
from hi.apps.entity.models import EntityState
from hi.apps.event.models import EventDefinition
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_metadata import HassMetaData
from hi.services.hass.hass_models import HassDevice

logging.disable(logging.CRITICAL)


def _build_binary_sensor_device( name, device_class = None, state = 'off' ):
    """Construct a HassDevice with a single ``binary_sensor.x`` state
    of the specified device_class. Mirrors the pattern in
    ``test_hass_converter_create.py``."""
    attributes = {
        'friendly_name': name.replace( '_', ' ' ).title(),
    }
    if device_class is not None:
        attributes[ 'device_class' ] = device_class
    api_dict = {
        'entity_id': f'binary_sensor.{name}',
        'state': state,
        'attributes': attributes,
        'last_changed': '2026-01-01T00:00:00+00:00',
        'last_reported': '2026-01-01T00:00:00+00:00',
        'last_updated': '2026-01-01T00:00:00+00:00',
        'context': { 'id': 'ctx', 'parent_id': None, 'user_id': None },
    }
    hass_state = HassConverter.create_hass_state( api_dict )
    device = HassDevice( device_id = name )
    device.add_state( hass_state )
    return device, hass_state


def _value_for( hass_state ):
    value_map = HassConverter.hass_state_to_sensor_value_map( hass_state )
    return next( iter( value_map.values() ) )


class TestSmokeBinarySensor(TestCase):
    """Smoke is the new device-class branch added for #300. Covers
    value emission, EntityState creation (regression guard for the
    fall-through-to-BLOB bug), and EntityType assignment."""

    def test_smoke_on_emits_smoke_detected(self):
        _, hass_state = _build_binary_sensor_device(
            'kitchen_smoke', device_class = 'smoke', state = 'on',
        )
        self.assertEqual(
            _value_for( hass_state ),
            str( EntityStateValue.SMOKE_DETECTED ),
        )

    def test_smoke_off_emits_smoke_clear(self):
        _, hass_state = _build_binary_sensor_device(
            'kitchen_smoke', device_class = 'smoke', state = 'off',
        )
        self.assertEqual(
            _value_for( hass_state ),
            str( EntityStateValue.SMOKE_CLEAR ),
        )

    def test_smoke_creates_entity_state_with_smoke_type(self):
        # Regression guard. The mapping table picks
        # ``EntityStateType.SMOKE``, but
        # ``_create_sensor_from_entity_state_type_with_params``
        # previously had no SMOKE branch and fell through to
        # ``create_blob_sensor`` — the EntityState ended up with
        # ``entity_state_type_str='blob'``, breaking every smoke-
        # specific dispatch downstream (EntityStateDisplayData,
        # rendering, etc.).
        device, _ = _build_binary_sensor_device(
            'kitchen_smoke', device_class = 'smoke',
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device = device, add_alarm_events = False,
        )
        states = list( EntityState.objects.filter( entity = entity ) )
        self.assertEqual( len( states ), 1 )
        self.assertEqual(
            states[ 0 ].entity_state_type_str,
            str( EntityStateType.SMOKE ),
        )

    def test_smoke_assigns_smoke_detector_entity_type(self):
        device, _ = _build_binary_sensor_device(
            'kitchen_smoke', device_class = 'smoke',
        )
        entity = HassConverter.create_models_for_hass_device(
            hass_device = device, add_alarm_events = False,
        )
        self.assertEqual( entity.entity_type, EntityType.SMOKE_DETECTOR )

    def test_smoke_creates_alarm_event_definition(self):
        # Smoke is safety-critical and warrants its own alarm rule —
        # mirrors the door/window OPEN_CLOSE and motion MOVEMENT
        # branches that wire ``create_*_event_definition`` when
        # ``add_alarm_events=True``.
        device, _ = _build_binary_sensor_device(
            'kitchen_smoke', device_class = 'smoke',
        )
        HassConverter.create_models_for_hass_device(
            hass_device = device, add_alarm_events = True,
        )
        hass_event_defs = EventDefinition.objects.filter(
            integration_id = HassMetaData.integration_id,
        )
        self.assertEqual( hass_event_defs.count(), 1 )


class TestDoorWindowBinarySensor(TestCase):
    """Door and window were covered before #300 via the OPEN_CLOSE
    branch, but the binary-sensor work added explicit non-Insteon
    fixtures that make these mappings load-bearing for HA-only
    setups. Test the value-emission contract directly."""

    def test_door_on_emits_open(self):
        _, hass_state = _build_binary_sensor_device(
            'front_door', device_class = 'door', state = 'on',
        )
        self.assertEqual(
            _value_for( hass_state ), str( EntityStateValue.OPEN ),
        )

    def test_door_off_emits_closed(self):
        _, hass_state = _build_binary_sensor_device(
            'front_door', device_class = 'door', state = 'off',
        )
        self.assertEqual(
            _value_for( hass_state ), str( EntityStateValue.CLOSED ),
        )

    def test_window_on_emits_open(self):
        _, hass_state = _build_binary_sensor_device(
            'living_window', device_class = 'window', state = 'on',
        )
        self.assertEqual(
            _value_for( hass_state ), str( EntityStateValue.OPEN ),
        )


class TestGenericBinarySensorFallthrough(TestCase):
    """Generic ``binary_sensor.x`` states (no device_class) fall
    through to ``EntityStateType.ON_OFF``. Adding the smoke
    mapping mustn't accidentally regress this catch-all path."""

    def test_no_device_class_emits_on(self):
        _, hass_state = _build_binary_sensor_device(
            'unknown_thing', device_class = None, state = 'on',
        )
        self.assertEqual(
            _value_for( hass_state ), str( EntityStateValue.ON ),
        )

    def test_no_device_class_emits_off(self):
        _, hass_state = _build_binary_sensor_device(
            'unknown_thing', device_class = None, state = 'off',
        )
        self.assertEqual(
            _value_for( hass_state ), str( EntityStateValue.OFF ),
        )
