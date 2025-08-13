import logging
from types import ModuleType
from unittest.mock import Mock

from hi.apps.config.app_settings import AppSettings, AppSettingDefinitions
from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


# Create mock module with setting enums for testing
class MockModuleSetting(SettingEnum):
    MOCK_SETTING_ONE = SettingDefinition(
        label='Mock Setting One',
        description='First mock setting',
        value_type=AttributeValueType.TEXT,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='mock_default_one',
    )
    MOCK_SETTING_TWO = SettingDefinition(
        label='Mock Setting Two',
        description='Second mock setting',
        value_type=AttributeValueType.INTEGER,
        value_range_str='[0, 100]',
        is_editable=True,
        is_required=False,
        initial_value='10',
    )


class AnotherMockSetting(SettingEnum):
    ANOTHER_MOCK_SETTING = SettingDefinition(
        label='Another Mock Setting',
        description='Another mock setting',
        value_type=AttributeValueType.BOOLEAN,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='false',
    )


def create_mock_module(label=None, *setting_classes):
    """Helper to create mock module with settings."""
    mock_module = Mock(spec=ModuleType)
    
    # Set up module attributes
    if label:
        mock_module.Label = label
    
    # Add setting classes to module
    for setting_class in setting_classes:
        setattr(mock_module, setting_class.__name__, setting_class)
    
    # Mock dir() to return setting class names
    setting_names = [cls.__name__ for cls in setting_classes]
    mock_module.__dir__ = Mock(return_value=setting_names)
    
    return mock_module


class TestAppSettingDefinitions(BaseTestCase):

    def test_app_setting_definitions_creation(self):
        """Test AppSettingDefinitions dataclass creation."""
        setting_definition_map = {
            MockModuleSetting.MOCK_SETTING_ONE.key: MockModuleSetting.MOCK_SETTING_ONE.definition,
            MockModuleSetting.MOCK_SETTING_TWO.key: MockModuleSetting.MOCK_SETTING_TWO.definition,
        }
        
        app_setting_definitions = AppSettingDefinitions(
            setting_enum_class=MockModuleSetting,
            setting_definition_map=setting_definition_map,
        )
        
        self.assertEqual(app_setting_definitions.setting_enum_class, MockModuleSetting)
        self.assertEqual(app_setting_definitions.setting_definition_map, setting_definition_map)
        return

    def test_app_setting_definitions_len(self):
        """Test AppSettingDefinitions __len__ method."""
        setting_definition_map = {
            'key1': MockModuleSetting.MOCK_SETTING_ONE.definition,
            'key2': MockModuleSetting.MOCK_SETTING_TWO.definition,
        }
        
        app_setting_definitions = AppSettingDefinitions(
            setting_enum_class=MockModuleSetting,
            setting_definition_map=setting_definition_map,
        )
        
        self.assertEqual(len(app_setting_definitions), 2)
        return


class TestAppSettings(BaseTestCase):

    def test_app_settings_with_explicit_label(self):
        """Test AppSettings with explicit label in module."""
        mock_module = create_mock_module('Custom Label', MockModuleSetting)
        
        app_settings = AppSettings(
            app_name='test.app.name',
            app_module=mock_module,
        )
        
        self.assertEqual(app_settings.app_name, 'test.app.name')
        self.assertEqual(app_settings.label, 'Custom Label')
        return

    def test_app_settings_with_default_label(self):
        """Test AppSettings with default label generation."""
        mock_module = create_mock_module(None, MockModuleSetting)  # No Label attribute
        
        app_settings = AppSettings(
            app_name='test.app.weather_station',
            app_module=mock_module,
        )
        
        self.assertEqual(app_settings.app_name, 'test.app.weather_station')
        # Should humanize the last part of the app name
        self.assertEqual(app_settings.label, 'Weather Station')
        return

    def test_app_settings_with_non_string_label(self):
        """Test AppSettings when Label attribute is not a string."""
        mock_module = create_mock_module(123, MockModuleSetting)  # Non-string Label
        
        app_settings = AppSettings(
            app_name='test.app.sensor_hub',
            app_module=mock_module,
        )
        
        # Should fall back to default label generation
        self.assertEqual(app_settings.label, 'Sensor Hub')
        return

    def test_app_settings_no_setting_classes(self):
        """Test AppSettings with module containing no SettingEnum classes."""
        mock_module = create_mock_module('Empty Module')  # No setting classes
        
        app_settings = AppSettings(
            app_name='test.app.empty',
            app_module=mock_module,
        )
        
        self.assertEqual(len(app_settings), 0)
        self.assertEqual(app_settings.all_setting_definitions(), {})
        return

    def test_app_settings_single_setting_class(self):
        """Test AppSettings with single SettingEnum class."""
        mock_module = create_mock_module('Single Settings', MockModuleSetting)
        
        app_settings = AppSettings(
            app_name='test.app.single',
            app_module=mock_module,
        )
        
        self.assertEqual(len(app_settings), 1)
        
        all_definitions = app_settings.all_setting_definitions()
        self.assertEqual(len(all_definitions), 2)  # Two settings in MockModuleSetting
        
        # Check that setting keys are included
        expected_keys = [
            MockModuleSetting.MOCK_SETTING_ONE.key,
            MockModuleSetting.MOCK_SETTING_TWO.key,
        ]
        for key in expected_keys:
            self.assertIn(key, all_definitions)
        return

    def test_app_settings_multiple_setting_classes(self):
        """Test AppSettings with multiple SettingEnum classes."""
        mock_module = create_mock_module('Multiple Settings', MockModuleSetting, AnotherMockSetting)
        
        app_settings = AppSettings(
            app_name='test.app.multiple',
            app_module=mock_module,
        )
        
        self.assertEqual(len(app_settings), 2)  # Two setting classes
        
        all_definitions = app_settings.all_setting_definitions()
        self.assertEqual(len(all_definitions), 3)  # Total of 3 settings across both classes
        
        # Check settings from first class
        self.assertIn(MockModuleSetting.MOCK_SETTING_ONE.key, all_definitions)
        self.assertIn(MockModuleSetting.MOCK_SETTING_TWO.key, all_definitions)
        
        # Check setting from second class
        self.assertIn(AnotherMockSetting.ANOTHER_MOCK_SETTING.key, all_definitions)
        return

    def test_app_settings_ignores_non_setting_classes(self):
        """Test that AppSettings ignores non-SettingEnum classes."""
        mock_module = create_mock_module('Mixed Module', MockModuleSetting)
        
        # Add non-SettingEnum classes that should be ignored
        class NotASettingEnum:
            pass
        
        setattr(mock_module, 'NotASettingEnum', NotASettingEnum)
        setattr(mock_module, 'some_function', lambda: None)
        setattr(mock_module, 'SOME_CONSTANT', 'value')
        
        # Update mock dir to include these
        mock_module.__dir__ = Mock(return_value=[
            'MockModuleSetting', 'NotASettingEnum', 'some_function', 'SOME_CONSTANT'
        ])
        
        app_settings = AppSettings(
            app_name='test.app.mixed',
            app_module=mock_module,
        )
        
        # Should only find the one SettingEnum class
        self.assertEqual(len(app_settings), 1)
        
        all_definitions = app_settings.all_setting_definitions()
        self.assertEqual(len(all_definitions), 2)  # Only MockModuleSetting's 2 settings
        return

    def test_app_settings_definition_properties(self):
        """Test that setting definitions are properly extracted."""
        mock_module = create_mock_module('Test Module', MockModuleSetting)
        
        app_settings = AppSettings(
            app_name='test.app.props',
            app_module=mock_module,
        )
        
        all_definitions = app_settings.all_setting_definitions()
        
        # Check first setting definition
        setting_one_def = all_definitions[MockModuleSetting.MOCK_SETTING_ONE.key]
        self.assertEqual(setting_one_def.label, 'Mock Setting One')
        self.assertEqual(setting_one_def.description, 'First mock setting')
        self.assertEqual(setting_one_def.value_type, AttributeValueType.TEXT)
        self.assertTrue(setting_one_def.is_editable)
        self.assertTrue(setting_one_def.is_required)
        self.assertEqual(setting_one_def.initial_value, 'mock_default_one')
        
        # Check second setting definition
        setting_two_def = all_definitions[MockModuleSetting.MOCK_SETTING_TWO.key]
        self.assertEqual(setting_two_def.label, 'Mock Setting Two')
        self.assertEqual(setting_two_def.description, 'Second mock setting')
        self.assertEqual(setting_two_def.value_type, AttributeValueType.INTEGER)
        self.assertEqual(setting_two_def.value_range_str, '[0, 100]')
        self.assertTrue(setting_two_def.is_editable)
        self.assertFalse(setting_two_def.is_required)
        self.assertEqual(setting_two_def.initial_value, '10')
        return

    def test_app_settings_len(self):
        """Test AppSettings __len__ method."""
        # Empty module
        empty_module = create_mock_module('Empty')
        empty_app_settings = AppSettings('test.empty', empty_module)
        self.assertEqual(len(empty_app_settings), 0)
        
        # Module with one setting class
        single_module = create_mock_module('Single', MockModuleSetting)
        single_app_settings = AppSettings('test.single', single_module)
        self.assertEqual(len(single_app_settings), 1)
        
        # Module with multiple setting classes
        multi_module = create_mock_module('Multi', MockModuleSetting, AnotherMockSetting)
        multi_app_settings = AppSettings('test.multi', multi_module)
        self.assertEqual(len(multi_app_settings), 2)
        return

    def test_app_settings_properties(self):
        """Test AppSettings property accessors."""
        mock_module = create_mock_module('Test Properties', MockModuleSetting)
        
        app_settings = AppSettings(
            app_name='test.app.properties',
            app_module=mock_module,
        )
        
        self.assertEqual(app_settings.app_name, 'test.app.properties')
        self.assertEqual(app_settings.label, 'Test Properties')
        return