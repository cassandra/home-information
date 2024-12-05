from dataclasses import dataclass
from datetime import datetime
from typing import List

from hi.apps.alert.transient_models import Alarm
from hi.apps.entity.models import EntityState
from hi.apps.sense.transient_models import SensorResponse

from .models import AlarmAction, EventDefinition, EventHistory


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
    def timestamp(self) -> datetime:
        return max([ x.timestamp for x in self.sensor_response_list ])
    
    def to_event_history(self) -> EventHistory:
        return EventHistory(
            event_definition = self.event_definition,
            event_datetime = self.timestamp,
        )
    
    def to_alarm( self, alarm_action : AlarmAction ) -> Alarm:
        return Alarm(
            title = self.event_definition.name,
            details = ', '.join([ x.sensor.name for x in self.sensor_response_list ]),
            security_posture = alarm_action.security_posture,
            alarm_level = alarm_action.alarm_level,
            lifetime_secs = alarm_action.lifetime_secs,
            timestamp = self.timestamp,
        )
