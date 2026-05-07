import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.services.hass.hass_converter import HassConverter
from hi.services.hass.hass_models import HassApi, HassDevice

logging.disable(logging.CRITICAL)


class HassDeviceToEntityTypeTests( TestCase ):
    """Pin the domain/device-class → EntityType mapping. Each branch
    is exercised with the smallest fake HassDevice that satisfies
    the predicate; a switch-domain regression where generic switches
    fell through to OTHER motivated the broader sweep."""

    @staticmethod
    def _device( domain_set = None, device_class_set = None ) -> HassDevice:
        device = Mock( spec = HassDevice )
        device.domain_set = set( domain_set or [] )
        device.device_class_set = set( device_class_set or [] )
        return device

    def test_switch_domain_maps_to_on_off_switch( self ):
        device = self._device( domain_set = { HassApi.SWITCH_DOMAIN } )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.ON_OFF_SWITCH,
        )

    def test_outlet_device_class_takes_precedence_over_switch_domain( self ):
        device = self._device(
            domain_set = { HassApi.SWITCH_DOMAIN },
            device_class_set = { HassApi.OUTLET_DEVICE_CLASS },
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.ELECTRICAL_OUTLET,
        )

    def test_lock_domain_maps_to_door_lock( self ):
        device = self._device( domain_set = { HassApi.LOCK_DOMAIN } )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.DOOR_LOCK,
        )

    def test_cover_domain_maps_to_open_close_sensor( self ):
        device = self._device( domain_set = { HassApi.COVER_DOMAIN } )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.OPEN_CLOSE_SENSOR,
        )

    def test_fan_domain_maps_to_ceiling_fan( self ):
        device = self._device( domain_set = { HassApi.FAN_DOMAIN } )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.CEILING_FAN,
        )

    def test_climate_domain_maps_to_thermostat( self ):
        device = self._device( domain_set = { HassApi.CLIMATE_DOMAIN } )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.THERMOSTAT,
        )

    def test_camera_domain_maps_to_camera( self ):
        device = self._device( domain_set = { HassApi.CAMERA_DOMAIN } )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.CAMERA,
        )

    def test_light_domain_maps_to_light( self ):
        device = self._device( domain_set = { HassApi.LIGHT_DOMAIN } )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.LIGHT,
        )

    def test_motion_device_class_maps_to_motion_sensor( self ):
        device = self._device(
            domain_set = { HassApi.BINARY_SENSOR_DOMAIN },
            device_class_set = { HassApi.MOTION_DEVICE_CLASS },
        )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.MOTION_SENSOR,
        )

    def test_unknown_domain_falls_through_to_other( self ):
        device = self._device( domain_set = { 'something_unrecognized' } )
        self.assertEqual(
            HassConverter.hass_device_to_entity_type( device ),
            EntityType.OTHER,
        )
