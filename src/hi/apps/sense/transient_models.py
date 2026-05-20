from dataclasses import dataclass
from datetime import datetime
import json
from typing import Dict, Optional

from django.urls import reverse

from hi.apps.entity.enums import EntityStateValue

from hi.integrations.transient_models import IntegrationKey

from .models import Sensor, SensorHistory
from .enums import CorrelationRole
from .sensor_history_urls import (
    sensor_history_details_url,
    sensor_history_video_browse_url,
)


@dataclass
class SensorResponse:
    """One sensor reading flowing through the live pipeline.

    ``correlation_id`` pairs the START / END readings of a single
    upstream event but is SENSOR-SCOPED — uniqueness is guaranteed
    only within a single Sensor's history. Never compare or look up
    ``correlation_id`` without a sensor scope; independent
    integrations can produce overlapping id strings."""
    integration_key            : IntegrationKey
    value                      : str
    timestamp                  : datetime
    sensor                     : Sensor                     = None
    detail_attrs               : Dict[ str, str ]           = None
    has_event_video_clip       : bool                       = False
    has_event_video_snapshot   : bool                       = False
    correlation_role           : Optional[CorrelationRole]  = None
    correlation_id             : Optional[str]              = None
    sensor_history_id          : int                        = None  # Core Django SensorHistory primary key
    
    def __str__(self):
        return json.dumps( self.to_dict() )

    @property
    def entity(self):
        return self.sensor.entity_state.entity

    @property
    def entity_state(self):
        return self.sensor.entity_state

    @property
    def has_details(self):
        return bool( self.detail_attrs )
    
    @property
    def css_class(self):
        if not self.sensor:
            return ''
        return self.sensor.entity_state.css_class
    
    def is_on(self):
        return bool( self.value == str(EntityStateValue.ON) )

    def is_open(self):
        return bool( self.value == str(EntityStateValue.OPEN) )

    @property
    def video_browse_url(self) -> Optional[ str ]:
        return sensor_history_video_browse_url(
            entity_id = self.entity.id,
            sensor_id = self.sensor.id,
            sensor_history_id = self.sensor_history_id,
            has_event_video_clip = self.has_event_video_clip,
            provides_event_video_clip = self.sensor.provides_event_video_clip,
        )

    @property
    def details_url(self) -> Optional[ str ]:
        return sensor_history_details_url(
            sensor_history_id = self.sensor_history_id,
            has_details = self.has_details,
        )
    
    @property
    def entity_state_history_url(self) -> str:
        return reverse( 'entity_state_history',
                        kwargs = { 'entity_state_id': self.sensor.entity_state.id })

    @property
    def click_url(self):
        if self.has_event_video_clip:
            return self.video_browse_url
        if self.sensor_history_id and self.has_details:
            return self.details_url
        return self.entity_state_history_url
        
    def to_dict(self):
        return {
            'key': str(self.integration_key),
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor.id if self.sensor else None,
            'detail_attrs': self.detail_attrs,
            'has_event_video_clip': self.has_event_video_clip,
            'has_event_video_snapshot': self.has_event_video_snapshot,
            'correlation_role': str(self.correlation_role) if self.correlation_role else None,
            'correlation_id': self.correlation_id,
            'sensor_history_id': self.sensor_history_id,
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
            has_event_video_clip = self.has_event_video_clip,
            has_event_video_snapshot = self.has_event_video_snapshot,
            correlation_role_str = str(self.correlation_role) if self.correlation_role else None,
            correlation_id = self.correlation_id,
        )

    @classmethod
    def from_sensor_history( cls, sensor_history : SensorHistory ) -> 'SensorResponse':
        return SensorResponse(
            integration_key = sensor_history.sensor.integration_key,
            value = sensor_history.value,
            timestamp = sensor_history.response_datetime,
            sensor = sensor_history.sensor,
            detail_attrs = sensor_history.detail_attrs,
            has_event_video_clip = sensor_history.has_event_video_clip,
            has_event_video_snapshot = sensor_history.has_event_video_snapshot,
            correlation_role = sensor_history.correlation_role,
            correlation_id = sensor_history.correlation_id,
            sensor_history_id = sensor_history.id,
        )

    @classmethod
    def from_string( cls, sensor_response_str : str ) -> 'SensorResponse':
        sensor_response_dict = json.loads( sensor_response_str )

        # Parse correlation_role if present
        correlation_role = None
        correlation_role_str = sensor_response_dict.get('correlation_role')
        if correlation_role_str:
            correlation_role = CorrelationRole.from_name_safe(correlation_role_str)

        return SensorResponse(
            integration_key = IntegrationKey.from_string( sensor_response_dict.get('key') ),
            value = sensor_response_dict.get('value'),
            timestamp = datetime.fromisoformat( sensor_response_dict.get('timestamp') ),
            detail_attrs = sensor_response_dict.get('detail_attrs'),
            has_event_video_clip = sensor_response_dict.get('has_event_video_clip', False),
            has_event_video_snapshot = sensor_response_dict.get('has_event_video_snapshot', False),
            correlation_role = correlation_role,
            correlation_id = sensor_response_dict.get('correlation_id'),
            sensor_history_id = sensor_response_dict.get('sensor_history_id'),
        )
