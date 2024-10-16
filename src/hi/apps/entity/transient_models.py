from dataclasses import dataclass, field
from typing import List

from hi.apps.location.models import LocationView

from .enums import EntityType
from .models import Entity


@dataclass
class EntityViewItem:

    entity          : Entity
    exists_in_view  : bool


@dataclass
class EntityViewGroup:

    location_view  : LocationView
    entity_type    : EntityType
    item_list      : List[EntityViewItem]  = field( default_factory = list )
