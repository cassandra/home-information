"""
Helper utilities for working with weather model types and DataPoint field detection.

This module provides robust utilities for detecting and working with DataPoint fields
in dataclass-based weather models, handling various type annotation patterns including
direct types, Union types, and Optional types.
"""

from typing import get_origin, get_args, Union
import types

from .transient_models import DataPoint


def extract_datapoint_type(field_type) -> tuple[type | None, bool]:
    """
    Extract the DataPoint type from a field type annotation, handling various type patterns.
    
    This function robustly handles:
    - Direct DataPoint types: NumericDataPoint
    - Union types (Python 3.10+): NumericDataPoint | None  
    - Optional types: Optional[NumericDataPoint]
    - Complex unions with multiple types
    
    Args:
        field_type: The type annotation from a dataclass field
        
    Returns:
        Tuple of (datapoint_class, is_optional) where:
        - datapoint_class: The DataPoint subclass, or None if not a DataPoint field
        - is_optional: True if the field can be None
        
    Examples:
        >>> extract_datapoint_type(NumericDataPoint)
        (NumericDataPoint, False)
        >>> extract_datapoint_type(NumericDataPoint | None)
        (NumericDataPoint, True)
        >>> extract_datapoint_type(Optional[StringDataPoint])
        (StringDataPoint, True)
        >>> extract_datapoint_type(str)
        (None, False)
    """
    # Handle direct DataPoint types
    try:
        if isinstance(field_type, type) and issubclass(field_type, DataPoint):
            return (field_type, False)
    except TypeError:
        # field_type is not a class, continue to union handling
        pass
    
    # Handle Union/Optional types
    origin = get_origin(field_type)
    if origin is Union or origin is types.UnionType:
        args = get_args(field_type)
        datapoint_type = None
        is_optional = False
        
        for arg in args:
            if arg is type(None):
                is_optional = True
            else:
                try:
                    if isinstance(arg, type) and issubclass(arg, DataPoint):
                        if datapoint_type is not None:
                            # Multiple DataPoint types in union - unusual case, take first
                            pass
                        else:
                            datapoint_type = arg
                except TypeError:
                    # arg is not a class, skip
                    continue
        
        return (datapoint_type, is_optional)
    
    # Not a DataPoint field
    return (None, False)


def is_datapoint_field(field_type) -> bool:
    """
    Check if a field type represents a DataPoint field (directly or optionally).
    
    Args:
        field_type: The type annotation from a dataclass field
        
    Returns:
        True if the field can contain a DataPoint, False otherwise
        
    Examples:
        >>> is_datapoint_field(NumericDataPoint)
        True
        >>> is_datapoint_field(NumericDataPoint | None)
        True
        >>> is_datapoint_field(Optional[StringDataPoint])
        True
        >>> is_datapoint_field(str)
        False
        >>> is_datapoint_field(int | None)
        False
    """
    datapoint_class, _ = extract_datapoint_type(field_type)
    return datapoint_class is not None


def get_datapoint_class(field_type) -> type | None:
    """
    Get the DataPoint class from a field type, ignoring optionality.
    
    Args:
        field_type: The type annotation from a dataclass field
        
    Returns:
        The DataPoint subclass, or None if not a DataPoint field
        
    Examples:
        >>> get_datapoint_class(NumericDataPoint | None)
        <class 'NumericDataPoint'>
        >>> get_datapoint_class(Optional[StringDataPoint])  
        <class 'StringDataPoint'>
        >>> get_datapoint_class(str)
        None
    """
    datapoint_class, _ = extract_datapoint_type(field_type)
    return datapoint_class


def create_datapoint_instance(field_type, **kwargs):
    """
    Create an instance of the appropriate DataPoint type for a field.
    
    Args:
        field_type: The type annotation from a dataclass field
        **kwargs: Arguments to pass to the DataPoint constructor
        
    Returns:
        Instance of the DataPoint subclass
        
    Raises:
        ValueError: If field_type is not a DataPoint field
        TypeError: If constructor arguments are invalid
        
    Example:
        >>> # For a field annotated as NumericDataPoint | None
        >>> dp = create_datapoint_instance(
        ...     field.type, 
        ...     station=station, 
        ...     source_datetime=now,
        ...     quantity_ave=UnitQuantity(25.0, 'degC')
        ... )
    """
    datapoint_class = get_datapoint_class(field_type)
    if datapoint_class is None:
        raise ValueError(f"Field type {field_type} is not a DataPoint field")
    
    return datapoint_class(**kwargs)


def is_field_optional(field_type) -> bool:
    """
    Check if a field type is optional (can be None).
    
    Args:
        field_type: The type annotation from a dataclass field
        
    Returns:
        True if the field can be None, False otherwise
        
    Examples:
        >>> is_field_optional(NumericDataPoint | None)
        True
        >>> is_field_optional(Optional[StringDataPoint])
        True
        >>> is_field_optional(NumericDataPoint)
        False
    """
    _, is_optional = extract_datapoint_type(field_type)
    return is_optional
