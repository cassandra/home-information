from dataclasses import dataclass
from datetime import datetime
import json
from typing import Dict, List

from hi.apps.entity.models import Entity

from hi.integrations.core.integration_key import IntegrationKey

from .models import Sensor, SensorHistory


@dataclass
class SensorResponse:
    integration_key  : IntegrationKey
    value            : str
    timestamp        : datetime
    sensor           : Sensor         = None
    details          : str            = None
    
    def __str__(self):
        return json.dumps( self.to_dict() )
    
    def to_dict(self):
        return {
            'key': str(self.integration_key),
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor.id if self.sensor else None,
            'details': self.details,
        }

    def to_sensor_history(self):
        return SensorHistory(
            sensor = self.sensor,
            value = self.value[0:255],
            response_datetime = self.timestamp,
            details = self.details,
        )
        
    @classmethod
    def from_sensor_history( self, sensor_history : SensorHistory ) -> 'SensorResponse':
        return SensorResponse(
            integration_key = sensor_history.sensor.integration_key,
            value = sensor_history.value,
            timestamp = sensor_history.response_datetime,
            sensor = sensor_history.sensor,
            details = sensor_history.details,
        )
        
    @classmethod
    def from_string( self, sensor_reading_str : str ) -> 'SensorResponse':
        sensor_reading_dict = json.loads( sensor_reading_str )
        return SensorResponse(
            integration_key = IntegrationKey.from_string( sensor_reading_dict.get('key') ),
            value = sensor_reading_dict.get('value'),
            timestamp = datetime.fromisoformat( sensor_reading_dict.get('timestamp') ),
            details = sensor_reading_dict.get('details'),
        )

    
@dataclass
class EntityStateHistoryData:
    entity                   : Entity
    sensor_history_list_map  : Dict[ Sensor, List[ SensorHistory ] ]
    
    def to_template_context(self):
        context = {
            'entity': self.entity,
            'sensor_history_list_map': self.sensor_history_list_map,
        }
        return context
