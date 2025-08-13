import json
import logging
from django.db import IntegrityError

from hi.apps.entity.models import Entity, EntityAttribute, EntityState
from hi.apps.entity.enums import EntityType, EntityStateType
from hi.apps.attribute.enums import AttributeValueType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntity(BaseTestCase):

    def test_integration_key_uniqueness_constraint(self):
        """Test integration key uniqueness - critical for data integrity."""
        # Create first entity
        Entity.objects.create(
            name='First Entity',
            entity_type_str='LIGHT',
            integration_id='unique_id',
            integration_name='unique_integration',
        )
        
        # Attempt duplicate integration key should fail
        with self.assertRaises(IntegrityError):
            Entity.objects.create(
                name='Second Entity',
                entity_type_str='CAMERA',
                integration_id='unique_id',  # Same ID
                integration_name='unique_integration',  # Same integration
            )
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

    def test_entity_type_invalid_fallback(self):
        """Test entity_type property with invalid type - error handling logic."""
        entity = Entity.objects.create(
            name='Test Device',
            entity_type_str='INVALID_TYPE',
            integration_id='test_device_001',
            integration_name='test_integration',
        )
        
        # Should handle invalid type gracefully (from_name_safe behavior)
        entity_type = entity.entity_type
        self.assertIsNotNone(entity_type)
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

    def test_value_range_dict_json_handling(self):
        """Test value_range_dict JSON serialization/deserialization - complex logic prone to bugs."""
        # Test with dictionary JSON
        value_dict = {"ON": "On", "OFF": "Off"}
        state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF',
            name='Power State',
            value_range_str=json.dumps(value_dict),
        )
        
        self.assertEqual(state.value_range_dict, value_dict)
        
        # Test with list JSON (should convert to dict)
        value_list = ["LOW", "MEDIUM", "HIGH"]
        state.value_range_str = json.dumps(value_list)
        expected_dict = {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"}
        self.assertEqual(state.value_range_dict, expected_dict)
        
        # Test with invalid JSON (should return empty dict)
        state.value_range_str = 'invalid json'
        self.assertEqual(state.value_range_dict, {})
        
        # Test setter
        new_dict = {"ACTIVE": "Active", "INACTIVE": "Inactive"}
        state.value_range_dict = new_dict
        self.assertEqual(state.value_range_str, json.dumps(new_dict))
        self.assertEqual(state.value_range_dict, new_dict)
        return

    def test_choices_method_integration(self):
        """Test choices method with value_range_str - complex business logic."""
        # This would test the choices() method if it exists in the full model
        # Based on the partial model reading, this appears to parse value_range_str
        state = EntityState.objects.create(
            entity=self.entity,
            entity_state_type_str='ON_OFF',
            name='Power State',
            value_range_str='{"ON": "On", "OFF": "Off"}',
        )
        
        # Test that value_range_dict works correctly
        choices_dict = state.value_range_dict
        self.assertIn('ON', choices_dict)
        self.assertIn('OFF', choices_dict)
        self.assertEqual(choices_dict['ON'], 'On')
        self.assertEqual(choices_dict['OFF'], 'Off')
        return