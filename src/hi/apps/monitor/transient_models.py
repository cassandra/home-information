from dataclasses import dataclass
from typing import List

from hi.apps.control.transient_models import ControllerData
from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.transient_models import SensorResponse


@dataclass
class EntityStateStatusData:
    entity_state          : EntityState
    sensor_response_list  : List[ SensorResponse ]  # Not grouped by sensor, but ordered by response time
    controller_data_list  : List[ ControllerData ]

    @property
    def latest_sensor_response(self):
        if self.sensor_response_list:
            return self.sensor_response_list[0]
        return None
    
    
@dataclass
class EntityStatusData:
    entity                         : Entity
    entity_state_status_data_list  : List[ EntityStateStatusData ]

    def to_template_context(self):
        context = {
            'entity': self.entity,
            'entity_state_status_data_list': self.entity_state_status_data_list,
        }
        return context
    
    
