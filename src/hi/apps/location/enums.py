from typing import List

from hi.apps.common.enums import LabeledEnum
from hi.apps.entity.enums import EntityStateType


class LocationViewType(LabeledEnum):

    def __init__( self,
                  label                            : str,
                  description                      : str,
                  entity_state_type_priority_list  : List[ EntityStateType ] ):
        super().__init__( label, description )
        self.entity_state_type_priority_list = entity_state_type_priority_list
        return
    
    DEFAULT = (
        'Default',
        '',
        [ EntityStateType.MOVEMENT,
          EntityStateType.PRESENCE,
          EntityStateType.OPEN_CLOSE,
          EntityStateType.ON_OFF,
          EntityStateType.LIGHT_DIMMER,
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
    SECURITY = (
        'Security',
        '',
        [ EntityStateType.MOVEMENT,
          EntityStateType.PRESENCE,
          EntityStateType.OPEN_CLOSE,
          EntityStateType.ON_OFF,
          EntityStateType.LIGHT_DIMMER,
          ],
    )
    AUTOMATION = (
        'Automation',
        '',
        [ EntityStateType.MOVEMENT,
          EntityStateType.PRESENCE,
          EntityStateType.OPEN_CLOSE,
          EntityStateType.ON_OFF,
          EntityStateType.LIGHT_DIMMER,
          EntityStateType.LIGHT_LEVEL,
          EntityStateType.CONNECTIVITY,
          EntityStateType.HIGH_LOW,
          EntityStateType.SOUND_LEVEL,
          EntityStateType.DISCRETE,
          EntityStateType.CONTINUOUS,
          ],
    )


class SvgItemType(LabeledEnum):

    ICON         = ( 'Icon', '' )
    OPEN_PATH    = ( 'Open Path ', '' )
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

    
class SvgStyleName(LabeledEnum):

    COLOR      = ( 'Color', '' )
    GREYSCALE  = ( 'Grey Scale ', '' )

    @property
    def svg_defs_template_name(self):
        return f'location/panes/svg_fill_patterns_{self}.html'

    @property
    def css_static_file_name(self):
        return f'css/svg-location-{self}.css'
