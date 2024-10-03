from dataclasses import dataclass, field
from typing import List

from hi.apps.collection.models import Collection
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity


@dataclass
class EntityCollectionItem:

    entity                : Entity
    exists_in_collection  : bool


@dataclass
class EntityCollectionGroup:

    collection   : Collection
    entity_type  : EntityType
    item_list    : List[EntityCollectionItem]  = field( default_factory = list )
    
