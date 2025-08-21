import logging

from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


# Create test setting enums for testing key generation and enum behavior
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


class NestedModuleTestSetting(SettingEnum):
    """Setting enum for testing nested module key generation."""
    NESTED_SETTING = SettingDefinition(
        label='Nested Setting',
        description='Setting in nested module context',
        value_type=AttributeValueType.TEXT,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='nested_default',
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

    def test_enum_auto_numbering_pattern(self):
        """Test that SettingEnum auto-numbers values correctly."""
        # Test enum members exist and are numbered sequentially
        self.assertTrue(hasattr(TestSetting, 'FIRST_SETTING'))
        self.assertTrue(hasattr(TestSetting, 'SECOND_SETTING'))
        
        # Test auto-assigned sequential values
        self.assertEqual(TestSetting.FIRST_SETTING.value, 1)
        self.assertEqual(TestSetting.SECOND_SETTING.value, 2)
        
        # Different enum classes should start numbering independently
        self.assertEqual(AnotherTestSetting.ANOTHER_SETTING.value, 1)
        return

    def test_definition_attachment_to_enum_members(self):
        """Test that SettingDefinitions are correctly attached to enum members."""
        first_setting = TestSetting.FIRST_SETTING
        
        # Definition should be attached and accessible
        self.assertIsInstance(first_setting.definition, SettingDefinition)
        self.assertEqual(first_setting.definition.label, 'First Setting')
        self.assertEqual(first_setting.definition.description, 'Description for first setting')
        self.assertEqual(first_setting.definition.value_type, AttributeValueType.TEXT)
        self.assertTrue(first_setting.definition.is_editable)
        self.assertTrue(first_setting.definition.is_required)
        self.assertEqual(first_setting.definition.initial_value, 'default_first')
        return

    def test_key_generation_algorithm(self):
        """Test the key generation algorithm produces correct and unique keys."""
        first_key = TestSetting.FIRST_SETTING.key
        second_key = TestSetting.SECOND_SETTING.key
        another_key = AnotherTestSetting.ANOTHER_SETTING.key
        
        # Keys should include full module path, class name, and enum name
        self.assertIn('test_setting_enums', first_key)  # Module name
        self.assertIn('TestSetting', first_key)         # Class name
        self.assertIn('FIRST_SETTING', first_key)       # Enum member name
        
        # Keys should be unique across different enum members
        self.assertNotEqual(first_key, second_key)
        self.assertNotEqual(first_key, another_key)
        
        # Keys should reflect their enum class
        self.assertIn('TestSetting', first_key)
        self.assertIn('AnotherTestSetting', another_key)
        return

    def test_key_format_consistency(self):
        """Test that all generated keys follow consistent format."""
        keys_to_test = [
            TestSetting.FIRST_SETTING.key,
            TestSetting.SECOND_SETTING.key,
            AnotherTestSetting.ANOTHER_SETTING.key,
            NestedModuleTestSetting.NESTED_SETTING.key,
        ]
        
        for key in keys_to_test:
            with self.subTest(key=key):
                # Should follow format: module.class.name
                parts = key.split('.')
                self.assertGreaterEqual(len(parts), 3)  # At least module.class.name
                
                # Last part should be enum member name
                enum_name = parts[-1]
                self.assertTrue(enum_name.isupper())  # Convention: enum names are uppercase
                
                # Second to last should be class name
                class_name = parts[-2]
                self.assertTrue(class_name[0].isupper())  # Convention: class names start with uppercase
        return

    def test_key_uniqueness_across_modules(self):
        """Test that keys are unique even across different module contexts."""
        all_keys = [
            TestSetting.FIRST_SETTING.key,
            TestSetting.SECOND_SETTING.key,
            AnotherTestSetting.ANOTHER_SETTING.key,
            NestedModuleTestSetting.NESTED_SETTING.key,
        ]
        
        # All keys should be unique
        unique_keys = set(all_keys)
        self.assertEqual(len(all_keys), len(unique_keys))
        return

    def test_enum_iteration_behavior(self):
        """Test that SettingEnum supports standard enum iteration patterns."""
        members = list(TestSetting)
        
        self.assertEqual(len(members), 2)
        self.assertIn(TestSetting.FIRST_SETTING, members)
        self.assertIn(TestSetting.SECOND_SETTING, members)
        
        # Test that iteration order is predictable (based on definition order)
        self.assertEqual(members[0], TestSetting.FIRST_SETTING)
        self.assertEqual(members[1], TestSetting.SECOND_SETTING)
        return

    def test_enum_membership_operations(self):
        """Test membership operations work correctly across enum classes."""
        # Test membership within same enum
        self.assertIn(TestSetting.FIRST_SETTING, TestSetting)
        self.assertIn(TestSetting.SECOND_SETTING, TestSetting)
        
        # Test non-membership across different enums
        self.assertNotIn(AnotherTestSetting.ANOTHER_SETTING, TestSetting)
        self.assertNotIn(TestSetting.FIRST_SETTING, AnotherTestSetting)
        return

    def test_setting_definition_attribute_accessibility(self):
        """Test that all SettingDefinition attributes are accessible through enum."""
        # Test editable setting attributes
        editable_setting = TestSetting.FIRST_SETTING
        self.assertTrue(editable_setting.definition.is_editable)
        self.assertTrue(editable_setting.definition.is_required)
        self.assertEqual(editable_setting.definition.value_range_str, '')
        
        # Test non-editable setting attributes
        readonly_setting = TestSetting.SECOND_SETTING
        self.assertFalse(readonly_setting.definition.is_editable)
        self.assertFalse(readonly_setting.definition.is_required)
        self.assertEqual(readonly_setting.definition.value_range_str, '[1, 100]')
        return

    def test_enum_value_type_preservation(self):
        """Test that value types are preserved correctly across different settings."""
        text_setting = TestSetting.FIRST_SETTING
        integer_setting = TestSetting.SECOND_SETTING
        boolean_setting = AnotherTestSetting.ANOTHER_SETTING
        
        self.assertEqual(text_setting.definition.value_type, AttributeValueType.TEXT)
        self.assertEqual(integer_setting.definition.value_type, AttributeValueType.INTEGER)
        self.assertEqual(boolean_setting.definition.value_type, AttributeValueType.BOOLEAN)
        return

    def test_enum_class_isolation(self):
        """Test that enum classes are properly isolated from each other."""
        # Each enum class should have its own members
        test_members = list(TestSetting.__members__.keys())
        another_members = list(AnotherTestSetting.__members__.keys())
        
        self.assertEqual(set(test_members), {'FIRST_SETTING', 'SECOND_SETTING'})
        self.assertEqual(set(another_members), {'ANOTHER_SETTING'})
        
        # Members should not overlap between classes
        self.assertEqual(set(test_members) & set(another_members), set())
        return
