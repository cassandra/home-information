"""
Custom Django model fields for common patterns.
"""
from django.core.exceptions import ValidationError
from django.db import models

from .enums import LabeledEnum


class LabeledEnumDescriptor:
    """
    A descriptor that automatically converts values to enum instances.
    
    This handles the automatic conversion when setting/getting field values
    on model instances.
    """
    
    def __init__(self, field):
        self.field = field
    
    def __get__(self, instance, owner):
        if instance is None:
            return self.field
        
        # Get the raw value from the instance's __dict__
        value = instance.__dict__.get(self.field.attname)
        
        if value is None:
            return None
        
        # Convert to enum if it's a string
        if isinstance(value, str):
            try:
                return self.field._convert_from_string(value)
            except (ValueError, ValidationError):
                # If conversion fails with safe mode, it returns default
                # If conversion fails with strict mode, return the string
                # (will fail on validation)
                if self.field.use_safe_conversion:
                    return self.field.enum_class.default()
                return value
        
        # If it's already an enum, return it
        if isinstance(value, self.field.enum_class):
            return value
        
        # Try to convert other types
        try:
            return self.field.to_python(value)
        except (ValueError, ValidationError):
            if self.field.use_safe_conversion:
                return self.field.enum_class.default()
            return value
    
    def __set__(self, instance, value):
        # Store the raw value for now, conversion happens on get
        # This matches Django's behavior for other fields
        instance.__dict__[self.field.attname] = value


class LabeledEnumField(models.CharField):
    """
    A Django model field for storing LabeledEnum values.
    
    This field:
    - Stores enum values as lowercase strings in the database (VARCHAR)
    - Accepts enum instances or strings when setting values
    - Returns enum instances when accessing values
    - Validates that values are valid enum members
    - Does NOT require migrations when enum values change
    
    Usage:
        class MyModel(models.Model):
            # Use safe conversion (returns default for invalid values)
            status = LabeledEnumField(StatusType, max_length=32)
            
            # Use strict conversion (raises ValueError for invalid values)
            priority = LabeledEnumField(PriorityType, max_length=32, use_safe_conversion=False)
            
        # Can set with enum instance
        obj.status = StatusType.ACTIVE
        
        # Can set with string (case-insensitive)
        obj.status = 'active'
        obj.status = 'ACTIVE'
        
        # Always returns enum instance
        assert obj.status == StatusType.ACTIVE
        assert isinstance(obj.status, StatusType)
    """
    
    description = "A field for storing LabeledEnum values as lowercase strings"
    
    def __init__(self, enum_class, *args, use_safe_conversion=True, **kwargs):
        """
        Initialize the field.
        
        Args:
            enum_class: The LabeledEnum subclass this field stores
            use_safe_conversion: If True, use from_name_safe() which returns default for invalid values.
                               If False, use from_name() which raises ValueError for invalid values.
                               Default is True for backward compatibility and safety.
        """
        if not issubclass(enum_class, LabeledEnum):
            raise TypeError(f"{enum_class} must be a subclass of LabeledEnum")
        
        self.enum_class = enum_class
        self.use_safe_conversion = use_safe_conversion
        
        # Set default max_length if not provided
        if 'max_length' not in kwargs:
            # Calculate max length from enum values
            max_len = max(len(str(e)) for e in enum_class)
            kwargs['max_length'] = max(32, max_len + 10)  # Add buffer, min 32
        
        # Set choices for Django admin
        kwargs['choices'] = enum_class.choices()
        
        # Set default if the enum has one and no default was provided
        if 'default' not in kwargs and hasattr(enum_class, 'default'):
            kwargs['default'] = str(enum_class.default())
        
        super().__init__(*args, **kwargs)
    
    def _convert_from_string(self, value):
        """
        Convert string value to enum instance using configured conversion method.
        
        Args:
            value: String value to convert
            
        Returns:
            Enum instance
            
        Raises:
            ValueError: If use_safe_conversion is False and value is invalid
        """
        if self.use_safe_conversion:
            return self.enum_class.from_name_safe(value)
        else:
            return self.enum_class.from_name(value)
    
    def deconstruct(self):
        """
        Return enough information to recreate the field.
        Required for migrations.
        """
        name, path, args, kwargs = super().deconstruct()
        # Store the enum class path for reconstruction
        kwargs['enum_class'] = self.enum_class
        kwargs['use_safe_conversion'] = self.use_safe_conversion
        return name, path, args, kwargs
    
    def from_db_value(self, value, expression, connection):
        """
        Convert database value to Python enum instance.
        Called when fetching from database.
        """
        if value is None:
            return None
        
        try:
            return self._convert_from_string(value)
        except ValueError as e:
            # This should rarely happen with database values
            # but if it does, we want to know about it
            raise ValidationError(
                f"Invalid database value '{value}' for {self.enum_class.__name__}: {e}"
            )
    
    def to_python(self, value):
        """
        Convert input value to Python enum instance.
        Called during deserialization and clean().
        """
        if value is None:
            return None
        
        if isinstance(value, self.enum_class):
            return value
        
        if isinstance(value, str):
            try:
                return self._convert_from_string(value)
            except ValueError as e:
                raise ValidationError(
                    f"Invalid value '{value}' for {self.enum_class.__name__}: {e}"
                )
        
        # Try to convert other types to string first
        try:
            return self._convert_from_string(str(value))
        except (TypeError, ValueError) as e:
            raise ValidationError(
                f"Cannot convert {value!r} to {self.enum_class.__name__}: {e}"
            )
    
    def get_prep_value(self, value):
        """
        Convert Python value to database value.
        Called before saving to database.
        """
        if value is None:
            return None
        
        if isinstance(value, self.enum_class):
            # Convert enum to lowercase string
            return str(value)
        
        if isinstance(value, str):
            # Ensure lowercase
            # First validate it's a valid enum value
            try:
                enum_instance = self._convert_from_string(value)
                return str(enum_instance)
            except ValueError as e:
                raise ValidationError(
                    f"Invalid value '{value}' for {self.enum_class.__name__}: {e}"
                )
        
        # Try to convert to enum first for validation
        try:
            enum_instance = self.to_python(value)
            return str(enum_instance) if enum_instance else None
        except ValidationError:
            # Re-raise with clear message
            raise ValidationError(
                f"Value {value!r} is not valid for {self.enum_class.__name__}"
            )
    
    def value_to_string(self, obj):
        """
        Convert value to string for serialization.
        Used by dumpdata and other serializers.
        """
        value = self.value_from_object(obj)
        if value is None:
            return None
        return str(value)
    
    def validate(self, value, model_instance):
        """
        Validate that the value is a valid enum member.
        Called during model validation.
        """
        super().validate(value, model_instance)
        
        if value is None and not self.null:
            raise ValidationError("This field cannot be null.")
        
        if value is not None:
            # Ensure it's a valid enum value
            if not isinstance(value, self.enum_class):
                try:
                    # Try to convert it
                    self.to_python(value)
                except ValidationError as e:
                    raise ValidationError(
                        f"Invalid value for {self.enum_class.__name__}: {e}"
                    )
    
    def contribute_to_class(self, cls, name, **kwargs):
        """
        Add field to model class with custom descriptor for automatic conversion.
        """
        super().contribute_to_class(cls, name, **kwargs)
        # Set up the descriptor for this field
        setattr(cls, name, LabeledEnumDescriptor(self))


class NullableLabeledEnumField(LabeledEnumField):
    """
    A nullable version of LabeledEnumField.
    
    Convenience class that sets null=True, blank=True by default.
    """
    
    def __init__(self, enum_class, *args, **kwargs):
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        super().__init__(enum_class, *args, **kwargs)
