from dataclasses import dataclass, field
from typing import List

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.apps.location.models import LocationView

from .models import Collection


@dataclass
class CollectionViewItem:

    collection      : Collection
    exists_in_view  : bool


@dataclass
class CollectionViewGroup:

    location_view  : LocationView
    item_list      : List[CollectionViewItem]  = field( default_factory = list )


@dataclass
class EntityCollectionItem:

    entity                : Entity
    exists_in_collection  : bool


@dataclass
class EntityCollectionGroup:

    collection   : Collection
    entity_type  : EntityType
    item_list    : List[EntityCollectionItem]  = field( default_factory = list )
    
