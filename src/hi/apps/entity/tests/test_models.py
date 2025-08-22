import json
import logging
from django.db import IntegrityError

from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.entity.enums import EntityType, EntityStateType
from hi.apps.attribute.enums import AttributeValueType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntity(BaseTestCase):

    def test_integration_key_enforces_unique_entity_identification(self):
        """Test integration key uniqueness - critical for data integrity."""
        # Create first entity with unique integration key
        first_entity = Entity.objects.create(
            name='First Entity',
            entity_type_str='LIGHT',
            integration_id='unique_id_001',
            integration_name='home_assistant',
        )
        
        # Different integration_id should work fine
        second_entity = Entity.objects.create(
            name='Second Entity',
            entity_type_str='CAMERA',
            integration_id='unique_id_002',  # Different ID
            integration_name='home_assistant',  # Same integration
        )
        
        # Different integration_name should work fine
        third_entity = Entity.objects.create(
            name='Third Entity',
            entity_type_str='THERMOSTAT',
            integration_id='unique_id_001',  # Same ID as first
            integration_name='nest_integration',  # Different integration
        )
        
        # Verify all entities were created successfully
        self.assertEqual(Entity.objects.count(), 3)
        self.assertNotEqual(first_entity.id, second_entity.id)
        self.assertNotEqual(first_entity.id, third_entity.id)
        
        # Verify constraint prevents duplicate integration keys
        try:
            Entity.objects.create(
                name='Duplicate Entity',
                entity_type_str='MOTOR',
                integration_id='unique_id_001',  # Same as first
                integration_name='home_assistant',  # Same as first
            )
            self.fail("Expected IntegrityError for duplicate integration key")
        except IntegrityError:
            pass  # Expected behavior
        
        return

    def test_entity_type_property_conversion(self):
        """Test entity_type property enum conversion logic - custom business logic."""
        entity = Entity.objects.create(
            name='Test Device',
            entity_type_str='LIGHT',
            integration_id='test_device_001',
            integration_name='test_integration',
        )
        
        # Test getter converts string to enum
        self.assertEqual(entity.entity_type, EntityType.LIGHT)
        
        # Test setter converts enum to string (lowercase)
        entity.entity_type = EntityType.CAMERA
        self.assertEqual(entity.entity_type_str, 'camera')
        self.assertEqual(entity.entity_type, EntityType.CAMERA)
        return

    def test_entity_type_property_handles_unknown_types_gracefully(self):
        """Test entity_type property with unknown type - should provide fallback behavior."""
        entity = Entity.objects.create(
            name='Future Device',
            entity_type_str='FUTURE_DEVICE_TYPE',  # Unknown type
            integration_id='future_device_001',
            integration_name='test_integration',
        )
        
        # Should handle unknown type gracefully without raising exception
        entity_type = entity.entity_type
        self.assertIsNotNone(entity_type)
        
        # Verify the fallback mechanism provides a usable value
        # The actual fallback behavior depends on from_name_safe implementation
        self.assertTrue(hasattr(entity_type, 'label') or hasattr(entity_type, 'name'))
        
        # String representation should still work
        str_representation = str(entity)
        self.assertIn('Future Device', str_representation)
        self.assertIn('FUTURE_DEVICE_TYPE', str_representation)
        
        return

    def test_get_attribute_map_logic(self):
        """Test get_attribute_map business logic - custom method prone to bugs."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='OTHER',
            integration_id='test_entity_001',
            integration_name='test_integration',
        )
        
        # Create attributes
        attr1 = EntityAttribute.objects.create(
            entity=entity,
            name='config_setting',
            value_type=AttributeValueType.TEXT,
            value='config_value',
        )
        
        attr2 = EntityAttribute.objects.create(
            entity=entity,
            name='documentation',
            value_type=AttributeValueType.TEXT,
            value='User manual link',
        )
        
        # Test mapping logic
        attribute_map = entity.get_attribute_map()
        
        self.assertEqual(len(attribute_map), 2)
        self.assertEqual(attribute_map['config_setting'], attr1)
        self.assertEqual(attribute_map['documentation'], attr2)
        
        # Test with no attributes
        empty_entity = Entity.objects.create(
            name='Empty Entity',
            entity_type_str='OTHER',
            integration_id='empty_entity_001',
            integration_name='test_integration',
        )
        
        empty_map = empty_entity.get_attribute_map()
        self.assertEqual(len(empty_map), 0)
        return

    def test_cascade_deletion_behavior(self):
        """Test cascade deletion - critical for data integrity."""
        entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='OTHER',
            integration_id='test_entity_001',
            integration_name='test_integration',
        )
        
        # Create related objects
        attribute = EntityAttribute.objects.create(
            entity=entity,
            name='test_attribute',
            value_type=AttributeValueType.TEXT,
            value='test_value',
        )
        
        state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF',
            name='Power State',
        )
        
        attribute_id = attribute.id
        state_id = state.id
        
        # Delete entity should cascade
        entity.delete()
        
        self.assertFalse(EntityAttribute.objects.filter(id=attribute_id).exists())
        self.assertFalse(EntityState.objects.filter(id=state_id).exists())
        return


class TestEntityState(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.entity = Entity.objects.create(
            name='Test Entity',
            entity_type_str='LIGHT',
            integration_id='test_entity_001',
            integration_name='test_integration',
        )
        return

    def test_entity_state_type_property_conversion(self):
        """Test entity_state_type property enum conversion - custom business logic."""
        state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF',
            name='Power State',
        )
        
        # Test getter converts string to enum
        self.assertEqual(state.entity_state_type, EntityStateType.ON_OFF)
        
        # Test setter converts enum to string (lowercase)
        state.entity_state_type = EntityStateType.TEMPERATURE
        self.assertEqual(state.entity_state_type_str, 'temperature')
        self.assertEqual(state.entity_state_type, EntityStateType.TEMPERATURE)
        return

    def test_value_range_dict_provides_flexible_state_value_handling(self):
        """Test value_range_dict JSON serialization/deserialization - flexible state value support."""
        # Test with dictionary format (key-value mapping for display)
        value_dict = {"ON": "Powered On", "OFF": "Powered Off"}
        state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF',
            name='Power State',
            value_range_str=json.dumps(value_dict),
        )
        
        # Should preserve exact mapping
        self.assertEqual(state.value_range_dict, value_dict)
        self.assertEqual(state.value_range_dict['ON'], 'Powered On')
        
        # Test with list format (should auto-create key=value mapping)
        value_list = ["LOW", "MEDIUM", "HIGH"]
        state.value_range_str = json.dumps(value_list)
        converted_dict = state.value_range_dict
        
        # Should convert list to self-mapping dictionary
        self.assertEqual(len(converted_dict), 3)
        self.assertEqual(converted_dict['LOW'], 'LOW')
        self.assertEqual(converted_dict['MEDIUM'], 'MEDIUM')
        self.assertEqual(converted_dict['HIGH'], 'HIGH')
        
        # Test setter round-trip behavior
        new_dict = {"ACTIVE": "Currently Active", "IDLE": "Currently Idle"}
        state.value_range_dict = new_dict
        
        # Should persist correctly
        saved_dict = state.value_range_dict
        self.assertEqual(saved_dict, new_dict)
        self.assertEqual(saved_dict['ACTIVE'], 'Currently Active')
        
        # Test graceful handling of malformed data
        state.value_range_str = 'not valid json at all'
        empty_dict = state.value_range_dict
        self.assertEqual(empty_dict, {})
        self.assertEqual(len(empty_dict), 0)
        
        return

    def test_entity_state_integrates_with_value_range_system(self):
        """Test entity state integration with value range system - supports UI choice generation."""
        # Create state with specific value mappings for UI
        state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF',
            name='Power State',
            value_range_str='{"ON": "Device On", "OFF": "Device Off"}',
        )
        
        # Verify value range system provides UI-friendly mappings
        choices_dict = state.value_range_dict
        self.assertEqual(len(choices_dict), 2)
        self.assertIn('ON', choices_dict)
        self.assertIn('OFF', choices_dict)
        self.assertEqual(choices_dict['ON'], 'Device On')
        self.assertEqual(choices_dict['OFF'], 'Device Off')
        
        # Test with temperature range (continuous values)
        temp_state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='TEMPERATURE',
            name='Temperature Reading',
            units='°F',
            value_range_str='null'  # Continuous values don't need fixed choices
        )
        
        # Should handle null/empty value ranges gracefully
        temp_choices = temp_state.value_range_dict
        self.assertEqual(temp_choices, {})
        self.assertEqual(temp_state.units, '°F')
        
        # Test CSS class generation for UI styling
        css_class = state.css_class
        self.assertTrue(css_class.startswith('hi-entity-state-'))
        self.assertIn(str(state.id), css_class)
        
        return

    def test_entity_attribute_map_business_logic(self):
        """Test entity attribute mapping - core functionality for configuration and metadata."""
        entity = Entity.objects.create(
            name='Smart Thermostat',
            entity_type_str='THERMOSTAT',
            integration_id='thermostat_001',
            integration_name='nest_integration',
        )
        
        # Create configuration attributes
        config_attr = EntityAttribute.objects.create(
            entity=entity,
            name='temperature_offset',
            value_type='TEXT',
            value='+2.5',
        )
        
        model_attr = EntityAttribute.objects.create(
            entity=entity,
            name='device_model',
            value_type='TEXT',
            value='Nest Learning Thermostat v3',
        )
        
        firmware_attr = EntityAttribute.objects.create(
            entity=entity,
            name='firmware_version',
            value_type='TEXT',
            value='6.2.1',
        )
        
        # Test attribute map functionality
        attribute_map = entity.get_attribute_map()
        
        # Should provide lookup by attribute name
        self.assertEqual(len(attribute_map), 3)
        self.assertEqual(attribute_map['temperature_offset'], config_attr)
        self.assertEqual(attribute_map['device_model'], model_attr)
        self.assertEqual(attribute_map['firmware_version'], firmware_attr)
        
        # Verify attribute values are accessible
        self.assertEqual(attribute_map['temperature_offset'].value, '+2.5')
        self.assertEqual(attribute_map['device_model'].value, 'Nest Learning Thermostat v3')
        
        # Test empty attribute map
        empty_entity = Entity.objects.create(
            name='Basic Switch',
            entity_type_str='ON_OFF_SWITCH',
            integration_id='switch_001',
            integration_name='test_integration',
        )
        
        empty_map = empty_entity.get_attribute_map()
        self.assertEqual(len(empty_map), 0)
        self.assertEqual(empty_map, {})
        
        return

    def test_entity_type_enum_conversion_round_trip(self):
        """Test entity type enum conversion - critical for type safety and UI display."""
        entity = Entity.objects.create(
            name='Security Camera',
            entity_type_str='CAMERA',
            integration_id='camera_001',
            integration_name='security_system',
        )
        
        # Verify string to enum conversion
        entity_type_enum = entity.entity_type
        self.assertEqual(str(entity_type_enum).lower(), 'camera')
        
        # Test enum to string conversion via setter
        from hi.apps.entity.enums import EntityType
        entity.entity_type = EntityType.MOTION_SENSOR
        
        # Should update the string field
        self.assertEqual(entity.entity_type_str, str(EntityType.MOTION_SENSOR).lower())
        
        # Save and reload to verify persistence
        entity.save()
        reloaded_entity = Entity.objects.get(id=entity.id)
        
        # Should maintain type consistency
        self.assertEqual(reloaded_entity.entity_type_str, 'motion_sensor')
        self.assertEqual(reloaded_entity.entity_type, EntityType.MOTION_SENSOR)
        
        return

    def test_cascade_deletion_maintains_data_integrity(self):
        """Test cascade deletion - ensures related data is properly cleaned up."""
        # Create entity with related objects
        entity = Entity.objects.create(
            name='Multi-State Device',
            entity_type_str='HVAC_FURNACE',
            integration_id='furnace_001',
            integration_name='hvac_system',
        )
        
        # Create related attributes
        config_attribute = EntityAttribute.objects.create(
            entity=entity,
            name='max_temperature',
            value_type='TEXT',
            value='85',
        )
        
        specs_attribute = EntityAttribute.objects.create(
            entity=entity,
            name='manufacturer',
            value_type='TEXT',
            value='Carrier',
        )
        
        # Create related states
        power_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='ON_OFF',
            name='Power State',
        )
        
        temp_state = EntityState.objects.create(
            entity=entity,
            entity_state_type_str='TEMPERATURE',
            name='Current Temperature',
            units='°F',
        )
        
        # Record IDs for verification
        entity_id = entity.id
        config_attr_id = config_attribute.id
        specs_attr_id = specs_attribute.id
        power_state_id = power_state.id
        temp_state_id = temp_state.id
        
        # Verify all objects exist
        self.assertTrue(Entity.objects.filter(id=entity_id).exists())
        self.assertTrue(EntityAttribute.objects.filter(id=config_attr_id).exists())
        self.assertTrue(EntityAttribute.objects.filter(id=specs_attr_id).exists())
        self.assertTrue(EntityState.objects.filter(id=power_state_id).exists())
        self.assertTrue(EntityState.objects.filter(id=temp_state_id).exists())
        
        # Delete entity should cascade to all related objects
        entity.delete()
        
        # Verify cascade deletion worked
        self.assertFalse(Entity.objects.filter(id=entity_id).exists())
        self.assertFalse(EntityAttribute.objects.filter(id=config_attr_id).exists())
        self.assertFalse(EntityAttribute.objects.filter(id=specs_attr_id).exists())
        self.assertFalse(EntityState.objects.filter(id=power_state_id).exists())
        self.assertFalse(EntityState.objects.filter(id=temp_state_id).exists())
        
        return
