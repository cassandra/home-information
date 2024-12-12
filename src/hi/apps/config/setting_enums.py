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
    
