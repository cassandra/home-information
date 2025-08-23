import json
from datetime import datetime

from django.utils import timezone

from hi.apps.entity.enums import EntityStateValue
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor, SensorHistory
from hi.apps.sense.transient_models import SensorResponse
from hi.integrations.transient_models import IntegrationKey
from hi.testing.base_test_case import BaseTestCase


class TestSensorResponse(BaseTestCase):
    """Test SensorResponse transient model functionality."""

    def setUp(self):
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT'
        )
        self.entity_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF'
        )
        self.sensor = Sensor.objects.create(
            name='Test Sensor',
            entity_state=self.entity_state,
            sensor_type_str='DEFAULT',
            integration_id='sensor_123',
            integration_name='test_integration'
        )
        self.integration_key = IntegrationKey(
            integration_id='sensor_123',
            integration_name='test_integration'
        )

    def test_sensor_response_initialization_with_required_fields(self):
        """Test SensorResponse initializes correctly with required fields."""
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timestamp
        )
        
        self.assertEqual(response.integration_key, self.integration_key)
        self.assertEqual(response.value, 'test_value')
        self.assertEqual(response.timestamp, timestamp)
        self.assertIsNone(response.sensor)
        self.assertIsNone(response.detail_attrs)
        self.assertIsNone(response.source_image_url)

    def test_sensor_response_initialization_with_all_fields(self):
        """Test SensorResponse initializes correctly with all optional fields."""
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        detail_attrs = {'key1': 'value1', 'key2': 'value2'}
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timestamp,
            sensor=self.sensor,
            detail_attrs=detail_attrs,
            source_image_url='http://example.com/image.jpg'
        )
        
        self.assertEqual(response.integration_key, self.integration_key)
        self.assertEqual(response.value, 'test_value')
        self.assertEqual(response.timestamp, timestamp)
        self.assertEqual(response.sensor, self.sensor)
        self.assertEqual(response.detail_attrs, detail_attrs)
        self.assertEqual(response.source_image_url, 'http://example.com/image.jpg')

    def test_sensor_response_is_on_method_with_on_value(self):
        """Test is_on method returns True for ON entity state value."""
        response = SensorResponse(
            integration_key=self.integration_key,
            value=str(EntityStateValue.ON),
            timestamp=timezone.now()
        )
        
        self.assertTrue(response.is_on())

    def test_sensor_response_is_on_method_with_off_value(self):
        """Test is_on method returns False for non-ON values."""
        off_response = SensorResponse(
            integration_key=self.integration_key,
            value=str(EntityStateValue.OFF),
            timestamp=timezone.now()
        )
        
        other_response = SensorResponse(
            integration_key=self.integration_key,
            value='custom_value',
            timestamp=timezone.now()
        )
        
        self.assertFalse(off_response.is_on())
        self.assertFalse(other_response.is_on())

    def test_sensor_response_css_class_property_with_sensor(self):
        """Test css_class property returns entity state CSS class when sensor is set."""
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timezone.now(),
            sensor=self.sensor
        )
        
        expected_css_class = self.sensor.entity_state.css_class
        self.assertEqual(response.css_class, expected_css_class)

    def test_sensor_response_css_class_property_without_sensor(self):
        """Test css_class property returns empty string when sensor is None."""
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timezone.now()
        )
        
        self.assertEqual(response.css_class, '')

    def test_sensor_response_to_dict_conversion_complete(self):
        """Test to_dict method includes all fields correctly."""
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        detail_attrs = {'key1': 'value1', 'key2': 'value2'}
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timestamp,
            sensor=self.sensor,
            detail_attrs=detail_attrs,
            source_image_url='http://example.com/image.jpg'
        )
        
        result_dict = response.to_dict()
        
        self.assertEqual(result_dict['key'], str(self.integration_key))
        self.assertEqual(result_dict['value'], 'test_value')
        self.assertEqual(result_dict['timestamp'], timestamp.isoformat())
        self.assertEqual(result_dict['sensor_id'], self.sensor.id)
        self.assertEqual(result_dict['detail_attrs'], detail_attrs)
        self.assertEqual(result_dict['source_image_url'], 'http://example.com/image.jpg')

    def test_sensor_response_to_dict_conversion_with_none_fields(self):
        """Test to_dict method handles None fields correctly."""
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timestamp
        )
        
        result_dict = response.to_dict()
        
        self.assertEqual(result_dict['key'], str(self.integration_key))
        self.assertEqual(result_dict['value'], 'test_value')
        self.assertEqual(result_dict['timestamp'], timestamp.isoformat())
        self.assertIsNone(result_dict['sensor_id'])
        self.assertIsNone(result_dict['detail_attrs'])
        self.assertIsNone(result_dict['source_image_url'])

    def test_sensor_response_str_representation_returns_json(self):
        """Test __str__ method returns JSON representation."""
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timestamp,
            sensor=self.sensor
        )
        
        str_result = str(response)
        
        # Should be valid JSON
        parsed_dict = json.loads(str_result)
        self.assertEqual(parsed_dict['key'], str(self.integration_key))
        self.assertEqual(parsed_dict['value'], 'test_value')
        self.assertEqual(parsed_dict['sensor_id'], self.sensor.id)

    def test_sensor_response_to_sensor_history_conversion_complete(self):
        """Test to_sensor_history method creates correct SensorHistory object."""
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        detail_attrs = {'key1': 'value1', 'key2': 'value2'}
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timestamp,
            sensor=self.sensor,
            detail_attrs=detail_attrs,
            source_image_url='http://example.com/image.jpg'
        )
        
        history = response.to_sensor_history()
        
        self.assertIsInstance(history, SensorHistory)
        self.assertEqual(history.sensor, self.sensor)
        self.assertEqual(history.value, 'test_value')
        self.assertEqual(history.response_datetime, timestamp)
        self.assertEqual(history.details, json.dumps(detail_attrs))
        self.assertEqual(history.source_image_url, 'http://example.com/image.jpg')

    def test_sensor_response_to_sensor_history_value_truncation(self):
        """Test to_sensor_history truncates value to 255 characters."""
        long_value = 'x' * 300  # Exceeds 255 character limit
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value=long_value,
            timestamp=timezone.now(),
            sensor=self.sensor
        )
        
        history = response.to_sensor_history()
        
        self.assertEqual(len(history.value), 255)
        self.assertEqual(history.value, long_value[:255])

    def test_sensor_response_to_sensor_history_with_none_detail_attrs(self):
        """Test to_sensor_history handles None detail_attrs correctly."""
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timezone.now(),
            sensor=self.sensor,
            detail_attrs=None
        )
        
        history = response.to_sensor_history()
        
        self.assertIsNone(history.details)

    def test_sensor_response_from_sensor_history_conversion(self):
        """Test from_sensor_history class method recreates SensorResponse correctly."""
        # Create and save a SensorHistory object
        detail_attrs = {'key1': 'value1', 'key2': 'value2'}
        from django.utils import timezone
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        
        history = SensorHistory.objects.create(
            sensor=self.sensor,
            value='test_value',
            response_datetime=timestamp,
            details=json.dumps(detail_attrs),
            source_image_url='http://example.com/image.jpg'
        )
        
        response = SensorResponse.from_sensor_history(history)
        
        self.assertEqual(response.integration_key, self.sensor.integration_key)
        self.assertEqual(response.value, 'test_value')
        self.assertEqual(response.timestamp, timestamp)
        self.assertEqual(response.sensor, self.sensor)
        self.assertEqual(response.detail_attrs, detail_attrs)
        self.assertEqual(response.source_image_url, 'http://example.com/image.jpg')

    def test_sensor_response_from_string_deserialization(self):
        """Test from_string class method correctly deserializes JSON string."""
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        detail_attrs = {'key1': 'value1', 'key2': 'value2'}
        
        # Create original response
        original_response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timestamp,
            detail_attrs=detail_attrs,
            source_image_url='http://example.com/image.jpg'
        )
        
        # Serialize to string
        serialized_string = str(original_response)
        
        # Deserialize from string
        deserialized_response = SensorResponse.from_string(serialized_string)
        
        self.assertEqual(deserialized_response.integration_key, self.integration_key)
        self.assertEqual(deserialized_response.value, 'test_value')
        self.assertEqual(deserialized_response.timestamp, timestamp)
        self.assertEqual(deserialized_response.detail_attrs, detail_attrs)
        self.assertEqual(deserialized_response.source_image_url, 'http://example.com/image.jpg')
        # Note: sensor is not included in serialization

    def test_sensor_response_serialization_roundtrip_integrity(self):
        """Test complete serialization/deserialization roundtrip maintains data integrity."""
        timestamp = timezone.make_aware(datetime(2023, 1, 1, 12, 0, 0))
        detail_attrs = {'nested': {'key': 'value'}, 'list': [1, 2, 3]}
        
        original_response = SensorResponse(
            integration_key=self.integration_key,
            value='complex_value',
            timestamp=timestamp,
            detail_attrs=detail_attrs,
            source_image_url='http://example.com/complex/path.jpg'
        )
        
        # Full roundtrip: to_dict -> JSON -> from_string
        json_string = json.dumps(original_response.to_dict())
        parsed_dict = json.loads(json_string)
        
        # Reconstruct from parsed data
        reconstructed_response = SensorResponse(
            integration_key=IntegrationKey.from_string(parsed_dict['key']),
            value=parsed_dict['value'],
            timestamp=datetime.fromisoformat(parsed_dict['timestamp']),
            detail_attrs=parsed_dict['detail_attrs'],
            source_image_url=parsed_dict['source_image_url']
        )
        
        self.assertEqual(reconstructed_response.integration_key, original_response.integration_key)
        self.assertEqual(reconstructed_response.value, original_response.value)
        self.assertEqual(reconstructed_response.timestamp, original_response.timestamp)
        self.assertEqual(reconstructed_response.detail_attrs, original_response.detail_attrs)
        self.assertEqual(reconstructed_response.source_image_url, original_response.source_image_url)

    def test_sensor_response_handles_special_characters_in_value(self):
        """Test SensorResponse correctly handles special characters and unicode."""
        special_value = 'Test with ñ, ü, 中文, emoji 🔥, quotes "test", newlines\nand tabs\t'
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value=special_value,
            timestamp=timezone.now()
        )
        
        # Should serialize and deserialize correctly
        serialized = str(response)
        deserialized = SensorResponse.from_string(serialized)
        
        self.assertEqual(deserialized.value, special_value)

    def test_sensor_response_detail_attrs_type_preservation(self):
        """Test detail_attrs preserves data types correctly through serialization."""
        detail_attrs = {
            'string': 'text',
            'integer': 42,
            'float': 3.14,
            'boolean': True,
            'null': None,
            'list': [1, 'two', 3.0],
            'nested': {'inner': 'value'}
        }
        
        response = SensorResponse(
            integration_key=self.integration_key,
            value='test_value',
            timestamp=timezone.now(),
            sensor=self.sensor,
            detail_attrs=detail_attrs
        )
        
        # Convert to history, save to database to test JSON round-trip
        history = response.to_sensor_history()
        saved_history = SensorHistory.objects.create(
            sensor=history.sensor,
            value=history.value,
            response_datetime=history.response_datetime,
            details=history.details,
            source_image_url=history.source_image_url
        )
        
        recreated_response = SensorResponse.from_sensor_history(saved_history)
        
        self.assertEqual(recreated_response.detail_attrs, detail_attrs)
