from dataclasses import dataclass
from typing import Generator, List, Set

from hi.apps.collection.models import Collection, CollectionPath, CollectionPosition
from hi.apps.entity.models import Entity, EntityPosition, EntityPath
from hi.apps.location.models import (
    LocationItemPositionModel,
    LocationItemPathModel,
)

from .models import LocationView


@dataclass
class LocationViewData:
    """
    Encapsulates all the data needed to render overlaying a Location's SVG
    for a given LocationView.
    """
    location_view             : LocationView
    entity_positions          : List[ EntityPosition ]
    entity_paths              : List[ EntityPath ]
    collection_positions      : List[ CollectionPosition ]
    collection_paths          : List[ CollectionPath ]
    unpositioned_collections  : List[ Collection ]
    orphan_entities           : Set[ Entity ]

    @property
    def location_item_positions(self) -> Generator[ LocationItemPositionModel, None, None ]:
        for entity_position in self.entity_positions:
            yield entity_position
            continue
        for collection_position in self.collection_positions:
            yield collection_position
            continue
        return

    @property
    def location_item_paths(self) -> Generator[ LocationItemPathModel, None, None ]:
        for entity_path in self.entity_paths:
            yield entity_path
            continue
        for collection_path in self.collection_paths:
            yield collection_path
            continue
        return
    
