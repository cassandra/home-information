import importlib
from dataclasses import dataclass
from enum import Enum

from hi.apps.attribute.enums import AttributeValueType


@dataclass
class SettingDefinition:
    label             : str
    description       : str
    value_type        : AttributeValueType
    value_range_str   : str
    is_editable       : bool
    is_required       : bool
    initial_value     : str    


class SettingEnum(Enum):

    def __new__( cls, definition : SettingDefinition):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__) + 1  # Auto-numbering
        obj.definition = definition
        return obj

    @property
    def key(self):
        return f'{self.__class__.__module__}.{self.__class__.__qualname__}.{self.name}'

    @classmethod
    def from_key(cls, setting_key: str) -> "SettingEnum":
        module_path, enum_class_name, member_name = setting_key.rsplit('.', 2)
        module = importlib.import_module(module_path)
        enum_cls = getattr(module, enum_class_name)
        if not issubclass(enum_cls, SettingEnum):
            raise AttributeError(f"{enum_class_name} is not a SettingEnum")
        return getattr(enum_cls, member_name)
    