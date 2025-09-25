from dataclasses import dataclass
from typing import List

from hi.apps.control.transient_models import ControllerData
from hi.apps.common.svg_models import SvgIconItem
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse

from .enums import EntityDisplayCategory


@dataclass
class EntityStateStatusData:
    entity_state          : EntityState
    sensor_response_list  : List[ SensorResponse ]  # Not grouped by sensor, but ordered by response time
    controller_data_list  : List[ ControllerData ]

    @property
    def latest_sensor_response(self) -> SensorResponse:
        if self.sensor_response_list:
            return self.sensor_response_list[0]
        return None

    
@dataclass
class EntityStatusData:
    entity                         : Entity
    entity_state_status_data_list  : List[ EntityStateStatusData ]
    entity_for_video               : Entity                        = None
    display_only_svg_icon_item     : SvgIconItem                   = None
    
    def __post_init__(self):
        if not self.entity_for_video and self.entity.has_video_stream:
            self.entity_for_video = self.entity
        return
    
    def to_template_context(self):
        context = {
            'entity': self.entity,
            'entity_state_status_data_list': self.entity_state_status_data_list,
            'entity_for_video': self.entity_for_video,
            'display_only_svg_icon_item': self.display_only_svg_icon_item,
            'display_category': self.display_category,
        }
        return context

    @property
    def display_category( self ) -> EntityDisplayCategory:
        if self.entity_for_video:
            return EntityDisplayCategory.HAS_VIDEO
        if len( self.entity_state_status_data_list ) > 0:
            return EntityDisplayCategory.HAS_STATE
        return EntityDisplayCategory.PLAIN
        
