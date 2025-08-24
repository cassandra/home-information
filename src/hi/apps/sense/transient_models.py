from dataclasses import dataclass
from datetime import datetime
import json
from typing import Dict

from hi.apps.entity.enums import EntityStateValue

from hi.integrations.transient_models import IntegrationKey

from .models import Sensor, SensorHistory


@dataclass
class SensorResponse:
    integration_key     : IntegrationKey
    value               : str
    timestamp           : datetime
    sensor              : Sensor            = None
    detail_attrs        : Dict[ str, str ]  = None
    source_image_url    : str               = None
    has_video_stream    : bool              = False
    
    def __str__(self):
        return json.dumps( self.to_dict() )

    @property
    def css_class(self):
        if not self.sensor:
            return ''
        return self.sensor.entity_state.css_class
    
    def is_on(self):
        return bool( self.value == str(EntityStateValue.ON) )
    
    def to_dict(self):
        return {
            'key': str(self.integration_key),
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor.id if self.sensor else None,
            'detail_attrs': self.detail_attrs,
            'source_image_url': self.source_image_url,
            'has_video_stream': self.has_video_stream,
        }

    def to_sensor_history(self):
        if self.detail_attrs:
            details = json.dumps(self.detail_attrs)
        else:
            details = None
        return SensorHistory(
            sensor = self.sensor,
            value = self.value[0:255],
            response_datetime = self.timestamp,
            details = details,
            source_image_url = self.source_image_url,
            has_video_stream = self.has_video_stream,
        )
        
    @classmethod
    def from_sensor_history( cls, sensor_history : SensorHistory ) -> 'SensorResponse':
        return SensorResponse(
            integration_key = sensor_history.sensor.integration_key,
            value = sensor_history.value,
            timestamp = sensor_history.response_datetime,
            sensor = sensor_history.sensor,
            detail_attrs = sensor_history.detail_attrs,
            source_image_url = sensor_history.source_image_url,
            has_video_stream = sensor_history.has_video_stream,
        )
        
    @classmethod
    def from_string( cls, sensor_response_str : str ) -> 'SensorResponse':
        sensor_response_dict = json.loads( sensor_response_str )
        return SensorResponse(
            integration_key = IntegrationKey.from_string( sensor_response_dict.get('key') ),
            value = sensor_response_dict.get('value'),
            timestamp = datetime.fromisoformat( sensor_response_dict.get('timestamp') ),
            detail_attrs = sensor_response_dict.get('detail_attrs'),
            source_image_url = sensor_response_dict.get('source_image_url') or sensor_response_dict.get('image_url'),
            has_video_stream = sensor_response_dict.get('has_video_stream', False),
        )
