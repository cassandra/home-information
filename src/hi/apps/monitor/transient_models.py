from dataclasses import dataclass
from typing import Dict, List

from hi.apps.control.transient_models import ControllerData
from hi.apps.common.svg_models import SvgIconItem
from hi.apps.entity.entity_state_role_order import ENTITY_STATUS_VIEW_ORDERING
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse

from .enums import EntityDisplayCategory


@dataclass
class EntityStateStatusData:
    entity_state          : EntityState
    sensor_response_list  : List[ SensorResponse ]  # Not grouped by sensor, but ordered by response time
    controller_data_list  : List[ ControllerData ]
    # Whether the EntityState has any Sensor / Controller defined,
    # distinct from whether the response/data lists are populated.
    # A sensor-only state whose Sensor has no cached response yet
    # has ``has_sensor=True`` but an empty ``sensor_response_list``;
    # the display layer uses these to distinguish "awaiting first
    # reading" from "nothing defined."
    has_sensor            : bool                    = False
    has_controller        : bool                    = False

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
    
    @property
    def state_status_data_list(self) -> List[ EntityStateStatusData ]:
        """Display-ordered EntityStateStatusData list, sorted by
        ``ENTITY_STATUS_VIEW_ORDERING`` for the entity's EntityType.
        Use this in templates and other consumers that need the
        canonical display order. The underlying
        ``entity_state_status_data_list`` field stays order-neutral
        for consumers (e.g., per-state CSS-class update paths) that
        don't care about listing order."""
        return sorted(
            self.entity_state_status_data_list,
            key = lambda d: ENTITY_STATUS_VIEW_ORDERING.sort_key(
                d.entity_state.entity_state_role, self.entity.entity_type,
            ),
        )

    @property
    def state_status_data_by_role( self ) -> Dict[ str, EntityStateStatusData ]:
        """Role-keyed lookup of EntityStateStatusData for panel
        templates that pull a specific state by its semantic role
        (e.g., ``state_status_data_by_role.smoke`` on a smoke detector;
        ``state_status_data_by_role.thermostat_current_temperature``
        on a thermostat). Keys are the lowercase EntityStateRole
        name. When two states on the entity share a role (rare; not
        the normal model), the later one wins — panel access is
        about the canonical state for a role on the entity."""
        return {
            data.entity_state.entity_state_role.name.lower(): data
            for data in self.entity_state_status_data_list
        }

    def to_template_context(self):
        context = {
            'entity': self.entity,
            'entity_status_data': self,
            'state_status_data_list': self.state_status_data_list,
            'state_status_data_by_role': self.state_status_data_by_role,
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
        
