from dataclasses import dataclass
from datetime import datetime

from hi.apps.entity.models import EntityState


@dataclass
class EntityStateTransition:

    entity_state  : EntityState
    from_value    : str
    to_value      : str
    timestamp     : datetime
    
