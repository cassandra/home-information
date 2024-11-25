from typing import List

from hi.apps.common.enums import LabeledEnum
from hi.apps.entity.enums import EntityStateType


class LocationViewType(LabeledEnum):

    CONTROL      = ('Control', '' )
    INFORMATION  = ('Information', '' )


class SvgItemType(LabeledEnum):

    ICON  = ( 'Icon', '' )
    OPEN_PATH  = ( 'Open Path ', '' )
    CLOSED_PATH  = ( 'Closed Path ', '' )

    @property
    def is_icon(self):
        return bool( self == SvgItemType.ICON )

    @property
    def is_path(self):
        return bool( self in [ SvgItemType.OPEN_PATH, SvgItemType.CLOSED_PATH ] )

    @property
    def is_path_closed(self):
        return bool( self == SvgItemType.CLOSED_PATH )

    
class StatusDisplayType(LabeledEnum):

    def __init__( self,
                  label                            : str,
                  description                      : str,
                  entity_state_type_priority_list  : List[ EntityStateType ] ):
        super().__init__( label, description )
        self.entity_state_type_priority_list = entity_state_type_priority_list
        return
    
    DEFAULT      = (
        'Default',
        '',
        [ EntityStateType.MOVEMENT,
          EntityStateType.PRESENCE,
          EntityStateType.OPEN_CLOSE,
          EntityStateType.LIGHT_LEVEL,
          EntityStateType.SOUND_LEVEL,
          EntityStateType.TEMPERATURE,
          EntityStateType.HIGH_LOW,
          EntityStateType.HUMIDITY,
          EntityStateType.MOISTURE,
          EntityStateType.WIND_SPEED,
          EntityStateType.AIR_PRESSURE,
          EntityStateType.ELECTRIC_USAGE,
          EntityStateType.WATER_FLOW,
          EntityStateType.HIGH_LOW,
          ],

    )
    SECURITY     = (
        'Security',
        '',
        [ EntityStateType.MOVEMENT,
          EntityStateType.PRESENCE,
          EntityStateType.OPEN_CLOSE,
          ],
    )
    LIGHT        = (
        'Light',
        '',
        [ EntityStateType.LIGHT_LEVEL,
          ],
    )
    SOUND        = (
        'Sound',
        '',
        [ EntityStateType.SOUND_LEVEL,
          ],
    )
    CLIMATE      = (
        'Climate',
        '',
        [ EntityStateType.TEMPERATURE,
          EntityStateType.HIGH_LOW,
          EntityStateType.HUMIDITY,
          EntityStateType.MOISTURE,
          EntityStateType.WIND_SPEED,
          EntityStateType.AIR_PRESSURE,
          ],
    )
    ENERGY       = (
        'Energy',
        '',
        [ EntityStateType.ELECTRIC_USAGE,
          EntityStateType.WATER_FLOW,
          EntityStateType.HIGH_LOW,
          ],
    )
    SUPPRESS     = (
        'Suppress',
        '',
        [],
    )

