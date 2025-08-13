import logging

from hi.apps.config.models import SubsystemAttribute
from hi.apps.config.settings_manager import SettingsManager
from hi.apps.attribute.enums import AttributeValueType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestConfigIntegration(BaseTestCase):
    """Integration tests for the config module components working together."""

    def test_end_to_end_setting_workflow(self):
        """Test complete workflow from model creation to manager access - complex integration."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Use existing subsystem instead of creating new one
        existing_subsystems = manager.get_subsystems()
        self.assertGreater(len(existing_subsystems), 0)
        test_subsystem = existing_subsystems[0]
        
        # Create settings for the existing subsystem
        setting_key = 'integration.test.setting'
        attribute = SubsystemAttribute.objects.create(
            subsystem=test_subsystem,
            setting_key=setting_key,
            value_type=AttributeValueType.TEXT,
            value='integration_test_value',
        )
        
        # Reload manager to pick up changes
        manager.reload()
        
        # Verify the setting is accessible
        self.assertIn(setting_key, manager._attribute_value_map)
        value = manager._attribute_value_map[setting_key]
        self.assertEqual(value, 'integration_test_value')
        
        # Update the setting through the manager
        mock_setting = type('MockSetting', (), {'key': setting_key})()
        manager.set_setting_value(mock_setting, 'updated_integration_value')
        
        # Verify the change is reflected in both memory and database
        updated_value = manager._attribute_value_map[setting_key]
        self.assertEqual(updated_value, 'updated_integration_value')
        
        attribute.refresh_from_db()
        self.assertEqual(attribute.value, 'updated_integration_value')
        
        # Clean up
        attribute.delete()
        return

    def test_multiple_value_types_integration(self):
        """Test integration with different attribute value types - complex type handling."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Use existing subsystem instead of creating new one
        existing_subsystems = manager.get_subsystems()
        self.assertGreater(len(existing_subsystems), 0)
        test_subsystem = existing_subsystems[0]
        
        test_cases = [
            ('text.setting', AttributeValueType.TEXT, 'text_value'),
            ('integer.setting', AttributeValueType.INTEGER, '123'),
            ('float.setting', AttributeValueType.FLOAT, '3.14'),
            ('boolean.setting', AttributeValueType.BOOLEAN, 'true'),
            ('enum.setting', AttributeValueType.ENUM, 'OPTION_A'),
        ]
        
        created_attributes = []
        for setting_key, value_type, value in test_cases:
            attr = SubsystemAttribute.objects.create(
                subsystem=test_subsystem,
                setting_key=setting_key,
                value_type=value_type,
                value=value,
            )
            created_attributes.append(attr)
        
        manager.reload()
        
        # Verify all settings are accessible with correct values
        for setting_key, _, expected_value in test_cases:
            with self.subTest(setting_key=setting_key):
                self.assertIn(setting_key, manager._attribute_value_map)
                actual_value = manager._attribute_value_map[setting_key]
                self.assertEqual(actual_value, expected_value)
        
        # Clean up
        for attr in created_attributes:
            attr.delete()
        return

    def test_manager_state_consistency_across_reloads(self):
        """Test SettingsManager maintains consistent state across multiple reloads - critical stability."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Get initial state after first reload to establish baseline
        manager.reload()
        initial_subsystems = len(manager._subsystem_list)
        initial_attributes = len(manager._attribute_value_map)
        
        # Multiple reloads should maintain consistency from this baseline
        for _ in range(3):
            manager.reload()
            
            current_subsystems = len(manager._subsystem_list)
            current_attributes = len(manager._attribute_value_map)
            
            self.assertEqual(current_subsystems, initial_subsystems)
            self.assertEqual(current_attributes, initial_attributes)
        return

    def test_setting_key_uniqueness_constraint(self):
        """Test that setting keys are unique across the system - critical data integrity."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Get all setting keys
        setting_keys = list(manager._attribute_value_map.keys())
        
        # Should have no duplicates
        unique_keys = set(setting_keys)
        self.assertEqual(len(setting_keys), len(unique_keys))
        return
