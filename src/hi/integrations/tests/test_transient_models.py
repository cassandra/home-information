"""
Unit tests for transient models (dataclasses and key parsing logic).
"""

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType

from hi.integrations.transient_models import (
    IntegrationKey, 
    IntegrationDetails, 
    IntegrationControlResult,
    IntegrationMetaData
)
from hi.integrations.enums import IntegrationAttributeType


class MockIntegrationAttributeType(IntegrationAttributeType):
    """Mock integration attribute type for testing."""
    
    TEST_ATTR = ('Test Attribute', 'Test description', AttributeValueType.TEXT, {}, True, True, 'default')


class IntegrationKeyTestCase(TestCase):
    """Test cases for IntegrationKey dataclass functionality."""

    def test_integration_key_initialization(self):
        """Test IntegrationKey initialization and basic properties."""
        key = IntegrationKey(
            integration_id='TestIntegration',
            integration_name='DeviceName'
        )
        
        # Test that values are lowercased during initialization
        self.assertEqual(key.integration_id, 'testintegration')
        self.assertEqual(key.integration_name, 'devicename')

    def test_integration_key_post_init_lowercasing(self):
        """Test that __post_init__ properly lowercases values."""
        # Test with mixed case
        key = IntegrationKey('MixedCase_Integration', 'Mixed_Device_NAME')
        
        self.assertEqual(key.integration_id, 'mixedcase_integration')
        self.assertEqual(key.integration_name, 'mixed_device_name')
        
        # Test with already lowercase
        key2 = IntegrationKey('lowercase', 'device')
        self.assertEqual(key2.integration_id, 'lowercase')
        self.assertEqual(key2.integration_name, 'device')
        
        # Test with uppercase
        key3 = IntegrationKey('UPPERCASE', 'DEVICE')
        self.assertEqual(key3.integration_id, 'uppercase')
        self.assertEqual(key3.integration_name, 'device')

    def test_integration_key_str_representation(self):
        """Test __str__ method returns integration_key_str."""
        key = IntegrationKey('test_integration', 'device_1')
        
        expected_str = 'test_integration.device_1'
        self.assertEqual(str(key), expected_str)
        self.assertEqual(str(key), key.integration_key_str)

    def test_integration_key_str_property(self):
        """Test integration_key_str property format."""
        key = IntegrationKey('home_assistant', 'light_bedroom')
        
        expected = 'home_assistant.light_bedroom'
        self.assertEqual(key.integration_key_str, expected)
        
        # Test with special characters (should be preserved after lowercasing)
        key2 = IntegrationKey('integration_with_underscores', 'device-with-dashes')
        expected2 = 'integration_with_underscores.device-with-dashes'
        self.assertEqual(key2.integration_key_str, expected2)

    def test_integration_key_equality(self):
        """Test __eq__ method for IntegrationKey comparison."""
        key1 = IntegrationKey('test_integration', 'device_1')
        key2 = IntegrationKey('test_integration', 'device_1')
        key3 = IntegrationKey('test_integration', 'device_2')
        key4 = IntegrationKey('other_integration', 'device_1')
        
        # Test equality
        self.assertEqual(key1, key2)
        self.assertTrue(key1 == key2)
        
        # Test inequality - different device name
        self.assertNotEqual(key1, key3)
        self.assertFalse(key1 == key3)
        
        # Test inequality - different integration id
        self.assertNotEqual(key1, key4)
        self.assertFalse(key1 == key4)
        
        # Test equality with different case (should be equal due to lowercasing)
        key_upper = IntegrationKey('TEST_INTEGRATION', 'DEVICE_1')
        self.assertEqual(key1, key_upper)

    def test_integration_key_equality_with_non_integration_key(self):
        """Test __eq__ method with non-IntegrationKey objects."""
        key = IntegrationKey('test_integration', 'device_1')
        
        # Test comparison with string
        self.assertNotEqual(key, 'test_integration.device_1')
        self.assertFalse(key == 'test_integration.device_1')
        
        # Test comparison with None
        self.assertNotEqual(key, None)
        self.assertFalse(key is None)
        
        # Test comparison with other object types
        self.assertNotEqual(key, 123)
        self.assertNotEqual(key, {'integration_id': 'test', 'integration_name': 'device'})

    def test_integration_key_hash(self):
        """Test __hash__ method for use in sets and dictionaries."""
        key1 = IntegrationKey('test_integration', 'device_1')
        key2 = IntegrationKey('test_integration', 'device_1')
        key3 = IntegrationKey('test_integration', 'device_2')
        
        # Equal objects should have equal hashes
        self.assertEqual(hash(key1), hash(key2))
        
        # Different objects should typically have different hashes
        self.assertNotEqual(hash(key1), hash(key3))
        
        # Test that keys can be used in sets
        key_set = {key1, key2, key3}
        self.assertEqual(len(key_set), 2)  # key1 and key2 are equal
        
        # Test that keys can be used as dictionary keys
        key_dict = {key1: 'value1', key3: 'value3'}
        self.assertEqual(len(key_dict), 2)
        self.assertEqual(key_dict[key2], 'value1')  # key2 equals key1

    def test_integration_key_hash_consistency_with_equality(self):
        """Test that hash is consistent with equality across case variations."""
        key_lower = IntegrationKey('test_integration', 'device_1')
        key_upper = IntegrationKey('TEST_INTEGRATION', 'DEVICE_1')
        key_mixed = IntegrationKey('Test_Integration', 'Device_1')
        
        # All should be equal due to lowercasing
        self.assertEqual(key_lower, key_upper)
        self.assertEqual(key_lower, key_mixed)
        self.assertEqual(key_upper, key_mixed)
        
        # All should have the same hash
        self.assertEqual(hash(key_lower), hash(key_upper))
        self.assertEqual(hash(key_lower), hash(key_mixed))
        self.assertEqual(hash(key_upper), hash(key_mixed))

    def test_integration_key_from_string_method(self):
        """Test from_string class method for parsing string representations."""
        # Test basic parsing
        key_str = 'home_assistant.light_bedroom'
        key = IntegrationKey.from_string(key_str)
        
        self.assertEqual(key.integration_id, 'home_assistant')
        self.assertEqual(key.integration_name, 'light_bedroom')
        
        # Test with complex names containing dots
        complex_str = 'complex_integration.device.with.multiple.dots'
        complex_key = IntegrationKey.from_string(complex_str)
        
        self.assertEqual(complex_key.integration_id, 'complex_integration')
        self.assertEqual(complex_key.integration_name, 'device.with.multiple.dots')
        
        # Test round-trip consistency
        original_key = IntegrationKey('test_integration', 'device_name')
        parsed_key = IntegrationKey.from_string(str(original_key))
        
        self.assertEqual(original_key, parsed_key)

    def test_integration_key_from_string_edge_cases(self):
        """Test from_string method with edge cases."""
        # Test with minimal dot case
        minimal_str = 'a.b'
        minimal_key = IntegrationKey.from_string(minimal_str)
        
        self.assertEqual(minimal_key.integration_id, 'a')
        self.assertEqual(minimal_key.integration_name, 'b')
        
        # Test with empty parts
        empty_integration = '.device_name'
        empty_key = IntegrationKey.from_string(empty_integration)
        
        self.assertEqual(empty_key.integration_id, '')
        self.assertEqual(empty_key.integration_name, 'device_name')
        
        # Test with special characters after split
        special_str = 'integration_id.device-name_with_special_chars'
        special_key = IntegrationKey.from_string(special_str)
        
        self.assertEqual(special_key.integration_id, 'integration_id')
        self.assertEqual(special_key.integration_name, 'device-name_with_special_chars')

    def test_integration_key_from_string_invalid_format(self):
        """Test from_string method error handling with invalid formats."""
        # Test string without dot
        with self.assertRaises(ValueError):
            IntegrationKey.from_string('no_dot_in_string')
        
        # Test empty string
        with self.assertRaises(ValueError):
            IntegrationKey.from_string('')
        
        # Test None input
        with self.assertRaises(AttributeError):
            IntegrationKey.from_string(None)


class IntegrationDetailsTestCase(TestCase):
    """Test cases for IntegrationDetails dataclass functionality."""

    def test_integration_details_initialization(self):
        """Test IntegrationDetails initialization with key and payload."""
        key = IntegrationKey('test_integration', 'device_1')
        payload = {'device_type': 'light', 'capabilities': ['brightness', 'color']}
        
        details = IntegrationDetails(key=key, payload=payload)
        
        self.assertEqual(details.key, key)
        self.assertEqual(details.payload, payload)

    def test_integration_details_with_none_payload(self):
        """Test IntegrationDetails with None payload (default)."""
        key = IntegrationKey('test_integration', 'device_1')
        
        # Test default None payload
        details = IntegrationDetails(key=key)
        
        self.assertEqual(details.key, key)
        self.assertIsNone(details.payload)
        
        # Test explicit None payload
        details_explicit = IntegrationDetails(key=key, payload=None)
        
        self.assertEqual(details_explicit.key, key)
        self.assertIsNone(details_explicit.payload)

    def test_integration_details_with_empty_payload(self):
        """Test IntegrationDetails with empty dictionary payload."""
        key = IntegrationKey('test_integration', 'device_1')
        empty_payload = {}
        
        details = IntegrationDetails(key=key, payload=empty_payload)
        
        self.assertEqual(details.key, key)
        self.assertEqual(details.payload, {})
        self.assertIsInstance(details.payload, dict)

    def test_integration_details_with_complex_payload(self):
        """Test IntegrationDetails with complex nested payload."""
        key = IntegrationKey('home_assistant', 'climate_thermostat')
        complex_payload = {
            'device_info': {
                'manufacturer': 'Nest',
                'model': 'Learning Thermostat',
                'sw_version': '5.9.3'
            },
            'capabilities': {
                'temperature': {'min': 50, 'max': 90, 'step': 1},
                'humidity': {'readable': True, 'writable': False}
            },
            'state': {
                'current_temperature': 72,
                'target_temperature': 68,
                'hvac_mode': 'heat'
            }
        }
        
        details = IntegrationDetails(key=key, payload=complex_payload)
        
        self.assertEqual(details.key, key)
        self.assertEqual(details.payload, complex_payload)
        
        # Test that payload is properly preserved
        self.assertEqual(details.payload['device_info']['manufacturer'], 'Nest')
        self.assertEqual(details.payload['capabilities']['temperature']['max'], 90)

    def test_integration_details_dataclass_behavior(self):
        """Test that IntegrationDetails behaves as expected dataclass."""
        key1 = IntegrationKey('test_integration', 'device_1')
        key2 = IntegrationKey('test_integration', 'device_1')
        payload = {'test': 'value'}
        
        details1 = IntegrationDetails(key=key1, payload=payload)
        details2 = IntegrationDetails(key=key2, payload=payload)
        
        # Test equality (should be equal with same content)
        self.assertEqual(details1, details2)
        
        # Test with different payloads
        details3 = IntegrationDetails(key=key1, payload={'different': 'value'})
        self.assertNotEqual(details1, details3)
        
        # Test with different keys
        key3 = IntegrationKey('other_integration', 'device_1')
        details4 = IntegrationDetails(key=key3, payload=payload)
        self.assertNotEqual(details1, details4)


class IntegrationControlResultTestCase(TestCase):
    """Test cases for IntegrationControlResult dataclass functionality."""

    def test_integration_control_result_initialization(self):
        """Test IntegrationControlResult initialization."""
        result = IntegrationControlResult(
            new_value='on',
            error_list=['Connection failed', 'Invalid state']
        )
        
        self.assertEqual(result.new_value, 'on')
        self.assertEqual(result.error_list, ['Connection failed', 'Invalid state'])

    def test_integration_control_result_has_errors_property(self):
        """Test has_errors property logic."""
        # Test with errors
        result_with_errors = IntegrationControlResult(
            new_value='off',
            error_list=['Network timeout', 'Device not found']
        )
        
        self.assertTrue(result_with_errors.has_errors)
        
        # Test with empty error list
        result_no_errors = IntegrationControlResult(
            new_value='on',
            error_list=[]
        )
        
        self.assertFalse(result_no_errors.has_errors)
        
        # Test with None error list (if that's possible)
        try:
            result_none_errors = IntegrationControlResult(
                new_value='on',
                error_list=None
            )
            # This would fail the bool() conversion, testing robustness
            _ = result_none_errors.has_errors
        except TypeError:
            # Expected if bool(None) is called
            pass

    def test_integration_control_result_has_errors_edge_cases(self):
        """Test has_errors property with edge cases."""
        # Test with single error
        result_single = IntegrationControlResult(
            new_value='dimmed',
            error_list=['Brightness out of range']
        )
        
        self.assertTrue(result_single.has_errors)
        
        # Test with empty strings in error list (should still count as having errors)
        result_empty_strings = IntegrationControlResult(
            new_value='unknown',
            error_list=['', '   ', 'Real error']
        )
        
        self.assertTrue(result_empty_strings.has_errors)
        
        # Test with falsy but non-empty error list
        result_falsy = IntegrationControlResult(
            new_value='state',
            error_list=[None, False, 0]  # Falsy values but list is not empty
        )
        
        self.assertTrue(result_falsy.has_errors)  # List is not empty, so has_errors = True

    def test_integration_control_result_with_complex_values(self):
        """Test IntegrationControlResult with complex new_value and detailed errors."""
        # Test with JSON-like new value
        complex_value = '{"brightness": 75, "color": {"r": 255, "g": 0, "b": 0}}'
        detailed_errors = [
            'Color temperature not supported by device',
            'Brightness adjustment failed: hardware limitation',
            'State change timeout after 30 seconds'
        ]
        
        result = IntegrationControlResult(
            new_value=complex_value,
            error_list=detailed_errors
        )
        
        self.assertEqual(result.new_value, complex_value)
        self.assertEqual(len(result.error_list), 3)
        self.assertTrue(result.has_errors)
        self.assertIn('hardware limitation', result.error_list[1])


class IntegrationMetaDataTestCase(TestCase):
    """Test cases for IntegrationMetaData dataclass functionality."""

    def test_integration_metadata_initialization(self):
        """Test IntegrationMetaData initialization with all required fields."""
        metadata = IntegrationMetaData(
            integration_id='test_integration',
            label='Test Integration Service',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        self.assertEqual(metadata.integration_id, 'test_integration')
        self.assertEqual(metadata.label, 'Test Integration Service')
        self.assertEqual(metadata.attribute_type, MockIntegrationAttributeType)
        self.assertTrue(metadata.allow_entity_deletion)

    def test_integration_metadata_with_deletion_disabled(self):
        """Test IntegrationMetaData with entity deletion disabled."""
        metadata = IntegrationMetaData(
            integration_id='readonly_integration',
            label='Read-Only Integration',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=False
        )
        
        self.assertFalse(metadata.allow_entity_deletion)
        self.assertEqual(metadata.integration_id, 'readonly_integration')

    def test_integration_metadata_dataclass_behavior(self):
        """Test IntegrationMetaData dataclass equality and representation."""
        metadata1 = IntegrationMetaData(
            integration_id='test_id',
            label='Test Label',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        metadata2 = IntegrationMetaData(
            integration_id='test_id',
            label='Test Label',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        # Test equality
        self.assertEqual(metadata1, metadata2)
        
        # Test inequality with different values
        metadata3 = IntegrationMetaData(
            integration_id='different_id',
            label='Test Label',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        self.assertNotEqual(metadata1, metadata3)

    def test_integration_metadata_with_different_attribute_types(self):
        """Test IntegrationMetaData with different attribute type enums."""
        # This tests that the attribute_type field can hold different enum classes
        
        class AlternativeAttributeType(IntegrationAttributeType):
            ALT_ATTR = ('Alternative', 'Alt description', AttributeValueType.BOOLEAN, {}, False, False, 'false')
        
        metadata1 = IntegrationMetaData(
            integration_id='test_1',
            label='Test 1',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        metadata2 = IntegrationMetaData(
            integration_id='test_2',
            label='Test 2',
            attribute_type=AlternativeAttributeType,
            allow_entity_deletion=True
        )
        
        # Test that different attribute types work
        self.assertEqual(metadata1.attribute_type, MockIntegrationAttributeType)
        self.assertEqual(metadata2.attribute_type, AlternativeAttributeType)
        self.assertNotEqual(metadata1.attribute_type, metadata2.attribute_type)

    def test_integration_metadata_field_types(self):
        """Test that IntegrationMetaData enforces expected field types."""
        metadata = IntegrationMetaData(
            integration_id='type_test',
            label='Type Test Integration',
            attribute_type=MockIntegrationAttributeType,
            allow_entity_deletion=True
        )
        
        # Test field types
        self.assertIsInstance(metadata.integration_id, str)
        self.assertIsInstance(metadata.label, str)
        self.assertIsInstance(metadata.allow_entity_deletion, bool)
        
        # Test that attribute_type is a class (IntegrationAttributeType subclass)
        self.assertTrue(hasattr(metadata.attribute_type, '__bases__'))
        self.assertIn(IntegrationAttributeType, metadata.attribute_type.__bases__)
