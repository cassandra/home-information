import logging

from hi.apps.sense.models import Sensor
from hi.apps.sense.enums import SensorType
from hi.apps.entity.models import Entity, EntityState
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSensor(BaseTestCase):

    def test_sensor_cascade_deletion_from_entity_state(self):
        """Test cascade deletion from entity state - critical for data integrity."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        sensor = Sensor.objects.create(
            name='Test Sensor',
            entity_state=entity_state,
            sensor_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        sensor_id = sensor.id
        
        # Delete entity state should cascade to sensor
        entity_state.delete()
        
        self.assertFalse(Sensor.objects.filter(id=sensor_id).exists())
        return

    def test_sensor_sensor_type_property_conversion(self):
        """Test sensor_type property enum conversion - custom business logic."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        sensor = Sensor.objects.create(
            name='Test Sensor',
            entity_state=entity_state,
            sensor_type_str='DEFAULT',
            integration_id='test_id',
            integration_name='test_integration'
        )
        
        # Test getter converts string to enum
        self.assertEqual(sensor.sensor_type, SensorType.DEFAULT)
        
        # Test setter converts enum to string
        sensor.sensor_type = SensorType.DEFAULT
        self.assertEqual(sensor.sensor_type_str, 'default')
        return

    def test_sensor_integration_key_inheritance(self):
        """Test Sensor integration key inheritance - critical for integration system."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='CAMERA'
        )
        entity_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF'
        )
        
        sensor = Sensor.objects.create(
            name='Test Sensor',
            entity_state=entity_state,
            sensor_type_str='DEFAULT',
            integration_id='sensor_123',
            integration_name='test_integration'
        )
        
        # Should inherit integration key fields from IntegrationKeyModel
        self.assertEqual(sensor.integration_id, 'sensor_123')
        self.assertEqual(sensor.integration_name, 'test_integration')
        return
