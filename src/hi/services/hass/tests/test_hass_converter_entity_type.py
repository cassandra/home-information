import logging

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassApi, HassDevice

logging.disable(logging.CRITICAL)


def _make_device(
        entity_id     : str,
        friendly_name : str = '',
        device_class  : str = None,
) -> HassDevice:
    """Construct a minimal real HassDevice with a single state. The
    state's ``entity_id`` drives ``domain_set`` (the prefix before
    ``.``) and the ``device_class`` attribute drives
    ``device_class_set``. ``friendly_name`` populates the name the
    converter exposes via ``hass_device_to_entity_name`` — used by
    the light-name heuristic. Avoids mocking so the converter
    runs over genuine HassDevice / HassState objects."""
    attributes = {}
    if friendly_name:
        attributes[HassApi.FRIENDLY_NAME_ATTR] = friendly_name
    if device_class is not None:
        attributes[HassApi.DEVICE_CLASS_ATTR] = device_class
    api_dict = {
        'entity_id'    : entity_id,
        'state'        : 'off',
        'attributes'   : attributes,
        'last_changed' : '2026-01-01T00:00:00+00:00',
        'last_reported': '2026-01-01T00:00:00+00:00',
        'last_updated' : '2026-01-01T00:00:00+00:00',
        'context'      : { 'id': 'ctx', 'parent_id': None, 'user_id': None },
    }
    state = HassConverter.create_hass_state( api_dict )
    device_id = entity_id.split( '.', 1 )[1] if '.' in entity_id else entity_id
    device = HassDevice( device_id = device_id )
    device.add_state( state )
    return device


class HassDeviceToEntityTypeTests( TestCase ):
    """Pin the domain/device-class → EntityType mapping. Each test
    builds a minimal real HassDevice that carries the predicate
    being exercised; a switch-domain regression where generic
    switches fell through to OTHER motivated the broader sweep."""

    def test_switch_domain_with_neutral_name_maps_to_on_off_switch( self ):
        device = _make_device(
            entity_id = 'switch.relay_a', friendly_name = 'Garage Relay',
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.ON_OFF_SWITCH,
        )

    def test_outlet_device_class_takes_precedence_over_switch_domain( self ):
        device = _make_device(
            entity_id = 'switch.outlet_a',
            friendly_name = 'Garage Outlet',
            device_class = HassApi.OUTLET_DEVICE_CLASS,
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.ELECTRICAL_OUTLET,
        )

    def test_lock_domain_maps_to_door_lock( self ):
        device = _make_device(
            entity_id = 'lock.front_door', friendly_name = 'Front Door',
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.DOOR_LOCK,
        )

    def test_cover_domain_maps_to_open_close_actuator( self ):
        device = _make_device(
            entity_id = 'cover.bedroom_blinds', friendly_name = 'Bedroom Blinds',
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.OPEN_CLOSE_ACTUATOR,
        )

    def test_fan_domain_maps_to_ceiling_fan( self ):
        device = _make_device(
            entity_id = 'fan.living_room', friendly_name = 'Living Room Fan',
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.CEILING_FAN,
        )

    def test_climate_domain_maps_to_thermostat( self ):
        device = _make_device(
            entity_id = 'climate.upstairs', friendly_name = 'Upstairs',
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.THERMOSTAT,
        )

    def test_camera_domain_maps_to_camera( self ):
        device = _make_device(
            entity_id = 'camera.front_door', friendly_name = 'Front Door Cam',
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.CAMERA,
        )

    def test_light_domain_maps_to_light( self ):
        device = _make_device(
            entity_id = 'light.kitchen_main', friendly_name = 'Kitchen Main',
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.LIGHT,
        )

    def test_motion_device_class_maps_to_motion_sensor( self ):
        device = _make_device(
            entity_id = 'binary_sensor.hallway',
            friendly_name = 'Hallway',
            device_class = HassApi.MOTION_DEVICE_CLASS,
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.MOTION_SENSOR,
        )

    def test_unknown_domain_falls_through_to_other( self ):
        device = _make_device(
            entity_id = 'unknown_domain.thing', friendly_name = 'Thing',
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.OTHER,
        )


class HassSwitchNameInferenceTests( TestCase ):
    """Switch-domain devices whose name reveals what they're wired
    to are pre-typed at import time to spare the operator the
    per-entity edit. Three keyword groups, in precedence order:
    outlet/plug → ELECTRICAL_OUTLET, fan → CEILING_FAN, light →
    LIGHT. Tests cover each keyword family plus precedence and
    word-boundary false-positive guards."""

    def _entity_type_for_name( self, friendly_name : str ) -> EntityType:
        device = _make_device(
            entity_id = 'switch.relay_a', friendly_name = friendly_name,
        )
        return HassConverter.hass_device_to_entity_type( device )

    # ----- light family -----

    def test_switch_named_light_promotes_to_light( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Kitchen Light' ),
            EntityType.LIGHT,
        )

    def test_switch_named_lights_plural_promotes_to_light( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Bedroom Lights' ),
            EntityType.LIGHT,
        )

    def test_switch_named_lighting_promotes_to_light( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Cabinet Lighting' ),
            EntityType.LIGHT,
        )

    def test_switch_named_lamp_promotes_to_light( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Living Room Lamp' ),
            EntityType.LIGHT,
        )

    def test_switch_named_led_promotes_to_light( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Hallway LED' ),
            EntityType.LIGHT,
        )

    def test_switch_named_chandelier_promotes_to_light( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Dining Chandelier' ),
            EntityType.LIGHT,
        )

    def test_switch_named_pendant_promotes_to_light( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Foyer Pendant' ),
            EntityType.LIGHT,
        )

    def test_switch_named_floodlight_promotes_to_light( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Backyard Floodlight' ),
            EntityType.LIGHT,
        )

    # ----- outlet family -----

    def test_switch_named_smart_plug_promotes_to_outlet( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Smart Plug' ),
            EntityType.ELECTRICAL_OUTLET,
        )

    def test_switch_named_outlet_promotes_to_outlet( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Workshop Outlet' ),
            EntityType.ELECTRICAL_OUTLET,
        )

    def test_switch_named_receptacle_promotes_to_outlet( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Garage Receptacle' ),
            EntityType.ELECTRICAL_OUTLET,
        )

    # ----- fan family -----

    def test_switch_named_fan_promotes_to_ceiling_fan( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Bathroom Fan' ),
            EntityType.CEILING_FAN,
        )

    def test_switch_named_ceiling_fan_promotes_to_ceiling_fan( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Bedroom Ceiling Fan' ),
            EntityType.CEILING_FAN,
        )

    # ----- precedence -----

    def test_outlet_keyword_wins_over_light_keyword( self ):
        """A switch named with both an outlet and a light keyword
        ('Lamp Plug') resolves as ELECTRICAL_OUTLET — outlet rule
        runs first and is the more specific signal about the
        device's nature (it's a plug; the load is incidental)."""
        self.assertEqual(
            self._entity_type_for_name( 'Lamp Plug' ),
            EntityType.ELECTRICAL_OUTLET,
        )

    def test_fan_keyword_wins_over_light_keyword( self ):
        """'Ceiling Fan Light' matches both fan and light keywords;
        fan rule fires first. Imperfect for combination switches
        controlling both, but the operator can edit (and a single
        switch controlling both fan and light is uncommon — usually
        they're separate switches with separate names)."""
        self.assertEqual(
            self._entity_type_for_name( 'Ceiling Fan Light' ),
            EntityType.CEILING_FAN,
        )

    # ----- false-positive guards -----

    def test_switch_named_smart_relay_falls_through_to_on_off_switch( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Smart Relay' ),
            EntityType.ON_OFF_SWITCH,
        )

    def test_switch_with_substring_lighthouse_does_not_match( self ):
        """Word-boundary regex prevents 'Lighthouse Decor' from
        matching the 'light' keyword via substring."""
        self.assertEqual(
            self._entity_type_for_name( 'Lighthouse Decor' ),
            EntityType.ON_OFF_SWITCH,
        )

    def test_switch_with_substring_lightning_does_not_match( self ):
        self.assertEqual(
            self._entity_type_for_name( 'Lightning Sensor' ),
            EntityType.ON_OFF_SWITCH,
        )

    def test_outlet_device_class_still_wins_over_name_heuristic( self ):
        """A switch.x with device_class=outlet is an outlet
        regardless of its friendly name; outlet device-class
        check fires before the name-inference dispatch."""
        device = _make_device(
            entity_id = 'switch.outlet_a',
            friendly_name = 'Lamp Outlet',
            device_class = HassApi.OUTLET_DEVICE_CLASS,
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.ELECTRICAL_OUTLET,
        )
