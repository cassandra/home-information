from typing import List

from hi.apps.common.enums import LabeledEnum
from hi.apps.entity.enums import EntityStateType


class ControllerType(LabeledEnum):

    DEFAULT              = ( 'Default', '' )  # EntityState will define behavior


class OneClickContextType(LabeledEnum):

    DEFAULT  = (
        'Default',
        '',
        [
            EntityStateType.ON_OFF,
            EntityStateType.LIGHT_DIMMER,
            EntityStateType.OPEN_CLOSE,
            EntityStateType.HIGH_LOW,
        ],        
    )

    def __init__( self,
                  label          : str,
                  description    : str,
                  priority_list  : List[ EntityStateType ] ):
        super().__init__( label, description )
        self.priority_list = priority_list
        return
        
