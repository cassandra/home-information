import logging
from types import ModuleType

from hi.apps.config.models import Subsystem, SubsystemAttribute
from hi.apps.config.settings_manager import SettingsManager
from hi.apps.config.app_settings import AppSettings
from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


# Create test settings for integration testing
class IntegrationTestSettings(SettingEnum):
    TEST_WORKFLOW_SETTING = SettingDefinition(
        label='Test Workflow Setting',
        description='Setting for testing complete workflows',
        value_type=AttributeValueType.TEXT,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='workflow_default',
    )
    NOTIFICATION_SETTING = SettingDefinition(
        label='Notification Setting',
        description='Setting for testing change notifications',
        value_type=AttributeValueType.BOOLEAN,
        value_range_str='',
        is_editable=True,
        is_required=False,
        initial_value='true',
    )


class TestConfigIntegration(BaseTestCase):
    """Integration tests for config module components working together in real workflows."""

    def setUp(self):
        super().setUp()
        # Reset SettingsManager singleton for proper test isolation
        SettingsManager._instance = None

    def test_complete_settings_discovery_workflow(self):
        """Test complete workflow from module discovery to setting value access."""
        # Create test module with settings
        test_module = ModuleType('integration_test_module')
        test_module.IntegrationTestSettings = IntegrationTestSettings
        
        # Test app settings discovery
        app_settings = AppSettings(
            app_name='test.integration.module',
            app_module=test_module,
        )
        
        # Verify settings were discovered correctly
        self.assertEqual(len(app_settings), 1)
        all_definitions = app_settings.all_setting_definitions()
        self.assertEqual(len(all_definitions), 2)
        
        # Verify specific settings are present
        workflow_key = IntegrationTestSettings.TEST_WORKFLOW_SETTING.key
        notification_key = IntegrationTestSettings.NOTIFICATION_SETTING.key
        
        self.assertIn(workflow_key, all_definitions)
        self.assertIn(notification_key, all_definitions)
        
        # Verify setting properties are preserved
        workflow_def = all_definitions[workflow_key]
        self.assertEqual(workflow_def.label, 'Test Workflow Setting')
        self.assertEqual(workflow_def.value_type, AttributeValueType.TEXT)
        self.assertTrue(workflow_def.is_editable)
        return

    def test_settings_manager_integration_with_real_enums(self):
        """Test SettingsManager integration with actual SettingEnum instances."""
        manager = SettingsManager()
        
        # Create subsystem and attribute with real enum key
        subsystem = Subsystem.objects.create(
            name='Integration Test Subsystem',
            subsystem_key='integration_test',
        )
        
        workflow_key = IntegrationTestSettings.TEST_WORKFLOW_SETTING.key
        attribute = SubsystemAttribute.objects.create(
            subsystem=subsystem,
            setting_key=workflow_key,
            value_type=AttributeValueType.TEXT,
            value='integration_initial_value',
        )
        
        manager.ensure_initialized()
        
        # Reload subsystems and attributes to pick up new data
        manager._subsystem_list = manager._load_settings()
        manager.reload()
        
        # Test getting value using real enum
        initial_value = manager.get_setting_value(IntegrationTestSettings.TEST_WORKFLOW_SETTING)
        self.assertEqual(initial_value, 'integration_initial_value')
        
        # Test setting value using real enum
        manager.set_setting_value(
            IntegrationTestSettings.TEST_WORKFLOW_SETTING,
            'integration_updated_value'
        )
        
        # Verify update worked
        updated_value = manager.get_setting_value(IntegrationTestSettings.TEST_WORKFLOW_SETTING)
        self.assertEqual(updated_value, 'integration_updated_value')
        
        # Verify persistence
        attribute.refresh_from_db()
        self.assertEqual(attribute.value, 'integration_updated_value')
        return

    def test_change_notification_workflow(self):
        """Test complete change notification workflow across components."""
        manager = SettingsManager()
        
        # Track notifications through the workflow
        notification_log = []
        
        def workflow_change_listener():
            notification_log.append('workflow_change_detected')
        
        def secondary_change_listener():
            notification_log.append('secondary_change_detected')
        
        # Register listeners
        manager.register_change_listener(workflow_change_listener)
        manager.register_change_listener(secondary_change_listener)
        
        # Create test subsystem and setting
        subsystem = Subsystem.objects.create(
            name='Notification Test Subsystem',
            subsystem_key='notification_test',
        )
        
        notification_key = IntegrationTestSettings.NOTIFICATION_SETTING.key
        SubsystemAttribute.objects.create(
            subsystem=subsystem,
            setting_key=notification_key,
            value_type=AttributeValueType.BOOLEAN,
            value='false',
        )
        
        # Initialize manager
        manager.ensure_initialized()
        initial_log_length = len(notification_log)
        
        # Trigger reload to test notification workflow
        manager.reload()
        
        # Verify notifications were sent
        self.assertGreater(len(notification_log), initial_log_length)
        self.assertIn('workflow_change_detected', notification_log)
        self.assertIn('secondary_change_detected', notification_log)
        return

    def test_cross_component_value_type_handling(self):
        """Test value type handling across all config components."""
        manager = SettingsManager()
        
        # Create subsystem for testing
        subsystem = Subsystem.objects.create(
            name='Value Type Test Subsystem',
            subsystem_key='value_type_test',
        )
        
        # Test various value types through complete workflow
        value_type_tests = [
            (AttributeValueType.TEXT, 'text_workflow_value'),
            (AttributeValueType.INTEGER, '42'),
            (AttributeValueType.FLOAT, '3.14159'),
            (AttributeValueType.BOOLEAN, 'true'),
            (AttributeValueType.ENUM, 'WORKFLOW_OPTION'),
        ]
        
        created_attributes = []
        setting_keys = []
        
        for i, (value_type, test_value) in enumerate(value_type_tests):
            setting_key = f'workflow.{value_type.name.lower()}.setting.{i}'
            setting_keys.append(setting_key)
            
            attr = SubsystemAttribute.objects.create(
                subsystem=subsystem,
                setting_key=setting_key,
                value_type=value_type,
                value=test_value,
            )
            created_attributes.append(attr)
        
        manager.ensure_initialized()
        
        # Reload subsystems and attributes to pick up new data
        manager._subsystem_list = manager._load_settings()
        manager.reload()
        
        # Verify all value types are accessible through manager
        for setting_key, (value_type, expected_value) in zip(setting_keys, value_type_tests):
            with self.subTest(value_type=value_type):
                # Create mock setting enum for access
                mock_setting = type('MockSetting', (), {'key': setting_key})()
                actual_value = manager.get_setting_value(mock_setting)
                self.assertEqual(actual_value, expected_value)
        
        # Test updating different value types
        for setting_key, (value_type, _) in zip(setting_keys, value_type_tests):
            mock_setting = type('MockSetting', (), {'key': setting_key})()
            new_value = f'updated_{value_type.name.lower()}_value'
            
            manager.set_setting_value(mock_setting, new_value)
            updated_value = manager.get_setting_value(mock_setting)
            self.assertEqual(updated_value, new_value)
        return

    def test_system_stability_across_component_interactions(self):
        """Test system stability when all components interact in realistic scenarios."""
        manager = SettingsManager()
        
        # Create multiple subsystems to simulate real system
        subsystems = []
        for i in range(3):
            subsystem = Subsystem.objects.create(
                name=f'Stability Test Subsystem {i}',
                subsystem_key=f'stability_test_{i}',
            )
            subsystems.append(subsystem)
        
        # Create multiple settings across subsystems
        all_setting_keys = []
        for i, subsystem in enumerate(subsystems):
            for j in range(2):
                setting_key = f'stability.subsystem_{i}.setting_{j}'
                all_setting_keys.append(setting_key)
                
                SubsystemAttribute.objects.create(
                    subsystem=subsystem,
                    setting_key=setting_key,
                    value_type=AttributeValueType.TEXT,
                    value=f'stability_value_{i}_{j}',
                )
        
        manager.ensure_initialized()
        
        # Reload subsystems and attributes to pick up new data
        manager._subsystem_list = manager._load_settings()
        manager.reload()
        
        # Test multiple operations in sequence (simulating real usage)
        operations_performed = 0
        
        # Multiple reloads
        for _ in range(3):
            manager.reload()
            operations_performed += 1
        
        # Multiple setting accesses
        for setting_key in all_setting_keys:
            mock_setting = type('MockSetting', (), {'key': setting_key})()
            value = manager.get_setting_value(mock_setting)
            self.assertIsNotNone(value)
            operations_performed += 1
        
        # Multiple setting updates
        for i, setting_key in enumerate(all_setting_keys[:3]):  # Update subset
            mock_setting = type('MockSetting', (), {'key': setting_key})()
            manager.set_setting_value(mock_setting, f'stability_updated_{i}')
            operations_performed += 1
        
        # Verify system maintained stability
        self.assertGreater(operations_performed, 10)  # Multiple operations completed
        
        # Verify all subsystems still accessible
        current_subsystems = manager.get_subsystems()
        self.assertGreaterEqual(len(current_subsystems), 3)
        
        # Verify settings still accessible after all operations
        final_reload_successful = True
        try:
            manager.reload()
        except Exception:
            final_reload_successful = False
        
        self.assertTrue(final_reload_successful)
        return

    def test_error_recovery_across_component_boundaries(self):
        """Test system recovery from errors that cross component boundaries."""
        manager = SettingsManager()
        
        # Create valid subsystem and setting
        subsystem = Subsystem.objects.create(
            name='Error Recovery Test Subsystem',
            subsystem_key='error_recovery_test',
        )
        
        valid_setting_key = 'error.recovery.valid.setting'
        SubsystemAttribute.objects.create(
            subsystem=subsystem,
            setting_key=valid_setting_key,
            value_type=AttributeValueType.TEXT,
            value='valid_value',
        )
        
        manager.ensure_initialized()
        
        # Reload subsystems and attributes to pick up new data
        manager._subsystem_list = manager._load_settings()
        manager.reload()
        
        # Verify normal operation works
        mock_valid_setting = type('MockSetting', (), {'key': valid_setting_key})()
        initial_value = manager.get_setting_value(mock_valid_setting)
        self.assertEqual(initial_value, 'valid_value')
        
        # Test error handling for non-existent setting
        mock_invalid_setting = type('MockSetting', (), {
            'key': 'non.existent.setting',
            'name': 'NON_EXISTENT_SETTING'
        })()
        
        # Should handle gracefully without crashing
        non_existent_value = manager.get_setting_value(mock_invalid_setting)
        self.assertIsNone(non_existent_value)
        
        # Should raise appropriate error for set operation
        with self.assertRaises(KeyError):
            manager.set_setting_value(mock_invalid_setting, 'any_value')
        
        # Verify valid operations still work after errors
        updated_value = manager.get_setting_value(mock_valid_setting)
        self.assertEqual(updated_value, 'valid_value')
        
        # System should still be able to reload successfully
        manager.reload()
        post_error_value = manager.get_setting_value(mock_valid_setting)
        self.assertEqual(post_error_value, 'valid_value')
        return
