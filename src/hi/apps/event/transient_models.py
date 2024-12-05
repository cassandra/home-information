from dataclasses import dataclass
from typing import List

from hi.apps.entity.models import EntityState
from hi.apps.sense.transient_models import SensorResponse

from .models import EventDefinition


@dataclass
class EntityStateTransition:

    entity_state            : EntityState
    latest_sensor_response  : SensorResponse
    previous_value          : str

    @property
    def timestamp(self):
        return self.latest_sensor_response.timestamp
    
    
@dataclass
class Event:
    event_definition  : EventDefinition
    sensor_response_list  : List[ SensorResponse ]
    
    @property
    def timestamp(self):
        return max([ x.timestamp for x in self.sensor_response_list ])
    
