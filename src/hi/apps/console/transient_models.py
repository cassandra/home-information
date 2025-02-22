from dataclasses import dataclass

from hi.apps.entity.models import Entity, EntityState
from hi.apps.sense.models import Sensor


@dataclass
class VideoStreamEntity:
    entity           : Entity
    entity_state     : EntityState
    sensor           : Sensor

    @property
    def name(self) -> str:
        name = self.entity.name
        if name.lower().endswith('camera') and len(name) > len('camera'):
            name = name[:-len('camera')].strip()
        return name

    
@dataclass
class GeographicLocation:

    latitude   : float
    longitude  : float
    
