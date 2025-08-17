import logging
from types import ModuleType

from hi.apps.config.app_settings import AppSettings, AppSettingDefinitions
from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


# Real setting enums for testing actual module scanning
class TestModuleSetting(SettingEnum):
    TEST_SETTING_ONE = SettingDefinition(
        label='Test Setting One',
        description='First test setting',
        value_type=AttributeValueType.TEXT,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='test_default_one',
    )
    TEST_SETTING_TWO = SettingDefinition(
        label='Test Setting Two',
        description='Second test setting',
        value_type=AttributeValueType.INTEGER,
        value_range_str='[0, 100]',
        is_editable=True,
        is_required=False,
        initial_value='10',
    )


class AnotherTestSetting(SettingEnum):
    ANOTHER_TEST_SETTING = SettingDefinition(
        label='Another Test Setting',
        description='Another test setting',
        value_type=AttributeValueType.BOOLEAN,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='false',
    )


class NotASettingEnum:
    """Class that should be ignored during module scanning."""
    pass


def create_test_module(label=None, include_settings=True, include_non_settings=False):
    """Create a real module-like object for testing."""
    module = ModuleType('test_module')
    
    if label:
        module.Label = label
    
    if include_settings:
        module.TestModuleSetting = TestModuleSetting
        module.AnotherTestSetting = AnotherTestSetting
    
    if include_non_settings:
        module.NotASettingEnum = NotASettingEnum
        module.some_function = lambda: None
        module.SOME_CONSTANT = 'value'
    
    return module


class TestAppSettingDefinitions(BaseTestCase):

    def test_app_setting_definitions_creation(self):
        """Test AppSettingDefinitions dataclass creation."""
        setting_definition_map = {
            TestModuleSetting.TEST_SETTING_ONE.key: TestModuleSetting.TEST_SETTING_ONE.definition,
            TestModuleSetting.TEST_SETTING_TWO.key: TestModuleSetting.TEST_SETTING_TWO.definition,
        }
        
        app_setting_definitions = AppSettingDefinitions(
            setting_enum_class=TestModuleSetting,
            setting_definition_map=setting_definition_map,
        )
        
        self.assertEqual(app_setting_definitions.setting_enum_class, TestModuleSetting)
        self.assertEqual(app_setting_definitions.setting_definition_map, setting_definition_map)
        return

    def test_app_setting_definitions_len(self):
        """Test AppSettingDefinitions __len__ method."""
        setting_definition_map = {
            'key1': TestModuleSetting.TEST_SETTING_ONE.definition,
            'key2': TestModuleSetting.TEST_SETTING_TWO.definition,
        }
        
        app_setting_definitions = AppSettingDefinitions(
            setting_enum_class=TestModuleSetting,
            setting_definition_map=setting_definition_map,
        )
        
        self.assertEqual(len(app_setting_definitions), 2)
        return


class TestAppSettings(BaseTestCase):

    def test_module_scanning_with_explicit_label(self):
        """Test module scanning with explicit label configuration."""
        test_module = create_test_module(label='Custom Label', include_settings=True)
        
        app_settings = AppSettings(
            app_name='test.app.name',
            app_module=test_module,
        )
        
        self.assertEqual(app_settings.app_name, 'test.app.name')
        self.assertEqual(app_settings.label, 'Custom Label')
        return

    def test_module_scanning_with_default_label_generation(self):
        """Test automatic label generation from app name."""
        test_module = create_test_module(include_settings=True)  # No Label attribute
        
        app_settings = AppSettings(
            app_name='test.app.weather_station',
            app_module=test_module,
        )
        
        self.assertEqual(app_settings.app_name, 'test.app.weather_station')
        # Should humanize the last part of the app name
        self.assertEqual(app_settings.label, 'Weather Station')
        return

    def test_module_scanning_with_invalid_label(self):
        """Test fallback when Label attribute is not a string."""
        test_module = create_test_module(label=123, include_settings=True)  # Non-string Label
        
        app_settings = AppSettings(
            app_name='test.app.sensor_hub',
            app_module=test_module,
        )
        
        # Should fall back to default label generation
        self.assertEqual(app_settings.label, 'Sensor Hub')
        return

    def test_module_scanning_empty_module(self):
        """Test scanning module with no SettingEnum classes."""
        test_module = create_test_module(label='Empty Module', include_settings=False)
        
        app_settings = AppSettings(
            app_name='test.app.empty',
            app_module=test_module,
        )
        
        self.assertEqual(len(app_settings), 0)
        self.assertEqual(app_settings.all_setting_definitions(), {})
        return

    def test_module_scanning_single_setting_class(self):
        """Test scanning module with single SettingEnum class."""
        # Create module with only one setting class
        test_module = ModuleType('single_setting_module')
        test_module.TestModuleSetting = TestModuleSetting
        
        app_settings = AppSettings(
            app_name='test.app.single',
            app_module=test_module,
        )
        
        self.assertEqual(len(app_settings), 1)
        
        all_definitions = app_settings.all_setting_definitions()
        self.assertEqual(len(all_definitions), 2)  # Two settings in TestModuleSetting
        
        # Check that setting keys are included
        expected_keys = [
            TestModuleSetting.TEST_SETTING_ONE.key,
            TestModuleSetting.TEST_SETTING_TWO.key,
        ]
        for key in expected_keys:
            self.assertIn(key, all_definitions)
        return

    def test_module_scanning_multiple_setting_classes(self):
        """Test scanning module with multiple SettingEnum classes."""
        test_module = create_test_module(include_settings=True)
        
        app_settings = AppSettings(
            app_name='test.app.multiple',
            app_module=test_module,
        )
        
        self.assertEqual(len(app_settings), 2)  # Two setting classes
        
        all_definitions = app_settings.all_setting_definitions()
        self.assertEqual(len(all_definitions), 3)  # Total of 3 settings across both classes
        
        # Check settings from first class
        self.assertIn(TestModuleSetting.TEST_SETTING_ONE.key, all_definitions)
        self.assertIn(TestModuleSetting.TEST_SETTING_TWO.key, all_definitions)
        
        # Check setting from second class
        self.assertIn(AnotherTestSetting.ANOTHER_TEST_SETTING.key, all_definitions)
        return

    def test_module_scanning_ignores_non_setting_classes(self):
        """Test that module scanning correctly ignores non-SettingEnum classes."""
        test_module = create_test_module(
            include_settings=True,
            include_non_settings=True
        )
        
        app_settings = AppSettings(
            app_name='test.app.mixed',
            app_module=test_module,
        )
        
        # Should only find the SettingEnum classes
        self.assertEqual(len(app_settings), 2)
        
        all_definitions = app_settings.all_setting_definitions()
        self.assertEqual(len(all_definitions), 3)  # Only settings from SettingEnum classes
        return

    def test_setting_definition_extraction_accuracy(self):
        """Test that setting definitions are accurately extracted from enums."""
        test_module = ModuleType('test_module')
        test_module.TestModuleSetting = TestModuleSetting
        
        app_settings = AppSettings(
            app_name='test.app.props',
            app_module=test_module,
        )
        
        all_definitions = app_settings.all_setting_definitions()
        
        # Check first setting definition
        setting_one_def = all_definitions[TestModuleSetting.TEST_SETTING_ONE.key]
        self.assertEqual(setting_one_def.label, 'Test Setting One')
        self.assertEqual(setting_one_def.description, 'First test setting')
        self.assertEqual(setting_one_def.value_type, AttributeValueType.TEXT)
        self.assertTrue(setting_one_def.is_editable)
        self.assertTrue(setting_one_def.is_required)
        self.assertEqual(setting_one_def.initial_value, 'test_default_one')
        
        # Check second setting definition
        setting_two_def = all_definitions[TestModuleSetting.TEST_SETTING_TWO.key]
        self.assertEqual(setting_two_def.label, 'Test Setting Two')
        self.assertEqual(setting_two_def.description, 'Second test setting')
        self.assertEqual(setting_two_def.value_type, AttributeValueType.INTEGER)
        self.assertEqual(setting_two_def.value_range_str, '[0, 100]')
        self.assertTrue(setting_two_def.is_editable)
        self.assertFalse(setting_two_def.is_required)
        self.assertEqual(setting_two_def.initial_value, '10')
        return

    def test_app_settings_length_calculation(self):
        """Test AppSettings length reflects number of setting classes found."""
        # Empty module
        empty_module = create_test_module(include_settings=False)
        empty_app_settings = AppSettings('test.empty', empty_module)
        self.assertEqual(len(empty_app_settings), 0)
        
        # Module with one setting class
        single_module = ModuleType('single_module')
        single_module.TestModuleSetting = TestModuleSetting
        single_app_settings = AppSettings('test.single', single_module)
        self.assertEqual(len(single_app_settings), 1)
        
        # Module with multiple setting classes
        multi_module = create_test_module(include_settings=True)
        multi_app_settings = AppSettings('test.multi', multi_module)
        self.assertEqual(len(multi_app_settings), 2)
        return

    def test_app_settings_property_access(self):
        """Test AppSettings property accessors work correctly."""
        test_module = create_test_module(label='Test Properties', include_settings=True)
        
        app_settings = AppSettings(
            app_name='test.app.properties',
            app_module=test_module,
        )
        
        self.assertEqual(app_settings.app_name, 'test.app.properties')
        self.assertEqual(app_settings.label, 'Test Properties')
        return

    def test_setting_key_uniqueness_across_classes(self):
        """Test that setting keys are unique even across multiple enum classes."""
        test_module = create_test_module(include_settings=True)
        
        app_settings = AppSettings(
            app_name='test.app.uniqueness',
            app_module=test_module,
        )
        
        all_definitions = app_settings.all_setting_definitions()
        setting_keys = list(all_definitions.keys())
        
        # Should have no duplicate keys
        unique_keys = set(setting_keys)
        self.assertEqual(len(setting_keys), len(unique_keys))
        return
