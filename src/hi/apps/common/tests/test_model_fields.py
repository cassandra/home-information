"""
Tests for custom Django model fields.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

from hi.apps.common.enums import LabeledEnum
from hi.apps.common.model_fields import LabeledEnumField, NullableLabeledEnumField


class TestEnum(LabeledEnum):
    """Test enum for field testing."""
    FIRST = ('First Option', 'The first option')
    SECOND = ('Second Option', 'The second option')
    THIRD = ('Third Option', 'The third option')
    
    @classmethod
    def default(cls):
        return cls.FIRST


class TestModel(models.Model):
    """Test model for LabeledEnumField testing."""
    safe_field = LabeledEnumField(TestEnum)
    strict_field = LabeledEnumField(TestEnum, use_safe_conversion=False)
    nullable_field = NullableLabeledEnumField(TestEnum)
    
    class Meta:
        app_label = 'common'
        # Don't create database table
        managed = False


class TestLabeledEnumField(TestCase):
    """Test the LabeledEnumField custom field."""
    
    def test_field_accepts_enum_instance(self):
        """Test that field accepts enum instances."""
        obj = TestModel()
        obj.safe_field = TestEnum.SECOND
        
        self.assertEqual(obj.safe_field, TestEnum.SECOND)
        self.assertIsInstance(obj.safe_field, TestEnum)
    
    def test_field_accepts_string_lowercase(self):
        """Test that field accepts lowercase string values."""
        obj = TestModel()
        obj.safe_field = 'second'
        
        self.assertEqual(obj.safe_field, TestEnum.SECOND)
        self.assertIsInstance(obj.safe_field, TestEnum)
    
    def test_field_accepts_string_uppercase(self):
        """Test that field accepts uppercase string values."""
        obj = TestModel()
        obj.safe_field = 'THIRD'
        
        self.assertEqual(obj.safe_field, TestEnum.THIRD)
        self.assertIsInstance(obj.safe_field, TestEnum)
    
    def test_field_accepts_string_mixed_case(self):
        """Test that field accepts mixed case string values."""
        obj = TestModel()
        obj.safe_field = 'FiRsT'
        
        self.assertEqual(obj.safe_field, TestEnum.FIRST)
        self.assertIsInstance(obj.safe_field, TestEnum)
    
    def test_safe_field_handles_invalid_value(self):
        """Test that safe field returns default for invalid values."""
        obj = TestModel()
        obj.safe_field = 'invalid'
        
        # Should return default (FIRST) for invalid value
        self.assertEqual(obj.safe_field, TestEnum.FIRST)
    
    def test_strict_field_raises_on_invalid_value(self):
        """Test that strict field raises error for invalid values."""
        obj = TestModel()
        
        # Setting invalid value should work initially (no validation yet)
        obj.strict_field = 'invalid'
        
        # But accessing it should raise an error during conversion
        with self.assertRaises(ValidationError) as context:
            # Force conversion by accessing to_python
            field = obj._meta.get_field('strict_field')
            field.to_python('invalid')
        
        self.assertIn('Invalid value', str(context.exception))
    
    def test_get_prep_value_returns_lowercase(self):
        """Test that get_prep_value returns lowercase string."""
        field = TestModel._meta.get_field('safe_field')
        
        # Test with enum instance
        value = field.get_prep_value(TestEnum.SECOND)
        self.assertEqual(value, 'second')
        
        # Test with uppercase string
        value = field.get_prep_value('THIRD')
        self.assertEqual(value, 'third')
        
        # Test with mixed case string
        value = field.get_prep_value('FiRsT')
        self.assertEqual(value, 'first')
    
    def test_nullable_field_accepts_none(self):
        """Test that nullable field accepts None."""
        obj = TestModel()
        obj.nullable_field = None
        
        self.assertIsNone(obj.nullable_field)
    
    def test_nullable_field_has_correct_defaults(self):
        """Test that nullable field has null=True and blank=True."""
        field = TestModel._meta.get_field('nullable_field')
        
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
    
    def test_field_choices_are_set(self):
        """Test that field choices are properly set for admin."""
        field = TestModel._meta.get_field('safe_field')
        
        choices = field.choices
        self.assertEqual(len(choices), 3)
        
        # Choices should be lowercase tuples
        self.assertIn(('first', 'First Option'), choices)
        self.assertIn(('second', 'Second Option'), choices)
        self.assertIn(('third', 'Third Option'), choices)
    
    def test_field_default_is_set(self):
        """Test that field default is properly set from enum."""
        field = TestModel._meta.get_field('safe_field')
        
        # Default should be lowercase string
        self.assertEqual(field.default, 'first')
    
    def test_from_db_value_converts_to_enum(self):
        """Test that from_db_value converts string to enum."""
        field = TestModel._meta.get_field('safe_field')
        
        # Simulate database value
        enum_value = field.from_db_value('second', None, None)
        
        self.assertEqual(enum_value, TestEnum.SECOND)
        self.assertIsInstance(enum_value, TestEnum)
    
    def test_value_to_string_for_serialization(self):
        """Test that value_to_string returns lowercase string."""
        obj = TestModel()
        obj.safe_field = TestEnum.THIRD
        
        field = TestModel._meta.get_field('safe_field')
        string_value = field.value_to_string(obj)
        
        self.assertEqual(string_value, 'third')
