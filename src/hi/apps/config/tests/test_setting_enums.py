import logging

from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


# Create test setting enums for testing
class TestSetting(SettingEnum):
    FIRST_SETTING = SettingDefinition(
        label='First Setting',
        description='Description for first setting',
        value_type=AttributeValueType.TEXT,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='default_first',
    )
    SECOND_SETTING = SettingDefinition(
        label='Second Setting',
        description='Description for second setting',
        value_type=AttributeValueType.INTEGER,
        value_range_str='[1, 100]',
        is_editable=False,
        is_required=False,
        initial_value='50',
    )


class AnotherTestSetting(SettingEnum):
    ANOTHER_SETTING = SettingDefinition(
        label='Another Setting',
        description='Description for another setting',
        value_type=AttributeValueType.BOOLEAN,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='true',
    )


class TestSettingDefinition(BaseTestCase):

    def test_setting_definition_creation(self):
        """Test SettingDefinition dataclass creation."""
        definition = SettingDefinition(
            label='Test Setting',
            description='A test setting for testing',
            value_type=AttributeValueType.TEXT,
            value_range_str='[a-z]+',
            is_editable=True,
            is_required=False,
            initial_value='default',
        )
        
        self.assertEqual(definition.label, 'Test Setting')
        self.assertEqual(definition.description, 'A test setting for testing')
        self.assertEqual(definition.value_type, AttributeValueType.TEXT)
        self.assertEqual(definition.value_range_str, '[a-z]+')
        self.assertTrue(definition.is_editable)
        self.assertFalse(definition.is_required)
        self.assertEqual(definition.initial_value, 'default')
        return

    def test_setting_definition_all_value_types(self):
        """Test SettingDefinition with all value types."""
        test_cases = [
            (AttributeValueType.TEXT, 'text_default'),
            (AttributeValueType.INTEGER, '42'),
            (AttributeValueType.FLOAT, '3.14'),
            (AttributeValueType.BOOLEAN, 'true'),
            (AttributeValueType.ENUM, 'OPTION_A'),
            (AttributeValueType.FILE, 'test.txt'),
            (AttributeValueType.SECRET, 'secret_value'),
        ]
        
        for value_type, initial_value in test_cases:
            with self.subTest(value_type=value_type):
                definition = SettingDefinition(
                    label=f'{value_type.name} Setting',
                    description=f'Setting for {value_type.name}',
                    value_type=value_type,
                    value_range_str='',
                    is_editable=True,
                    is_required=True,
                    initial_value=initial_value,
                )
                
                self.assertEqual(definition.value_type, value_type)
                self.assertEqual(definition.initial_value, initial_value)
                continue
        return


class TestSettingEnum(BaseTestCase):

    def test_setting_enum_creation(self):
        """Test that SettingEnum creates properly."""
        # Test enum members exist
        self.assertTrue(hasattr(TestSetting, 'FIRST_SETTING'))
        self.assertTrue(hasattr(TestSetting, 'SECOND_SETTING'))
        
        # Test values are auto-assigned
        self.assertEqual(TestSetting.FIRST_SETTING.value, 1)
        self.assertEqual(TestSetting.SECOND_SETTING.value, 2)
        return

    def test_setting_enum_definition_access(self):
        """Test accessing SettingDefinition through enum."""
        first_setting = TestSetting.FIRST_SETTING
        
        self.assertIsInstance(first_setting.definition, SettingDefinition)
        self.assertEqual(first_setting.definition.label, 'First Setting')
        self.assertEqual(first_setting.definition.description, 'Description for first setting')
        self.assertEqual(first_setting.definition.value_type, AttributeValueType.TEXT)
        self.assertTrue(first_setting.definition.is_editable)
        self.assertTrue(first_setting.definition.is_required)
        self.assertEqual(first_setting.definition.initial_value, 'default_first')
        return

    def test_setting_enum_key_property(self):
        """Test the key property generates correct keys."""
        first_key = TestSetting.FIRST_SETTING.key
        second_key = TestSetting.SECOND_SETTING.key
        
        # Keys should include module and class information
        self.assertIn('TestSetting', first_key)
        self.assertIn('FIRST_SETTING', first_key)
        self.assertIn('TestSetting', second_key)
        self.assertIn('SECOND_SETTING', second_key)
        
        # Keys should be unique
        self.assertNotEqual(first_key, second_key)
        return

    def test_setting_enum_key_format(self):
        """Test the key property format is correct."""
        key = TestSetting.FIRST_SETTING.key
        
        # Should follow format: module.class.name
        parts = key.split('.')
        self.assertGreater(len(parts), 2)  # At least module.class.name
        self.assertEqual(parts[-2], 'TestSetting')  # Class name
        self.assertEqual(parts[-1], 'FIRST_SETTING')  # Enum name
        return

    def test_multiple_setting_enums(self):
        """Test multiple SettingEnum classes work independently."""
        test_key = TestSetting.FIRST_SETTING.key
        another_key = AnotherTestSetting.ANOTHER_SETTING.key
        
        # Keys should be different
        self.assertNotEqual(test_key, another_key)
        
        # Should contain respective class names
        self.assertIn('TestSetting', test_key)
        self.assertIn('AnotherTestSetting', another_key)
        return

    def test_setting_enum_iteration(self):
        """Test iterating over SettingEnum members."""
        members = list(TestSetting)
        
        self.assertEqual(len(members), 2)
        self.assertIn(TestSetting.FIRST_SETTING, members)
        self.assertIn(TestSetting.SECOND_SETTING, members)
        return

    def test_setting_enum_membership(self):
        """Test membership testing for SettingEnum."""
        self.assertIn(TestSetting.FIRST_SETTING, TestSetting)
        self.assertIn(TestSetting.SECOND_SETTING, TestSetting)
        self.assertNotIn(AnotherTestSetting.ANOTHER_SETTING, TestSetting)
        return

    def test_setting_definition_attributes(self):
        """Test various SettingDefinition attributes through enum."""
        # Test editable setting
        editable_setting = TestSetting.FIRST_SETTING
        self.assertTrue(editable_setting.definition.is_editable)
        self.assertTrue(editable_setting.definition.is_required)
        
        # Test non-editable setting
        readonly_setting = TestSetting.SECOND_SETTING
        self.assertFalse(readonly_setting.definition.is_editable)
        self.assertFalse(readonly_setting.definition.is_required)
        return

    def test_setting_value_ranges(self):
        """Test value range specifications."""
        # Setting with no range
        first_setting = TestSetting.FIRST_SETTING
        self.assertEqual(first_setting.definition.value_range_str, '')
        
        # Setting with range
        second_setting = TestSetting.SECOND_SETTING
        self.assertEqual(second_setting.definition.value_range_str, '[1, 100]')
        return

    def test_different_value_types(self):
        """Test settings with different value types."""
        text_setting = TestSetting.FIRST_SETTING
        integer_setting = TestSetting.SECOND_SETTING
        boolean_setting = AnotherTestSetting.ANOTHER_SETTING
        
        self.assertEqual(text_setting.definition.value_type, AttributeValueType.TEXT)
        self.assertEqual(integer_setting.definition.value_type, AttributeValueType.INTEGER)
        self.assertEqual(boolean_setting.definition.value_type, AttributeValueType.BOOLEAN)
        return
