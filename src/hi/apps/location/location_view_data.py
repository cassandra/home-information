from dataclasses import dataclass
from typing import List, Set

from hi.apps.collection.models import Collection, CollectionPath, CollectionPosition
from hi.apps.entity.models import Entity, EntityPosition, EntityPath

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
