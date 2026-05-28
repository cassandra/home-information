"""
Helper utilities for detecting DataPoint fields in dataclass-based weather models,
handling direct types, Union types, and Optional types.
"""

from typing import get_origin, get_args, Union
import types

from .transient_models import DataPoint


def extract_datapoint_type(field_type) -> tuple[type | None, bool]:
    """
    Extract the DataPoint subclass (if any) and optionality from a dataclass field's
    type annotation. Handles direct types, ``T | None``, ``Optional[T]``, and unions
    with multiple non-None members (first DataPoint subclass wins).

    Returns ``(datapoint_class, is_optional)``; ``datapoint_class`` is ``None`` when
    the field does not carry a DataPoint subclass.
    """
    try:
        if isinstance(field_type, type) and issubclass(field_type, DataPoint):
            return (field_type, False)
    except TypeError:
        pass

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
                    continue

        return (datapoint_type, is_optional)

    return (None, False)


def is_datapoint_field(field_type) -> bool:
    datapoint_class, _ = extract_datapoint_type(field_type)
    return datapoint_class is not None


def get_datapoint_class(field_type) -> type | None:
    datapoint_class, _ = extract_datapoint_type(field_type)
    return datapoint_class


def create_datapoint_instance(field_type, **kwargs):
    datapoint_class = get_datapoint_class(field_type)
    if datapoint_class is None:
        raise ValueError(f"Field type {field_type} is not a DataPoint field")

    return datapoint_class(**kwargs)


def is_field_optional(field_type) -> bool:
    _, is_optional = extract_datapoint_type(field_type)
    return is_optional
