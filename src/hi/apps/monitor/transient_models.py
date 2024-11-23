from dataclasses import dataclass
from datetime import datetime
import json

from hi.integrations.core.integration_key import IntegrationKey


@dataclass
class SensorResponse:
    integration_key  : IntegrationKey
    value            : str
    timestamp        : datetime

    def __str__(self):
        return json.dumps( self.to_dict() )
    
    def to_dict(self):
        return {
            'key': str(self.integration_key),
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
        }

    @classmethod
    def from_string( self, sensor_reading_str : str ) -> 'SensorResponse':
        sensor_reading_dict = json.loads( sensor_reading_str )
        return SensorResponse(
            integration_key = IntegrationKey.from_string( sensor_reading_dict.get('key') ),
            value = sensor_reading_dict.get('value'),
            timestamp = datetime.fromisoformat( sensor_reading_dict.get('timestamp') ),
        )
